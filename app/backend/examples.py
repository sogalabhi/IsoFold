"""Field examples for the web app: the CorelDraw hand traces (decoded into dataset/traces/boundaries) with the
hand-measured t'a tables from the department spreadsheets, where a table exists for that drawing.

A drawing is matched to its spreadsheet table by its angle labels: Fold_11 carries 30/45/60/70/75/80 deg like
table Fold-2A (same photo IMG_20180211_163530); Fold-3 like Fold-3A (IMG_20180211_145755); Backup_of_Fold_3B
carries 19.99/25.97/38.04/44.06/52.05/64.07 deg, exactly table Fold 3_B's alpha values.

The dataset lives outside the repo; set ISOFOLD_TRACES to point elsewhere."""
import json
import os
from pathlib import Path

import numpy as np

TRACES = Path(os.environ.get('ISOFOLD_TRACES', Path(__file__).resolve().parents[3] / 'dataset' / 'traces'))

# hand-measured t'a by alpha (deg), copied from 'Fold data.xlsx' (sheets Fold-2, Fold-3) and 'Folds_Layers_New.xlsx'
HAND = {
    'Fold-2A': [(30.0, 0.879), (45.0, 0.751), (60.0, 0.577), (70.0, 0.462), (75.0, 0.401), (80.0, 0.340)],
    'Fold-3A': [(30.0, 0.887), (45.0, 0.766), (60.0, 0.590), (70.0, 0.513), (75.0, 0.412), (80.0, 0.369)],
    'Fold 3_B': [(19.99, 0.931), (25.97, 0.880), (38.04, 0.782), (44.06, 0.740), (52.05, 0.426), (64.07, 0.652)],
}

# distinct folds only (the backups duplicate these). pair = which two traced boundaries form the bed.
CATALOG = [
    dict(name='Fold_11', title='Fold 11', hand='Fold-2A'),
    dict(name='Fold-3', title='Fold 3', hand='Fold-3A'),
    dict(name='Backup_of_Fold_3B', title='Fold 3B', hand='Fold 3_B'),
    dict(name='Fold_17A', title='Fold 17A'),
    dict(name='Fold_14', title='Fold 14'),
    dict(name='Fold_13', title='Fold 13'),
    dict(name='Fold_12', title='Fold 12', pair=(0, 1)),
    dict(name='Fold_9', title='Fold 9', pair=(0, 1)),
    dict(name='Fold_15A', title='Fold 15A'),
    dict(name='Fold_15B', title='Fold 15B'),
    dict(name='Fold_16A', title='Fold 16A'),
    dict(name='Fold_16B', title='Fold 16B', pair=(0, 1)),
]


def hand_R(table):
    """Least-squares R for t' = R + (1 - R) cos a, i.e. t' - cos a = R (1 - cos a), through the origin."""
    c = np.cos(np.radians([a for a, _ in table]))
    y = np.array([t for _, t in table]) - c
    return float(np.sum((1 - c) * y) / np.sum((1 - c) ** 2))


def _hand(key):
    if not key:
        return None
    table = HAND[key]
    R = hand_R(table)
    cls = '1A' if R > 1.05 else '1B' if R > 0.95 else '1C' if R > 0.05 else '2' if R > -0.05 else '3'
    return dict(label=key, R=round(R, 3), fold_class=cls, angles=[a for a, _ in table], t_prime=[t for _, t in table])


def _locality(source):
    # 'Shear Zone/11_IMG_...jpg' -> 'Shear Zone'; 'More photos/Photographs/x.jpg' -> photo name
    parts = source.split('/')
    return parts[0] if parts[0] != 'More photos' else parts[-1].rsplit('.', 1)[0]


def catalog():
    index = {r['name']: r for r in json.loads((TRACES / 'boundaries' / 'index.json').read_text())}
    out = []
    for e in CATALOG:
        rec = index[e['name']]
        out.append(dict(name=e['name'], title=e['title'], locality=_locality(rec['source']), source=rec['source'],
                        photo_size=rec['photo_size'], hand=_hand(e.get('hand'))))
    return out


def load(name):
    """One example: photo path, the two traced boundaries (as drawn; manual.classify decides which is outer)."""
    e = next(e for e in CATALOG if e['name'] == name)
    b = json.loads((TRACES / 'boundaries' / f'{name}.json').read_text())
    i, j = e.get('pair', (0, 1))
    info = next(c for c in catalog() if c['name'] == name)
    return dict(info, photo_path=TRACES / b['photo'],
                outer=np.array(b['boundaries'][i]['points']), inner=np.array(b['boundaries'][j]['points']))
