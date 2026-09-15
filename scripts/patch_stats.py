"""Registered tests for the newline activation-patching experiment.

Reads the JSON written by candle-mi's `figure13_newline_patch` example and
applies the criteria registered in `docs/patching-spec.md`:

* **Prompt validation** - the unpatched recipient's rhyme rate, which decides
  whether a prompt is usable at all. Patching cannot show a rhyme moving in a
  prompt whose rhyme does not hold.
* **H1, the newline carries a rhyme plan** - does any patch condition raise the
  donor-group fraction of the composed line's final word above the unpatched
  baseline, with Clopper-Pearson intervals that do not overlap?
* **H2, next-token capture without rhyme transfer** - does the patch move the
  line's opening while H1 fails?
* **Insertion** - the composition-horizon runs showed that an intervention at
  this position captures the next token almost deterministically, so any
  apparent rhyme effect is reported next to how often the donor's own words
  simply appear in the line.
* **Row divergence** - the per-layer distance between the donor's and the
  recipient's newline rows, which is what makes a null interpretable.

Phonology is imported from `horizon_leakage.py`, so this experiment and the
composition-horizon experiment classify rhymes identically.

Usage (no GPU, seconds):

  python scripts/patch_stats.py data/patching/patch_*.json

Doctests:

  python -m doctest scripts/patch_stats.py
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from horizon_leakage import classify, final_word, line_words, rime_of  # noqa: E402
from horizon_stats import clopper_pearson, fisher_two_sided  # noqa: E402


def opens_with(line: str, word: str) -> bool:
  """Whether the composed line's first word is `word`.

  >>> opens_with('Around the town, she went about.', 'around')
  True
  >>> opens_with('Her heart was filled with doubt.', 'around')
  False
  """
  ws = line_words(line)
  return bool(ws) and ws[0] == word.strip().lower()


def separates(k_hi: int, n_hi: int, k_lo: int, n_lo: int) -> bool:
  """Whether `k_hi/n_hi`'s exact interval lies wholly above `k_lo/n_lo`'s.

  >>> separates(40, 60, 0, 60)
  True
  >>> separates(3, 60, 1, 60)
  False
  """
  return clopper_pearson(k_hi, n_hi)[0] > clopper_pearson(k_lo, n_lo)[1]


def classify_run(doc: dict, cmu: dict) -> dict[str, collections.Counter]:
  """Per condition, count donor / recipient / other endings and insertions."""
  donor_rime = rime_of(doc['donor_word'], cmu)
  recip_rime = rime_of(doc['recipient_word'], cmu)
  donor_word = doc['donor_word']
  out: dict[str, collections.Counter] = {}
  for cond in doc['conditions']:
    c = collections.Counter()
    for line in cond['sampled_lines']:
      c['n'] += 1
      # `classify` names the natural group first; here the donor plays that role.
      grp = classify(final_word(line), cmu, donor_rime, recip_rime)
      c[{'natural': 'donor', 'inject': 'recipient'}.get(grp, 'other')] += 1
      if opens_with(line, donor_word):
        c['opens_with_donor_word'] += 1
      if donor_word.strip().lower() in line_words(line):
        c['contains_donor_word'] += 1
    out[cond['condition']] = c
  return out


def report(paths: list[Path]) -> None:
  from nltk.corpus import cmudict  # noqa: PLC0415 - heavy optional import
  cmu = cmudict.dict()
  pooled: dict[tuple[str, str, str], collections.Counter] = collections.defaultdict(
      collections.Counter)
  divergence: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
  identity_failures: list[str] = []

  for p in paths:
    doc = json.loads(p.read_text(encoding='utf-8'))
    key_model, key_pair = doc['model'], doc['pair']
    if not doc['identity_check']['passed']:
      identity_failures.append(p.name)
    for cond, counts in classify_run(doc, cmu).items():
      pooled[(key_model, key_pair, cond)] += counts
    divergence[(key_model, key_pair)].extend(
        d['cosine'] for d in doc.get('newline_divergence', []))

  if identity_failures:
    print(f"IDENTITY CONTROL FAILED in {len(identity_failures)} run(s): "
          f"{', '.join(identity_failures)}")
    print("The patch path is unsound on that device; nothing below is usable.\n")
  else:
    print(f"identity control: passed in all {len(paths)} run(s)\n")

  cells = sorted({(m, p) for (m, p, _) in pooled})
  for model, pair in cells:
    base = pooled[(model, pair, 'baseline')]
    n = base['n']
    print(f"== {model}  pair {pair}   (n = {n} sampled lines per condition)")
    rhyme_rate = base['recipient'] / n if n else 0.0
    lo, hi = clopper_pearson(base['recipient'], n)
    verdict = 'usable' if lo > 0.0 else 'PROMPT UNUSABLE (rhyme does not hold)'
    print(f"   prompt validation: unpatched recipient rhymes {base['recipient']}/{n} "
          f"= {rhyme_rate:.2f} [{lo:.3f},{hi:.3f}] -> {verdict}")
    cos = divergence[(model, pair)]
    if cos:
      print(f"   newline rows donor vs recipient: cosine min {min(cos):.4f}, "
            f"median {statistics.median(cos):.4f}")
    print(f"   {'condition':14}{'donor':>7}{'recip':>7}{'other':>7}"
          f"{'opens w/ donor word':>21}{'H1':>6}")
    for cond in ('baseline', 'all-layer', 'single-layer'):
      c = pooled[(model, pair, cond)]
      if not c['n']:
        continue
      h1 = '' if cond == 'baseline' else (
          'PASS' if separates(c['donor'], c['n'], base['donor'], base['n']) else 'fail')
      print(f"   {cond:14}{c['donor']:>7}{c['recipient']:>7}{c['other']:>7}"
            f"{c['opens_with_donor_word']:>13}/{c['n']:<7}{h1:>6}")
    for cond in ('all-layer', 'single-layer'):
      c = pooled[(model, pair, cond)]
      if not c['n']:
        continue
      p_donor = fisher_two_sided(base['donor'], base['n'] - base['donor'],
                                 c['donor'], c['n'] - c['donor'])
      p_open = fisher_two_sided(
          base['opens_with_donor_word'], base['n'] - base['opens_with_donor_word'],
          c['opens_with_donor_word'], c['n'] - c['opens_with_donor_word'])
      print(f"   {cond}: Fisher vs baseline, donor-group p={p_donor:.2e}, "
            f"opens-with-donor-word p={p_open:.2e}")
    mde = next((k / n for k in range(1, n + 1)
                if separates(k, n, base['donor'], base['n'])), None)
    if mde is not None:
      print(f"   minimum detectable donor-group fraction: {mde:.3f}")
    print()


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
  ap.add_argument('files', nargs='+')
  args = ap.parse_args()
  paths = [Path(p) for pat in args.files for p in sorted(glob.glob(pat))]
  if not paths:
    print('no run files matched')
    return
  report(paths)


if __name__ == '__main__':
  main()
