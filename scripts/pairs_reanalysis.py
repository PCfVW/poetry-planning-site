"""Pair-level re-analysis of the plip-rs suppress-and-inject position sweeps.

Reproduces the pair-level table of the arXiv revision (Appendix C, "Pair-level
re-analysis"): for each (prompt, inject feature) pair, the argmax position, the
effect size against the sweep's own floor (the median over positions), and the
best newline position's ratio to that floor.

The plip-rs files record a ``baseline_p_inject`` field that disagrees with the
flat in-sweep level by a roughly constant factor on Gemma (about 50x), so every
ratio here is taken against the in-sweep floor instead.

Usage (no GPU, seconds):

  python scripts/pairs_reanalysis.py data/pairs/suppress_inject_sweep_gemma_426k.json \
      data/pairs/suppress_inject_sweep_llama_524k.json \
      data/pairs/suppress_inject_sweep_gemma_2.5m.json

Doctests cover the pure helpers:

  python -m doctest scripts/pairs_reanalysis.py
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def median_floor(probs: list[float]) -> float:
  """Median over positions, used as the unsteered floor of one sweep.

  >>> median_floor([1.0, 1.0, 1.0, 100.0])
  1.0
  """
  return statistics.median(probs)


def newline_positions(tokens: list[str]) -> list[int]:
  """Indices of tokens containing a newline (Llama merges ',\\n' into one token).

  >>> newline_positions(['A', ',\\n', 'b', '\\n'])
  [1, 3]
  """
  return [i for i, t in enumerate(tokens) if '\n' in t]


def summarize_pair(pair: dict) -> dict:
  """Per-pair statistics against the in-sweep floor.

  >>> p = {'positions': [{'token': 'a', 'p_inject': 1.0}, {'token': '\\n', 'p_inject': 1.2},
  ...                    {'token': 'b', 'p_inject': 1.0}, {'token': 'c', 'p_inject': 1.0},
  ...                    {'token': ' ', 'p_inject': 50.0}]}
  >>> s = summarize_pair(p)
  >>> (s['argmax'], s['at_final'], s['max_ratio'], round(s['newline_ratio'], 2))
  (4, True, 50.0, 1.2)
  """
  probs = [p['p_inject'] for p in pair['positions']]
  tokens = [p['token'] for p in pair['positions']]
  n = len(probs)
  floor = median_floor(probs)
  argmax = max(range(n), key=lambda i: probs[i])
  nl = newline_positions(tokens)
  return {
    'n': n,
    'argmax': argmax,
    'at_final': argmax == n - 1,
    'argmax_is_newline': argmax in nl,
    'max_p': max(probs),
    'max_ratio': max(probs) / floor if floor > 0 else float('nan'),
    'newline_ratio': (max(probs[i] for i in nl) / floor) if nl and floor > 0 else float('nan'),
  }


def summarize_file(path: Path, detect: float = 10.0, behavioral: float = 0.1) -> dict:
  d = json.loads(path.read_text(encoding='utf-8'))
  rows = [summarize_pair(r) for r in d['results']]
  det = [r for r in rows if r['max_ratio'] > detect]
  beh = [r for r in rows if r['max_p'] >= behavioral]
  nl_arg = [r for r in rows if r['argmax_is_newline']]
  return {
    'file': path.name,
    'model': d['model'],
    'clt': d['clt_repo'],
    'strength': d['suppress_strength'],
    'pairs': len(rows),
    'prompts': len({r['prompt_text'] for r in d['results']}),
    'argmax_at_final': sum(r['at_final'] for r in rows),
    'detectable': len(det),
    'detectable_at_final': sum(r['at_final'] for r in det),
    'behavioral': len(beh),
    'behavioral_at_final': sum(r['at_final'] for r in beh),
    'argmax_at_newline': len(nl_arg),
    'argmax_at_newline_max_ratio': max((r['max_ratio'] for r in nl_arg), default=float('nan')),
    'newline_ratio_median': statistics.median(r['newline_ratio'] for r in rows),
    'newline_ratio_max': max(r['newline_ratio'] for r in rows),
  }


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('files', nargs='+', type=Path)
  ap.add_argument('--detect-ratio', type=float, default=10.0)
  ap.add_argument('--behavioral-p', type=float, default=0.1)
  args = ap.parse_args()
  for f in args.files:
    s = summarize_file(f, args.detect_ratio, args.behavioral_p)
    print(f"== {s['file']}: {s['model']} x {s['clt']} (s={s['strength']})")
    print(f"  pairs {s['pairs']} over {s['prompts']} prompts")
    print(f"  argmax at final token: {s['argmax_at_final']}")
    print(f"  detectable (>{args.detect_ratio:g}x floor): {s['detectable']}, "
          f"of which at final: {s['detectable_at_final']}")
    print(f"  behavioral (P>={args.behavioral_p:g}): {s['behavioral']}, "
          f"of which at final: {s['behavioral_at_final']}")
    print(f"  argmax at a newline: {s['argmax_at_newline']} "
          f"(their max ratio {s['argmax_at_newline_max_ratio']:.2f}x)")
    print(f"  best newline / floor: median {s['newline_ratio_median']:.2f}x, "
          f"max {s['newline_ratio_max']:.2f}x")


if __name__ == '__main__':
  main()
