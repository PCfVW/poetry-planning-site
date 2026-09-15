# Figure-13 Paper Conventions

Conventions for this paper directory: the LaTeX source, the Python analysis
layer in `scripts/`, the Wolfram figure script, and the committed data under
`data/`. The companion crate conventions live in
`candle-mi/CONVENTIONS.md`; anything run through that library follows *that*
document, not this one.

Every rule below is here because breaking it cost time or produced a wrong
number in this project.

## Trigger checklist

| You are about to... | Check |
|---|---|
| Open a data file in Python | [Always pass `encoding='utf-8'`](#always-pass-encodingutf-8) |
| Write a helper in `scripts/` | [Python style](#python-style), [doctests are the gate](#doctests-are-the-gate) |
| Assert a number in the paper | [Every number is machine-checked](#every-number-is-machine-checked) |
| Report a comparison | [Absolute effects, not only ratios](#absolute-effects-not-only-ratios) |
| Run a new experiment | [Register the criteria first](#register-the-criteria-first) |
| Add an analysis after seeing data | [Label post hoc work](#label-post-hoc-work) |
| Edit `main.tex` | [No em-dashes](#no-em-dashes), [never `sed` LaTeX](#never-sed-latex), [tables must not overfull](#tables-must-not-overfull) |
| Cite a repository or a preprint | [Verify every bib entry](#verify-every-bib-entry) |
| Copy results in from a run | [Keep the canonical printouts](#keep-the-canonical-printouts) |

---

## Data and analysis

### Always pass `encoding='utf-8'`

Windows Python defaults to cp1252. Several committed JSONs contain UTF-8 text
(sampled poem lines carry curly quotes and accented characters), so a bare
`json.load(open(path))` raises `UnicodeDecodeError` partway through a sweep.
Every read and write in `scripts/` passes `encoding='utf-8'` explicitly.

> Correct: `json.loads(path.read_text(encoding='utf-8'))`
> Wrong: `json.load(open(path))`

The same applies to files this directory writes: a terminal that renders `É` as
`?` is a display artifact, but a file written without the encoding argument is a
real corruption. Verify with a round-trip read, not by eye.

### Python style

- 2-space indentation, lines at most 100 characters.
- PEP-604 type hints (`str | None`, not `Optional[str]`).
- `argparse` with kebab-case flags.
- Standard library only for the statistics. `horizon_stats.py` implements exact
  Clopper-Pearson intervals and Fisher exact tests in plain Python on purpose,
  so a reader can re-derive a published interval without installing SciPy.
  `nltk` is the one accepted dependency, for the CMU Pronouncing Dictionary.
- No absolute paths and no hard-coded machine names; take paths as arguments and
  glob relative to the working directory.

### Doctests are the gate

Every pure helper carries doctests, and they are the correctness gate rather
than decoration:

```
python -m doctest scripts/<file>.py
```

Doctests must use real values from the data where a real value exists. The
doctest for `extract_rime` uses the actual ARPABET transcription of "around";
the one for `redirect_criteria` uses a line the model actually produced.

### Keep the canonical printouts

Each experiment directory under `data/` carries the exact stdout of the
analysis scripts that produced the paper's numbers (`ANALYSIS_*.txt`), beside
the raw run files. Regenerate them from the committed data, never by hand, so
that a diff shows whether a number moved.

---

## Claims and statistics

### Every number is machine-checked

`scripts/verify_paper_numbers.py` recomputes the composition-horizon quantities
asserted in `main.tex` from `data/horizon-power/` and checks each against the
LaTeX source, exiting non-zero on disagreement. Run it after any edit to §4.4,
Table 6 or Table 7. Extend it when a new experiment lands.

This exists because an earlier paper in this line shipped with main-text and
appendix numbers that disagreed.

### Absolute effects, not only ratios

A ratio over a tiny baseline makes a weak effect look strong. Every steering
result reports the absolute probability, the baseline, and a behavioral readout
alongside any ratio. The paper's effect-size tiers (behavioral, marginal,
logit-only) exist for this reason and any new cell is assigned one.

State what a null design can exclude. Overlapping confidence intervals are not
evidence of equivalence, so a null result is reported with the minimum effect
the sample size could have detected.

### Register the criteria first

Before a GPU run, write a spec in `docs/` containing the design, the decision
criteria, and the predictions, and do not edit anything above the results
section afterwards. `docs/horizon-power-spec.md` is the model: everything from
"Execution record" down was written after the runs, everything above it before,
and the document says so.

Drivers live in the library repository under `scripts/run_*.sh`, are resumable
(skip completed outputs), support `DRY_RUN=1`, and log per-run durations.

### Label post hoc work

An analysis devised after seeing the data is labelled exploratory in the text,
in the relevant table caption, and in Limitations. Where a post hoc criterion
replaces a registered one, report both, and show the conclusion under a range
of criteria rather than the single most favourable.

---

## LaTeX

### No em-dashes

None anywhere in the paper. Use a comma, a colon, or a new sentence. Check with
`grep "—" main.tex` before every build.

### Never `sed` LaTeX

GNU `sed` interprets `\u`, `\l`, `\U`, `\L` and `\E` in the replacement text as
case-conversion directives, so `s/.../\\usepackage[preprint]{acl}/` silently
produces `\Sepackage`. Edit `.tex` files with an editor, and if a scripted edit
is unavoidable use Python with an explicit assertion that the old text was
found.

### Tables must not overfull

The build must be free of `Overfull \hbox` warnings. Narrow a wide table by
reducing `\tabcolsep`, moving to `\footnotesize`, or shortening a column, not
by letting it run into the margin. Check with:

```
grep -n "Overfull" main.log | grep -v Font
```

### Verify every bib entry

Check each entry against its source page before it ships: full author list,
venue, year, identifier. A previous submission in this line cited hallucinated
co-authors. Record the verification date in a comment at the top of
`references.bib`.

---

## Figures

Figures are produced by `scripts/make_figures.wl` from the committed JSONs and
exported as PDF. Font sizes are chosen for the printed scale, not the nominal
canvas: a panel that occupies half a column is typeset at roughly half size, so
its labels must be set correspondingly larger. Reviewers of the first
submission could not read the figures.

Use the Okabe-Ito colourblind-safe palette already defined at the top of the
script, and keep newline tokens in the same colour as their annotation.
