"""Separate genuine rhyme redirection from word insertion in the horizon runs.

The m1 metric counts a sampled line as *redirected* when its final word falls in
the injected word's rhyme group. That count is confounded. Steering at the
line-3 newline places the injected word into the composed line (almost always as
its first word); when the line later ends on that same word, or on a rhyme-mate
of it, m1 scores a redirect even though the model never composed toward a rhyme.

This script recomputes the per-line class with the same CMUdict phonology the
reference classifier uses (``newline_steering_classify.py``, which stores only
counts), and reports three things:

1. **Insertion**: how often the injected word appears in the composed line, and
   where (first word / middle / final word only).
2. **Redirect sensitivity**: the inject-group count under six criteria of
   increasing strictness, from the raw m1 count to "the injected word does not
   occur in the line at all", each tested against baseline by Fisher exact.
   The conclusion should not depend on which criterion is chosen.
3. **Composition quality**: mean line length, type/token ratio, and the share of
   lines repeating a word three or more times, to show whether steering degrades
   the line generally or only inserts a word.

The redirect-sensitivity analysis is **post hoc**: it was not part of the
registered criteria in ``docs/horizon-power-spec.md``, which registered the raw
m1 metric. It is reported as exploratory, and the sensitivity table exists so
that the reader can see the result under the registered metric and under every
stricter one.

Self-check: the recomputed natural/inject/other counts must equal the stored m1
counts for every file, verifying that this phonology matches the reference.

Usage (no GPU, seconds):

  python scripts/horizon_leakage.py data/horizon-power/fullline_*.json

Doctests:

  python -m doctest scripts/horizon_leakage.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from horizon_stats import clopper_pearson, fisher_two_sided  # noqa: E402

_LEADING_SPACE = re.compile(r'^[\s▁Ġ]+')
_TRAILING_PUNCT = re.compile(r'[^A-Za-z0-9]+$')
_NON_LETTERS = re.compile(r'[^a-z]')
_WORD = re.compile(r"[A-Za-z']+")

CONDITIONS = ('baseline', 'suppress-only', 'inject-only', 'suppress+inject')


def normalise_token(text: str) -> str | None:
  """Lowercase word suitable for a CMUdict lookup, or None.

  >>> normalise_token(' Paris'), normalise_token('feet.'), normalise_token('123')
  ('paris', 'feet', None)
  """
  cleaned = _LEADING_SPACE.sub('', text)
  cleaned = _TRAILING_PUNCT.sub('', cleaned).lower().strip()
  if not cleaned or _NON_LETTERS.search(cleaned) or len(cleaned) < 2:
    return None
  return cleaned


def extract_rime(pron: list[str]) -> str | None:
  """Rime of an ARPABET pronunciation: last primary-stress vowel onward.

  >>> extract_rime(['F', 'IY1', 'T'])
  'IY1 T'
  >>> extract_rime(['AH0', 'R', 'AW1', 'N', 'D'])
  'AW1 N D'
  """
  last_stressed = last_vowel = -1
  for i, ph in enumerate(pron):
    if ph and ph[-1].isdigit():
      last_vowel = i
      if ph.endswith('1'):
        last_stressed = i
  pivot = last_stressed if last_stressed >= 0 else last_vowel
  return ' '.join(pron[pivot:]) if pivot >= 0 else None


def final_word(line: str) -> str:
  """Final word of a composed line, matching the reference classifier.

  >>> final_word('Around the town, she went about.')
  'about'
  >>> final_word('one line\\nsecond line')
  'line'
  """
  first = line.split('\n', 1)[0]
  parts = _TRAILING_PUNCT.sub('', first).split()
  return parts[-1].lower() if parts else ''


def line_words(line: str) -> list[str]:
  """Lowercased alphabetic words of the line's first physical line.

  >>> line_words("Around and around, round 'n' round.")
  ['around', 'and', 'around', 'round', "'n'", 'round']
  """
  return [w.lower() for w in _WORD.findall(line.split('\n', 1)[0])]


def insertion_site(line: str, inject_word: str) -> str | None:
  """Where the injected word first occurs: 'first', 'middle', 'final', or None.

  >>> insertion_site('Around the town, she went about.', 'around')
  'first'
  >>> insertion_site('She wandered home around.', 'around')
  'final'
  >>> insertion_site('Her heart was filled with doubt.', 'around')
  """
  ws = line_words(line)
  inj = inject_word.strip().lower()
  if inj not in ws:
    return None
  i = ws.index(inj)
  if i == 0:
    return 'first'
  return 'final' if i == len(ws) - 1 else 'middle'


def redirect_criteria(line: str, inject_word: str) -> dict[str, bool]:
  """Six nested criteria for counting an inject-group line as a genuine redirect.

  ``raw`` is the registered m1 metric (no control at all); the others remove
  lines in which the injected word was inserted, with increasing strictness.

  >>> c = redirect_criteria('Around and around and around.', 'around')
  >>> c['raw'], c['not-before-final'], c['absent']
  (True, False, False)
  >>> c = redirect_criteria('Her father was nowhere to be found.', 'around')
  >>> c['raw'], c['not-before-final'], c['absent']
  (True, True, True)
  """
  ws = line_words(line)
  inj = inject_word.strip().lower()
  counts = collections.Counter(ws)
  not_before_final = inj not in ws[:-1]
  distinct, repeats = len(set(ws)), (max(counts.values()) if counts else 0)
  return {
    'raw': True,
    'not-final-word': (ws[-1] != inj) if ws else False,
    'not-before-final': not_before_final,
    'not-before-final + no 3x repeat + 4 distinct':
        not_before_final and repeats < 3 and distinct >= 4,
    'not-before-final + no repeat + 5 distinct':
        not_before_final and repeats < 2 and distinct >= 5,
    'absent': inj not in ws,
  }


CRITERIA = list(redirect_criteria('a b c', 'z').keys())


def rime_of(word: str, cmu: dict) -> str | None:
  norm = normalise_token(word) or word
  variants = cmu.get(norm)
  return extract_rime(variants[0]) if variants else None


def classify(word: str, cmu: dict, natural_rime: str | None, inject_rime: str | None) -> str:
  """Classify a final word into natural / inject / other by CMUdict rime."""
  rime = rime_of(word, cmu)
  if rime is None:
    return 'other'
  if natural_rime is not None and rime == natural_rime:
    return 'natural'
  if inject_rime is not None and rime == inject_rime:
    return 'inject'
  return 'other'


def collect(paths: list[Path], cmu: dict) -> tuple[dict, dict, int]:
  """Aggregate per (cell, condition) counters and line-quality samples."""
  cnt: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
  qual: dict[tuple[str, str], list[tuple[int, float]]] = collections.defaultdict(list)
  mismatches = 0
  for p in paths:
    d = json.loads(p.read_text(encoding='utf-8'))
    inj_word = d['inject_word']
    nat_rime, inj_rime = rime_of(d['suppress_word'], cmu), rime_of(inj_word, cmu)
    for c in d['conditions']:
      key = (d['preset'], c['condition'])
      recomputed = collections.Counter()
      for ln in c['sampled_lines']:
        grp = classify(final_word(ln), cmu, nat_rime, inj_rime)
        recomputed[grp] += 1
        cnt[key][grp] += 1
        cnt[key]['n'] += 1
        ws = line_words(ln)
        if ws:
          qual[key].append((len(ws), len(set(ws)) / len(ws)))
          if max(collections.Counter(ws).values()) >= 3:
            cnt[key]['repeat3'] += 1
          cnt[key]['nonempty'] += 1
        site = insertion_site(ln, inj_word)
        if site is not None:
          cnt[key]['inserted'] += 1
          cnt[key][f'insert_{site}'] += 1
        if grp == 'inject':
          for name, ok in redirect_criteria(ln, inj_word).items():
            if ok:
              cnt[key][f'crit::{name}'] += 1
      stored = c['m1']
      if any(recomputed[g] != stored[g]['count'] for g in ('natural', 'inject', 'other')):
        mismatches += 1
        print(f"  MISMATCH {p.name} / {c['condition']}")
  return cnt, qual, mismatches


def report(paths: list[Path]) -> None:
  from nltk.corpus import cmudict  # noqa: PLC0415 - heavy optional import
  cmu = cmudict.dict()
  cnt, qual, mismatches = collect(paths, cmu)
  print(f"self-check: {len(paths)} files, "
        + ('all conditions match the stored m1 counts'
           if not mismatches else f'{mismatches} MISMATCHES'))
  for cell in sorted({k[0] for k in cnt}):
    base = cnt[(cell, 'baseline')]
    print(f"\n== {cell}   (n = {base['n']} sampled lines per condition)")

    print('  1. insertion of the injected word into the composed line')
    print(f"     {'condition':17}{'contains':>10}{'as 1st word':>13}{'middle':>8}{'final only':>12}")
    for cond in CONDITIONS:
      c = cnt[(cell, cond)]
      print(f"     {cond:17}{c['inserted']:>6}/{c['n']:<4}{c['insert_first']:>13}"
            f"{c['insert_middle']:>8}{c['insert_final']:>12}")

    print('  2. inject-group endings under criteria of increasing strictness'
          ' (Fisher vs baseline)')
    print(f"     {'criterion':46}{'base':>6}{'sup':>6}{'inj':>6}{'s+i':>6}{'p (base vs s+i)':>18}")
    for name in CRITERIA:
      k = f'crit::{name}'
      b, s = base[k], cnt[(cell, 'suppress+inject')][k]
      row = ''.join(f'{cnt[(cell, cond)][k]:>6}' for cond in CONDITIONS)
      p = fisher_two_sided(b, base['n'] - b, s, cnt[(cell, 'suppress+inject')]['n'] - s)
      lo, hi = clopper_pearson(s, cnt[(cell, 'suppress+inject')]['n'])
      print(f"     {name:46}{row}{p:>18.2e}   s+i 95% CI [{lo:.3f},{hi:.3f}]")

    print('  3. composition quality')
    print(f"     {'condition':17}{'mean words':>11}{'type/token':>12}{'word x3+':>12}")
    for cond in CONDITIONS:
      c, q = cnt[(cell, cond)], qual[(cell, cond)]
      print(f"     {cond:17}{statistics.mean(x[0] for x in q):>11.1f}"
            f"{statistics.mean(x[1] for x in q):>12.3f}"
            f"{c['repeat3']:>6}/{c['nonempty']:<5}")
    b_r, b_n = base['repeat3'], base['nonempty']
    s_c = cnt[(cell, 'suppress+inject')]
    print(f"     repetition baseline vs suppress+inject: "
          f"p = {fisher_two_sided(b_r, b_n - b_r, s_c['repeat3'], s_c['nonempty'] - s_c['repeat3']):.2e}")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('files', nargs='+')
  args = ap.parse_args()
  paths = [Path(p) for pat in args.files for p in sorted(glob.glob(pat))]
  report(paths)


if __name__ == '__main__':
  main()
