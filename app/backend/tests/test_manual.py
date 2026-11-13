"""manual.classify on the CorelDraw hand traces: same numbers as run_engine_on_traces.py, robust to how the user
traces (direction, which line first), and display isogons consistent with the fit.

Run from app/backend:  ../../.venv/bin/python -m pytest tests -q"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examples  # noqa: E402
import manual  # noqa: E402

pytestmark = pytest.mark.skipif(not (examples.TRACES / 'boundaries' / 'index.json').exists(),
                                reason='hand-trace dataset not found (set ISOFOLD_TRACES)')

# per-limb R with both lines in manual._canonical direction. dataset/traces/engine_results.json ran the lines as
# drawn in CorelDraw and got Fold_11 0.165/0.173, Fold-3 0.151/0.230: the same fold within the engine's
# sensitivity to the hinge position. Hand-measured R: Fold_11 0.186 (table Fold-2A), Fold-3 0.224 (Fold-3A).
KNOWN = {'Fold_11': (0.152, 0.186), 'Fold-3': (0.164, 0.223), 'Fold_15A': (-0.010, 0.009)}


def limb_Rs(res):
    return tuple(sorted(l['R'] for l in res['limbs'].values()))


@pytest.mark.parametrize('name', KNOWN)
def test_reproduces_known_R(name):
    ex = examples.load(name)
    res = manual.classify(ex['outer'], ex['inner'])
    assert res['verdict'] != 'refused'
    assert limb_Rs(res) == pytest.approx(sorted(KNOWN[name]), abs=0.002)


def test_tracing_order_and_direction_do_not_matter():
    ex = examples.load('Fold_11')
    base = manual.classify(ex['outer'], ex['inner'])
    swapped = manual.classify(ex['inner'], ex['outer'])
    others = [manual.classify(ex['inner'], ex['outer'])] + [
        manual.classify(o, i) for o, i in ((ex['outer'][::-1], ex['inner']), (ex['outer'], ex['inner'][::-1]),
                                           (ex['outer'][::-1], ex['inner'][::-1]))]
    assert swapped['swapped'] != base['swapped']
    for other in others:
        assert other['overall'] == base['overall']
        for limb in ('left', 'right'):                      # limbs are named by screen side, not tracing order
            assert other['limbs'][limb]['R'] == base['limbs'][limb]['R']


def test_display_isogons_match_the_fit():
    ex = examples.load('Fold-3')
    res = manual.classify(ex['outer'], ex['inner'], angles=[30, 45, 60])
    assert {(i['limb'], i['alpha']) for i in res['isogons']} == {(l, a) for l in ('left', 'right') for a in (30, 45, 60)}
    for iso in res['isogons']:
        # 30/45/60 lie on the engine's 2.5 deg grid, so the chart has the same point
        grid = dict((round(a, 2), t) for a, t in res['chart'][iso['limb']]['points'])
        assert iso['t_prime'] == pytest.approx(grid[iso['alpha']], abs=0.002)
        # t_alpha is the distance from q to the outer tangent at p
        assert np.hypot(*np.subtract(iso['q'], iso['foot'])) == pytest.approx(iso['t_px'], abs=0.5)
        assert iso['in_fit_range']


def test_unreachable_and_display_only_angles():
    ex = examples.load('Fold_11')
    res = manual.classify(ex['outer'], ex['inner'], angles=[10, 80])
    assert all(not i['in_fit_range'] for i in res['isogons'])
    assert {(m['limb'], m['alpha']) for m in res['missing']} == {('left', 80), ('right', 80)}
    assert '75° or steeper' in res['missing'][0]['why']


def test_hand_traces_are_confident_when_limbs_agree():
    # dip > 54 deg and the auto-detector's pair checks are notes, not reasons, for hand-drawn lines
    ex = examples.load('Fold_11')
    res = manual.classify(ex['outer'], ex['inner'])
    assert res['verdict'] == 'confident' and res['overall']['fold_class'] == '1C'
    assert any('dip' in n for n in res['notes'])


def test_refuses_with_a_plain_reason():
    line = np.stack([np.linspace(0, 500, 50), np.zeros(50)], 1)
    res = manual.classify(line, line + [0, 80])                 # two straight lines: no fold
    assert res['verdict'] == 'refused' and res['reasons'][0]
    assert manual.classify([[0, 0], [1, 1]], line)['verdict'] == 'refused'
