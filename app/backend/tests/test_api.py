"""API smoke test: an example's editable curves go back through /api/classify with the same answer as step 1."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api  # noqa: E402
import examples  # noqa: E402

pytestmark = pytest.mark.skipif(not (examples.TRACES / 'boundaries' / 'index.json').exists(),
                                reason='hand-trace dataset not found (set ISOFOLD_TRACES)')
client = TestClient(api.app)


def test_example_round_trip():
    assert len(client.get('/api/examples').json()) == len(examples.CATALOG)
    ex = client.get('/api/examples/Fold_11').json()
    r = client.post('/api/classify', json=dict(outer=ex['outer'], inner=ex['inner'], angles=[30, 45, 60])).json()
    assert r['verdict'] == 'confident' and r['overall']['fold_class'] == '1C'
    assert sorted(l['R'] for l in r['limbs'].values()) == pytest.approx([0.152, 0.186], abs=0.002)


def test_bad_input_is_refused_not_an_error():
    r = client.post('/api/classify', json=dict(outer={'points': [[0, 0], [1, 1]]}, inner={'points': []}))
    assert r.status_code == 200 and r.json()['verdict'] == 'refused'
    assert client.get('/api/examples/nope').status_code == 404
