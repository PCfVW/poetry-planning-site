"""Encoder activity of each cell's steering features at the censused positions.

For every census JSON (Experiment 1: every active CLT feature at three newline
positions, two mid-line control positions, and the final prompt token), report
the encoder activation of the preset's suppress and inject features at each
position. A feature absent from a position's list is encoder-silent there
(activation 0). This is the check behind the "write-direction steering"
footnote of the cells table.

Usage (no GPU, seconds):

  python scripts/steering_feature_activity.py <census.json> [...]

Feature identifiers come from the paper's Table 4 (layer:index) and are keyed
by the census file's preset name.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# preset -> (suppress features, inject feature), layer:index as in Table 4.
FEATURES: dict[str, tuple[list[tuple[int, int]], tuple[int, int]]] = {
  'gemma2-2b-426k': ([(16, 13725), (25, 9385)], (22, 10243)),
  'gemma2-2b-2.5m': ([(25, 57092), (23, 49923), (20, 77102)], (25, 82839)),
  'llama3.2-1b-524k': ([(13, 30985), (9, 5488), (14, 27874), (13, 32049)], (14, 13043)),
  'qwen3-0.6b-16k-ation': ([(23, 11154), (20, 10987), (14, 10719)], (22, 8011)),
  'qwen3-0.6b-20k-ation': ([(19, 9578), (0, 8867), (25, 4979)], (22, 4081)),
  'qwen3-0.6b-20k-teen': ([(27, 16425), (23, 15839), (26, 6308)], (19, 9578)),
  'qwen3-1.7b-20k-ation': ([(15, 263), (18, 3801), (18, 4404)], (21, 3908)),
  'qwen3-1.7b-20k-teen': ([(27, 16975), (20, 3668), (18, 10986)], (15, 263)),
}


def report(path: Path) -> None:
  d = json.loads(path.read_text(encoding='utf-8'))
  preset = d['preset']
  sup, inj = FEATURES[preset]
  wanted = {f: 'suppress' for f in sup}
  wanted[inj] = 'inject'
  print(f"== {path.name}: preset {preset}, natural word {d['natural_word']!r}, "
        f"{len(d['tokens'])} tokens")
  any_hit = False
  for p in d['positions']:
    act = {(x['layer'], x['index']): x['activation'] for x in p['features']}
    hits = {f"{l}:{i} ({wanted[(l, i)]})": round(act[(l, i)], 3)
            for (l, i) in wanted if (l, i) in act}
    any_hit |= bool(hits)
    print(f"  pos {p['position']:2d} {p['token']!r:14} {p['role']:8} "
          f"active {len(p['features']):6,d}  steering features: {hits or 'none'}")
  if not any_hit:
    print("  -> all steering features encoder-silent at every censused position")


if __name__ == '__main__':
  for arg in sys.argv[1:]:
    report(Path(arg))
