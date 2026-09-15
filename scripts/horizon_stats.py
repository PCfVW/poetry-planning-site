"""Exact statistics for the composition-horizon experiment (Appendix C).

Reads the committed ``fullline_*.json`` files and prints, per cell and
condition, the final-word class counts, exact Clopper-Pearson 95% intervals,
Fisher exact tests of each condition against baseline (inject-group and
natural-group rates), and the power of the 20-line design against a range of
true redirect rates. No SciPy dependency: everything is exact binomial
arithmetic in the standard library.

Usage (no GPU, seconds):

  python scripts/horizon_stats.py data/fullline_*.json

Doctests:

  python -m doctest scripts/horizon_stats.py
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from math import comb
from pathlib import Path


def binom_cdf(k: int, n: int, p: float) -> float:
  """P(X <= k) for X ~ Binomial(n, p), computed in log space.

  The direct form, ``sum(comb(n, i) * p**i * ...)``, overflows once ``comb(n, i)``
  exceeds a float: at n = 1260 it raises `OverflowError` rather than returning a
  wrong number, which is how this was caught. Terms are therefore accumulated
  through `math.lgamma`.

  >>> round(binom_cdf(0, 20, 0.14), 3)
  0.049
  >>> round(binom_cdf(384, 1260, 0.3), 6)   # the n that overflowed the old form
  0.656531
  >>> binom_cdf(5, 5, 0.5) == 1.0
  True
  """
  if k >= n:
    return 1.0
  if k < 0:
    return 0.0
  if p <= 0.0:
    return 1.0
  if p >= 1.0:
    return 0.0
  log_p, log_q = math.log(p), math.log1p(-p)
  ln_fact_n = math.lgamma(n + 1)
  total = 0.0
  for i in range(k + 1):
    log_term = (
        ln_fact_n - math.lgamma(i + 1) - math.lgamma(n - i + 1)
        + i * log_p + (n - i) * log_q
    )
    total += math.exp(log_term)
  return min(total, 1.0)


def _bisect(f, lo: float, hi: float) -> float:
  for _ in range(100):
    m = (lo + hi) / 2
    if f(m) > 0:
      lo = m
    else:
      hi = m
  return (lo + hi) / 2


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
  """Exact two-sided binomial confidence interval.

  >>> lo, hi = clopper_pearson(0, 20)
  >>> (round(lo, 3), round(hi, 3))
  (0.0, 0.168)
  >>> lo, hi = clopper_pearson(2, 20)
  >>> (round(lo, 3), round(hi, 3))
  (0.012, 0.317)
  """
  lo = 0.0 if k == 0 else _bisect(lambda p: binom_cdf(k - 1, n, p) - (1 - alpha / 2), 0, 1)
  hi = 1.0 if k == n else _bisect(lambda p: binom_cdf(k, n, p) - alpha / 2, 0, 1)
  return lo, hi


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
  """Two-sided Fisher exact test for the table [[a, b], [c, d]].

  >>> round(fisher_two_sided(0, 20, 2, 18), 3)
  0.487
  >>> round(fisher_two_sided(9, 11, 1, 19), 4)
  0.0084
  """
  n = a + b + c + d
  r1, c1 = a + b, a + c

  def prob(x: int) -> float:
    return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

  p_obs = prob(a)
  lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
  return sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-12)


def separation_threshold(n: int, alpha: float = 0.05) -> int:
  """Smallest k such that the CI of k/n lies above the CI of 0/n.

  >>> separation_threshold(20)
  8
  """
  hi0 = clopper_pearson(0, n, alpha)[1]
  return next(k for k in range(1, n + 1) if clopper_pearson(k, n, alpha)[0] > hi0)


def power_vs_zero(true_rate: float, n: int = 20) -> float:
  """Power to separate k/n from 0/n by CI, at a given true redirect rate.

  >>> round(power_vs_zero(0.7), 2)
  1.0
  >>> round(power_vs_zero(0.3), 2)
  0.23
  """
  kmin = separation_threshold(n)
  return 1 - binom_cdf(kmin - 1, n, true_rate)


def report(path: Path) -> None:
  d = json.loads(path.read_text(encoding='utf-8'))
  conds = {c['condition']: c for c in d['conditions']}
  base = conds['baseline']['m1']
  n = base['n']
  print(f"== {path.name}: {d['clt_repo']} inject '{d['inject_word']}' "
        f"suppress '{d['suppress_word']}' s={d['strength']} n={n}")
  for name, c in conds.items():
    m = c['m1']
    nat, inj, oth = m['natural']['count'], m['inject']['count'], m['other']['count']
    ci_inj = clopper_pearson(inj, n)
    line = (f"  {name:16s} nat {nat:2d} inj {inj:2d} oth {oth:2d}  "
            f"inj CI [{ci_inj[0]:.2f},{ci_inj[1]:.2f}]  "
            f"P(inject)={c['m3_p_inject']:.2e} P(natural)={c['m3_p_natural']:.2e}")
    if name != 'baseline':
      p_inj = fisher_two_sided(base['inject']['count'], n - base['inject']['count'], inj, n - inj)
      p_nat = fisher_two_sided(base['natural']['count'], n - base['natural']['count'], nat, n - nat)
      line += f"  Fisher vs baseline: inject p={p_inj:.3f}, natural p={p_nat:.4f}"
    print(line + f"  greedy={c['greedy_line']!r}")
  m4 = d['m4_position_sweep']
  probs = [p['p_inject'] for p in m4]
  i = probs.index(max(probs))
  print(f"  m4: max P(inject)={max(probs):.3g} at position {i} ({m4[i]['token']!r}); "
        f"at newline ({d['newline_index']}) {probs[d['newline_index']]:.3g}")


CONDITIONS = ('baseline', 'suppress-only', 'inject-only', 'suppress+inject')


def cell_and_label(path: Path) -> tuple[str, str]:
  """Split ``fullline_<preset>_<label>_s<seed>.json`` into (preset, label).

  >>> cell_and_label(Path('fullline_gemma2-2b-426k_so_s2.json'))
  ('gemma2-2b-426k', 'so')
  >>> cell_and_label(Path('fullline_gemma2-2b-426k.json'))
  ('gemma2-2b-426k', 'preset')
  """
  stem = path.stem.removeprefix('fullline_')
  parts = stem.split('_')
  if len(parts) >= 3 and parts[-1].startswith('s') and parts[-1][1:].isdigit():
    return '_'.join(parts[:-2]), parts[-2]
  return stem, 'preset'


def counts(d: dict) -> dict[str, dict[str, int]]:
  """Per condition: natural / inject / other counts and n of the m1 lines."""
  out = {}
  for c in d['conditions']:
    m = c['m1']
    out[c['condition']] = {'natural': m['natural']['count'], 'inject': m['inject']['count'],
                           'other': m['other']['count'], 'n': m['n']}
  return out


def pooled_report(paths: list[Path], alpha_contrasts: int = 12) -> None:
  """Pool m1 counts per cell across prompts and seeds; apply the registered tests."""
  by_cell: dict[str, list[tuple[str, dict]]] = {}
  for p in paths:
    d = json.loads(p.read_text(encoding='utf-8'))
    cell, label = cell_and_label(p)
    by_cell.setdefault(cell, []).append((label, counts(d)))
  alpha = 0.05 / alpha_contrasts
  print(f"Registered tests: H1 = CI separation of pooled inject fractions; "
        f"H2 = Fisher on pooled natural rate at alpha = 0.05/{alpha_contrasts} = {alpha:.4f}")
  for cell, runs in by_cell.items():
    pooled = {c: {'natural': 0, 'inject': 0, 'n': 0} for c in CONDITIONS}
    per_prompt: dict[str, dict] = {}
    for label, cnt in runs:
      pp = per_prompt.setdefault(label, {c: {'natural': 0, 'inject': 0, 'n': 0} for c in CONDITIONS})
      for c in CONDITIONS:
        for k in ('natural', 'inject', 'n'):
          pooled[c][k] += cnt[c][k]
          pp[c][k] += cnt[c][k]
    n = pooled['baseline']['n']
    print(f"\n== {cell}: {len(runs)} runs, {len(per_prompt)} prompts, N = {n} lines per condition")
    b = pooled['baseline']
    b_inj_ci = clopper_pearson(b['inject'], b['n'])
    for c in CONDITIONS:
      r = pooled[c]
      ci_i = clopper_pearson(r['inject'], r['n'])
      ci_n = clopper_pearson(r['natural'], r['n'])
      line = (f"  {c:16s} inject {r['inject']:4d}/{r['n']} [{ci_i[0]:.3f},{ci_i[1]:.3f}]  "
              f"natural {r['natural']:4d}/{r['n']} [{ci_n[0]:.3f},{ci_n[1]:.3f}]")
      if c != 'baseline':
        h1 = ci_i[0] > b_inj_ci[1]
        p_nat = fisher_two_sided(b['natural'], b['n'] - b['natural'], r['natural'], r['n'] - r['natural'])
        signs = [(pp[c]['natural'] / pp[c]['n']) - (pp['baseline']['natural'] / pp['baseline']['n'])
                 for pp in per_prompt.values()]
        consistent = all(s <= 0 for s in signs) or all(s >= 0 for s in signs)
        line += (f"  H1 {'PASS' if h1 else 'fail'}  natural-rate Fisher p={p_nat:.2e} "
                 f"{'(< alpha)' if p_nat < alpha else ''} sign consistent across prompts: {consistent}")
      print(line)
    mde = next((k / n for k in range(1, n + 1) if clopper_pearson(k, n)[0] > b_inj_ci[1]), None)
    print(f"  minimum detectable inject fraction against this baseline: "
          f"{mde:.3f}" if mde is not None else "  (no detectable fraction)")
    print("  per prompt (inject / natural counts per condition):")
    for label, pp in per_prompt.items():
      print("   ", f"{label:8s}", "  ".join(f"{c}: {pp[c]['inject']}/{pp[c]['natural']}/{pp[c]['n']}" for c in CONDITIONS))


def compare(a: Path, b: Path, tol: float = 0.10) -> None:
  """Step-0 acceptance: same greedy lines, m3 within tol (relative)."""
  da = json.loads(a.read_text(encoding='utf-8'))
  db = json.loads(b.read_text(encoding='utf-8'))
  ca = {c['condition']: c for c in da['conditions']}
  cb = {c['condition']: c for c in db['conditions']}
  ok = True
  print(f"== compare {a.name} (reference) vs {b.name}")
  for name in CONDITIONS:
    x, y = ca[name], cb[name]
    same = x['greedy_line'] == y['greedy_line']
    rels = []
    for k in ('m3_p_inject', 'm3_p_natural'):
      ref = x[k]
      rel = abs(y[k] - ref) / ref if ref else float('inf')
      rels.append(rel)
    within = all(r <= tol for r in rels)
    ok &= same and within
    print(f"  {name:16s} greedy {'same' if same else 'DIFFERENT'}; m3 rel. diff "
          f"{rels[0]:.3f} / {rels[1]:.3f} {'ok' if within else 'EXCEEDS ' + str(tol)}")
    if not same:
      print(f"    ref: {x['greedy_line']!r}\n    new: {y['greedy_line']!r}")
  if 'm1' in ca['baseline'] and 'm1' in cb['baseline']:
    for name in CONDITIONS:
      ma, mb = ca[name]['m1'], cb[name]['m1']
      print(f"  {name:16s} m1 nat/inj/other  ref {ma['natural']['count']}/{ma['inject']['count']}/{ma['other']['count']}"
            f"  new {mb['natural']['count']}/{mb['inject']['count']}/{mb['other']['count']}")
  print("  ACCEPT" if ok else "  REJECT: record as stack drift (Appendix D) and rerun on the July binary")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('files', nargs='*')
  ap.add_argument('--n', type=int, default=20, help='lines per arm for the power table')
  ap.add_argument('--pool', action='store_true',
                  help='pool m1 counts per cell across prompts and seeds and apply the registered tests')
  ap.add_argument('--compare', nargs=2, metavar=('REF', 'NEW'),
                  help='step-0 acceptance check of a rerun against a committed fullline JSON')
  args = ap.parse_args()
  if args.compare:
    compare(Path(args.compare[0]), Path(args.compare[1]))
    return
  paths = [Path(p) for pat in args.files for p in sorted(glob.glob(pat))]
  if args.pool:
    pooled_report(paths)
    return
  for p in paths:
    report(p)
  kmin = separation_threshold(args.n)
  print(f"\nPower of the {args.n}-line design: CI separation from 0/{args.n} needs k >= {kmin}")
  for rate in (0.1, 0.2, 0.3, 0.4, 0.5, 0.7):
    print(f"  true redirect rate {rate:.1f}: power {power_vs_zero(rate, args.n):.2f}")
  print(f"  P(k <= 2 | rate 0.7) = {binom_cdf(2, args.n, 0.7):.1e}")


if __name__ == '__main__':
  main()
