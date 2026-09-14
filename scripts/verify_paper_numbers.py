"""Check that the composition-horizon numbers asserted in main.tex match the data.

An earlier paper in this line shipped with numbers that disagreed between its
main text and its appendix. This script closes that failure mode for the
experiment most likely to be re-run: it recomputes the quantities §4.4,
Table 6 and Table 7 assert, straight from ``data/horizon-power/fullline_*.json``,
and checks each against the string actually present in ``main.tex``.

It is a consistency check, not a correctness proof: it verifies that the paper
says what the data say, not that the data are right.

Usage (no GPU, seconds), from the paper directory:

  python scripts/verify_paper_numbers.py

Exit status is 0 when every check passes and 1 otherwise, so it can gate a
build. Doctests:

  python -m doctest scripts/verify_paper_numbers.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from horizon_leakage import (  # noqa: E402
    classify, final_word, insertion_site, redirect_criteria, rime_of,
)

CONDITIONS = ('baseline', 'suppress-only', 'inject-only', 'suppress+inject')


def tex_number(value: int) -> str:
  """Render an integer the way the paper writes it, with a LaTeX thousands mark.

  >>> tex_number(703), tex_number(1545), tex_number(8640)
  ('703', '1{,}545', '8{,}640')
  """
  return f'{value:,}'.replace(',', '{,}')


def gather(paths: list[Path]) -> dict:
  """Recompute the quantities the paper asserts, from the run files."""
  from nltk.corpus import cmudict  # noqa: PLC0415
  cmu = cmudict.dict()
  cnt: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
  sweeps: list[dict] = []
  total_lines = 0
  for p in paths:
    d = json.loads(p.read_text(encoding='utf-8'))
    inj = d['inject_word']
    nat_rime, inj_rime = rime_of(d['suppress_word'], cmu), rime_of(inj, cmu)
    probs = [q['p_inject'] for q in d['m4_position_sweep']]
    argmax = max(range(len(probs)), key=lambda i: probs[i])
    floor = sorted(probs[:argmax] + probs[argmax + 1:])[len(probs) // 2 - 1]
    sweeps.append({
      'in_composed': argmax >= len(d['tokens']),
      'is_newline': argmax == d['newline_index'],
      'newline_over_floor': probs[d['newline_index']] / floor,
    })
    for c in d['conditions']:
      key = (d['preset'], c['condition'])
      for ln in c['sampled_lines']:
        total_lines += 1
        cnt[key]['n'] += 1
        grp = classify(final_word(ln), cmu, nat_rime, inj_rime)
        cnt[key][grp] += 1
        site = insertion_site(ln, inj)
        if site:
          cnt[key]['inserted'] += 1
          cnt[key][f'insert_{site}'] += 1
        if grp == 'inject':
          for name, ok in redirect_criteria(ln, inj).items():
            cnt[key][f'crit::{name}'] += ok
  return {'cnt': cnt, 'sweeps': sweeps, 'total_lines': total_lines}


def build_checks(data: dict, tex: str) -> list[tuple[str, bool, str]]:
  cnt, sweeps = data['cnt'], data['sweeps']
  g426, g25 = 'gemma2-2b-426k', 'gemma2-2b-2.5m'
  llama, qwen = 'llama3.2-1b-524k', 'qwen3-0.6b-16k-ation'
  out: list[tuple[str, bool, str]] = []

  def check(label: str, ok: bool, detail: str = '') -> None:
    out.append((label, bool(ok), detail))

  # Totals.
  check('total sampled lines is 8,640 and the paper says so',
        data['total_lines'] == 8640 and tex_number(8640) in tex, str(data['total_lines']))
  check('36 runs', len(sweeps) == 36, str(len(sweeps)))

  # Insertion.
  first_si = cnt[(g426, 'suppress+inject')]['insert_first']
  base_first = cnt[(g426, 'baseline')]['insert_first']
  check('Gemma 426K first-word insertion 703 under s+i, 0 at baseline, both in the text',
        first_si == 703 and base_first == 0 and '703 of 720' in tex and '0 of 720 at baseline' in tex,
        f'{first_si}/{base_first}')
  check('Llama first-word insertion 470 under s+i, 1 at baseline, both in the text',
        cnt[(llama, 'suppress+inject')]['insert_first'] == 470
        and cnt[(llama, 'baseline')]['insert_first'] == 1
        and '470 of 540' in tex and '1 of 540' in tex)
  tot_any = sum(cnt[(c, 'suppress+inject')]['inserted'] for c in (g426, g25, llama, qwen))
  tot_first = sum(cnt[(c, 'suppress+inject')]['insert_first'] for c in (g426, g25, llama, qwen))
  check('inserted total and first-word total match the text',
        tex_number(tot_any) in tex and tex_number(tot_first) in tex, f'{tot_any}/{tot_first}')

  # Position sweeps.
  n_comp = sum(s['in_composed'] for s in sweeps)
  n_nl = sum(s['is_newline'] for s in sweeps)
  check('sweep peak inside the composed line in every run, never at the newline',
        n_comp == len(sweeps) and n_nl == 0, f'{n_comp} composed / {n_nl} newline')
  lo = min(s['newline_over_floor'] for s in sweeps)
  hi = max(s['newline_over_floor'] for s in sweeps)
  check('newline/floor range is covered by the stated 0.86 to 1.24',
        0.86 <= lo and hi <= 1.24 and '0.86 to 1.24' in tex, f'{lo:.3f}..{hi:.3f}')

  # Registered metric.
  for cell, label in ((g426, 'Gemma 426K'), (llama, 'Llama'), (qwen, 'Qwen3'), (g25, 'Gemma 2.5M')):
    b, s = cnt[(cell, 'baseline')]['inject'], cnt[(cell, 'suppress+inject')]['inject']
    n = cnt[(cell, 'baseline')]['n']
    check(f'{label} registered inject counts {s}/{n} against {b}/{n} appear in the text',
          f'{s}/{n}' in tex and f'{b}/{n}' in tex, f'{s} vs {b}')

  # Sensitivity table rows.
  for name in redirect_criteria('a b c d e', 'zz'):
    row = ' & '.join(str(cnt[(g426, c)][f'crit::{name}']) for c in CONDITIONS)
    check(f'sensitivity row for {name!r}', row in tex, row)

  return out


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('--tex', default='main.tex')
  ap.add_argument('--data', default='data/horizon-power/fullline_*.json')
  args = ap.parse_args()
  paths = [Path(p) for p in sorted(glob.glob(args.data))]
  if not paths:
    print(f'no run files matched {args.data}')
    return 1
  tex = re.sub(r'\s+', ' ', Path(args.tex).read_text(encoding='utf-8'))
  checks = build_checks(gather(paths), tex)
  for label, ok, detail in checks:
    print(('  OK  ' if ok else 'FAIL  ') + label + (f'   [{detail}]' if detail else ''))
  failed = [c for c in checks if not c[1]]
  print(f'\n{len(checks) - len(failed)}/{len(checks)} checks passed')
  return 1 if failed else 0


if __name__ == '__main__':
  raise SystemExit(main())
