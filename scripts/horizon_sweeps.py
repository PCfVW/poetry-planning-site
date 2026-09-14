"""Position-sweep summary for the composition-horizon runs.

Every horizon run writes an m4 position sweep: the teacher-forced probability of
the injected word at the composed line's final-word slot, as the steering
position is swept over the prompt and the composed line. The power run therefore
produced one sweep per (cell, prompt, seed) instead of the single sweep per cell
of the earlier study.

For each sweep this script reports where the probability peaks, whether that
position is the line-3 newline (the original's planning site), and the newline's
probability relative to the sweep's own floor (the median over the other
positions), which is the quantity the paper cites for newline inertness.

Usage (no GPU, seconds):

  python scripts/horizon_sweeps.py data/horizon-power/fullline_*.json

Doctests:

  python -m doctest scripts/horizon_sweeps.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import statistics
from pathlib import Path


def summarise_sweep(sweep: list[dict], newline_index: int, n_prompt: int) -> dict:
  """Peak location and newline level of one m4 sweep, against its own floor.

  >>> s = [{'token': 'a', 'p_inject': 1e-6}, {'token': '\\n', 'p_inject': 1e-6},
  ...      {'token': 'x', 'p_inject': 1e-6}, {'token': 'y', 'p_inject': 0.5}]
  >>> r = summarise_sweep(s, newline_index=1, n_prompt=2)
  >>> r['argmax'], r['argmax_is_newline'], r['argmax_in_composed']
  (3, False, True)
  >>> round(r['newline_over_floor'], 3), f"{r['peak_over_floor']:.0f}"
  (1.0, '500000')
  """
  probs = [p['p_inject'] for p in sweep]
  argmax = max(range(len(probs)), key=lambda i: probs[i])
  floor = statistics.median([p for i, p in enumerate(probs) if i != argmax])
  return {
    'argmax': argmax,
    'argmax_token': sweep[argmax]['token'],
    'argmax_is_newline': argmax == newline_index,
    'argmax_in_composed': argmax >= n_prompt,
    'peak': probs[argmax],
    'newline': probs[newline_index],
    'floor': floor,
    'peak_over_floor': probs[argmax] / floor if floor else float('inf'),
    'newline_over_floor': probs[newline_index] / floor if floor else float('inf'),
  }


def report(paths: list[Path]) -> None:
  by_cell: dict[str, list[dict]] = collections.defaultdict(list)
  for p in paths:
    d = json.loads(p.read_text(encoding='utf-8'))
    by_cell[d['preset']].append(
        summarise_sweep(d['m4_position_sweep'], d['newline_index'], len(d['tokens'])))
  total = sum(len(v) for v in by_cell.values())
  n_nl = sum(r['argmax_is_newline'] for v in by_cell.values() for r in v)
  n_comp = sum(r['argmax_in_composed'] for v in by_cell.values() for r in v)
  print(f"{total} position sweeps: peak in the composed line {n_comp}/{total}, "
        f"peak at the newline {n_nl}/{total}")
  for cell, rs in sorted(by_cell.items()):
    n = len(rs)
    pk = [r['peak_over_floor'] for r in rs]
    nl = [r['newline_over_floor'] for r in rs]
    print(f"\n== {cell}: {n} sweeps")
    print(f"   peak in composed line {sum(r['argmax_in_composed'] for r in rs)}/{n}, "
          f"at newline {sum(r['argmax_is_newline'] for r in rs)}/{n}")
    print(f"   peak / floor     median {statistics.median(pk):.3g}   "
          f"min {min(pk):.3g}   max {max(pk):.3g}")
    print(f"   newline / floor  median {statistics.median(nl):.3g}   "
          f"min {min(nl):.3g}   max {max(nl):.3g}")
    print(f"   peak absolute P  median {statistics.median(r['peak'] for r in rs):.3g}; "
          f"newline absolute P median {statistics.median(r['newline'] for r in rs):.3g}")
    toks = collections.Counter(r['argmax_token'] for r in rs)
    print(f"   peak tokens: {', '.join(f'{t!r} x{k}' for t, k in toks.most_common(5))}")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('files', nargs='+')
  args = ap.parse_args()
  paths = [Path(p) for pat in args.files for p in sorted(glob.glob(pat))]
  report(paths)


if __name__ == '__main__':
  main()
