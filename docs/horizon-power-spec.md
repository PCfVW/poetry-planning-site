# Composition-horizon power run: specification and registered criteria

**Status**: specification, written 2026-09-11 before any run; executed
2026-09-14 (the machine was not free on the 12th as originally planned).
Everything from "Execution record" down was written after the runs; everything
above it, including the registered criteria, was fixed beforehand and is
unedited. Follow-up item 2 of `review-response-map.md`.
**Paper**: arXiv revision of "Planning or Improvisation?", `main.tex` §4.4 and
Appendix C. Replaces the "Power" and "Content is perturbed" paragraphs and
extends Table 6.
**Harness**: `candle-mi/examples/figure13_newline_steering.rs` (unchanged
source) rebuilt 2026-09-11 against candle-mi `ac64b50` (v0.1.24, which
includes the 2026-09-01 rank-preserving fix to `project_to_vocab`). The July
binary is kept as `figure13_newline_steering.2026-07-13.exe`.
**Driver**: `candle-mi/scripts/run_horizon_power.sh` (resumable; `DRY_RUN=1`
prints the commands). **Analysis**: `Figure-13/scripts/horizon_stats.py`
(`--pool`, `--compare`).

## Why

The submitted composition-horizon test used one prompt per cell and 20
sampled lines per condition. Reviewer yeTd noted, correctly, that this design
cannot separate a 0/20 baseline from anything below 8/20, and that
overlapping intervals do not show equivalence. Two natural-rhyme-rate drops
(Gemma 426K inject-only 9/20 to 1/20; Llama suppress-only 9/20 to 1/20, both
Fisher p = 0.008 uncorrected) were also left unresolved. This run raises the
sample to three or four prompts per cell, 60 lines per condition, three
seeds, so that pooled arms hold 180 to 720 lines.

## Design

Steering position is the line-3 newline (the final prompt token), as before.
Prompts are the first three lines of each validated four-line prompt plus
the line-3 newline; the harness receives them verbatim (`--prompt` is not
truncated by the harness).

| Cell (preset) | s | Inject | Prompts (natural rime) |
|---|---|---|---|
| Gemma 2 2B x mntss 426K | 25 | around, 22:10243 | about (AW1 T), so (OW1), shout (AW1 T), who (UW1) |
| Gemma 2 2B x mntss 2.5M | 10 | can, 25:82839 | same four prompts |
| Llama 3.2 1B x mntss 524K | 25 | that, 14:13043 | free (IY1), new (UW1), more (AO1 R) |
| Qwen3-0.6B x BlueLightAI-dev 16K | 25 | myself, 22:8011 | the -ation prompt only |

The Llama "sat" prompt (AE1 T) is excluded: its natural group contains the
inject word "that", so redirection is undefined there. Qwen3 has one
validated prompt per rhyme family; the -teen family is a different cell and
was the logit-only control, not rerun.

**Suppress features** follow the preset convention: every feature of the
prompt's natural rhyme group in the CLT's phonologically clean scan (decoder
cosine >= 0.3; `plip-rs/outputs/rhyme_pairs_*.json`), the same sets the
136-pair and 44-pair sweeps used.

| Cell | Rime | Suppress features (layer:index) |
|---|---|---|
| Gemma 426K | AW1 T | 16:13725, 25:9385 (preset) |
| Gemma 426K | OW1 | 25:6778, 25:4985, 25:4505, 22:10362, 25:5776, 20:12770, 19:3248 |
| Gemma 426K | UW1 | 25:10073, 23:1548, 25:14014, 18:7484, 19:5076, 23:3304, 25:5927 |
| Gemma 2.5M | AW1 T | 25:57092, 23:49923, 20:77102 (preset) |
| Gemma 2.5M | OW1 | 25:70598, 25:51326, 25:52789, 25:28986, 25:5076, 25:73247, 25:97279, 25:94279, 24:78290, 21:89350, 21:51174, 18:7726, 23:94103 |
| Gemma 2.5M | UW1 | 22:86352, 25:46148, 25:70439, 23:15981, 19:39669, 22:72623, 18:46523, 25:75246, 19:70754 |
| Llama 524K | IY1 | 13:30985, 9:5488, 14:27874, 13:32049 (preset) |
| Llama 524K | UW1 | 14:18284, 15:8165, 11:20779 |
| Llama 524K | AO1 R | 1:5297, 3:22663, 10:18203 |
| Qwen 16K | EY1 SH AH0 N | 23:11154, 20:10987, 14:10719 (preset) |

**Conditions**: baseline, suppress-only, inject-only, suppress+inject (the
harness runs all four). **Sampling**: 60 lines per condition, temperature
0.7, seeds 1, 2, 3 (each seed is one harness run; seeds are pooled as
replicates). **Readouts**: as before, m1 (final-word rime class of each
sampled line, via `newline_steering_classify.py`), m2 (greedy line), m3
(teacher-forced P(inject) and P(natural) at the final-word slot), m4
(position sweep, one per run, unchanged).

**Step 0, stack replication.** Before the power runs, the four preset cells
are rerun exactly as in July (prompt 1, k = 20, seed 42) on the rebuilt
binary. Acceptance: identical greedy lines in all four conditions, and m3
values within 10% of the committed `fullline_*.json`. If either fails, the
run continues on the July binary and the discrepancy is recorded in
Appendix D (stack drift).

## Registered criteria (pooled per cell across prompts and seeds)

Let N be the pooled number of sampled lines per condition (720 for the two
Gemma cells, 540 for Llama, 180 for Qwen).

1. **H1, newline redirect recovered** (the original's claim): the pooled
   inject-group fraction under suppress+inject has a Clopper-Pearson 95%
   lower bound above the pooled baseline's upper bound. Also reported per
   prompt. With N = 720 and a baseline near 0, this separates a true
   redirect rate of about 1.5% or more; the original reports 70%.
2. **H2, plan disruption without redirect** (the registered "partial"
   outcome): for each cell, three condition-versus-baseline contrasts on the
   pooled natural-group rate (suppress-only, inject-only, suppress+inject),
   Fisher exact, two-sided, at alpha = 0.05 / 12 (four cells, three
   contrasts). A drop that passes this is reported as plan disruption; the
   two July drops either replicate at this alpha or are recorded as not
   replicating.
3. **Per-prompt consistency**: a pooled effect is reported as consistent only
   if the sign holds in every prompt of the cell; otherwise as
   prompt-dependent.
4. **Minimum detectable effect**, stated in the paper from N: the smallest
   inject fraction whose lower CI bound clears the baseline's upper bound.

Predictions written before running: H1 fails in every cell (consistent with
the submitted result); H2 is undecided, which is the point of the run. If H1
passes anywhere, the paper's reading (ii) in §7 becomes the primary reading
for that cell and the abstract changes.

## Outputs

`candle-mi/docs/experiments/figure13-newline/power/`:
`replicate_<preset>.json` (step 0), `fullline_<preset>_<label>_s<seed>.json`
(power runs, m1 added in place by the classifier), `run.log` (durations).
Copy to `Figure-13/data/horizon-power/` afterwards.

## Runtime (measured 2026-09-11, RTX 5060 Ti)

Fixed cost per run: 25 s Gemma, about 15 s Llama, 7 s Qwen. Per sampled
line: 1.25 s Gemma 426K, about 0.55 s Llama, 0.25 s Qwen; Gemma 2.5M
assumed 1.5 s. Estimate: step 0 about 3 min; Llama 3 x 3 runs about 30 min;
Gemma 426K 4 x 3 runs about 75 min; Gemma 2.5M about 90 min; Qwen 3 runs
about 3 min. Total about 3 h 20 min, unattended, resumable if interrupted.

## Execution record (2026-09-14)

**Step 0 passed with zero drift.** All four cells were rerun at k = 20,
seed 42 on the rebuilt binary (candle-mi `ac64b50`) and compared against the
committed July files with `horizon_stats.py --compare`: identical greedy
lines in all sixteen conditions, m3 relative differences 0.000, identical
m1 rime-class counts. The 2026-09-01 `project_to_vocab` change did not move
any number in this experiment, so the July results and the new runs are
directly comparable and no stack-drift note is needed in Appendix D.

Step-0 wall clock (k = 20, four conditions, including the m1 classifier):
Gemma 426K 149 s, Gemma 2.5M 154 s, Llama 42 s, Qwen 16K 30 s. These imply
about 1.55 s per sampled line on both Gemma cells, 0.34 s on Llama, 0.29 s
on Qwen. Revised estimate for the 36 power runs at k = 60: Llama about
14 min, Gemma 426K about 79 min, Gemma 2.5M about 80 min, Qwen about 4 min,
total about 3 h. Power runs launched 12:37 local.

**All 36 runs completed 15:36, 179 min total**, no stderr output, every file
carrying four conditions of 60 classified lines, 4 prompts x 3 seeds on both
Gemma cells, 3 x 3 on Llama, 1 x 3 on Qwen. `hmn watch --follow-new` sampled
the adapter every 30 s for the whole run: 360 observations, no spill episode,
shared memory flat at its 159 MiB baseline, peak dedicated 13.7 GiB of the
15.7 GiB limit, the harness steady at 6.0 GiB. Raw data, the two analysis
printouts, and the spill log are in `Figure-13/data/horizon-power/`.

## Results (2026-09-14)

**H1 (newline redirect) fails in all four cells**, as predicted, both on the
raw m1 metric and after the leakage correction below. Pooled inject-group
fractions under suppress+inject: Gemma 426K 38/720, Llama 4/540, Qwen 2/180,
Gemma 2.5M 0/720; no cell's interval clears its baseline's. Minimum
detectable inject fraction: 0.013 (Gemma 2.5M), 0.017 (Llama), 0.050 (Qwen),
0.061 (Gemma 426K, whose baseline is a non-zero 21/720 because the prompts'
natural groups and the `around` group both occur spontaneously). Every cell
therefore excludes the original's 70% redirect by a wide margin, and the
three cells with near-zero baselines exclude anything above about 2%.

**H2 (natural-rate drop) is mostly a hijack artifact and does not survive as
plan disruption.** The July Gemma 426K inject-only drop replicates in pooled
form (220/720 to 164/720, Fisher p = 1.0e-3, below the registered alpha of
0.0042) but its sign is not consistent across the four prompts. The July
Llama suppress-only drop does not replicate at the corrected alpha
(61/540 to 41/540, p = 4.8e-2), though its sign is consistent. Both are
accounted for by the hijack finding below, so neither is reported as plan
disruption.

**Unregistered finding, the sharp one: newline injection hijacks the line's
content without ever redirecting its rhyme.** The injected word appears
somewhere in the composed line in 703/720 samples on Gemma 426K under
suppress+inject (639/720 inject-only) against 5/720 at baseline; 471/540 on
Llama against 19/540; 370/720 on Gemma 2.5M against 9/720. The newline is
therefore *not* causally inert: it changes what gets written in up to 98% of
samples. But splitting the inject-group lines by whether the injected word
also occurs before the final word, or the line has collapsed into repetition
(`scripts/horizon_leakage.py`), leaves **zero clean redirects** under
steering in every cell except a single Qwen line: Gemma 426K 0/720, Llama
0/540, Gemma 2.5M 0/720, Qwen 1/180. Every one of the 38 Gemma 426K
"redirects" is a leak (34) or a collapse (4), typically
`around and around and around.` or `Around the sun, round and round.`

Most tellingly, steering **removes** the genuine redirects that occur
spontaneously: Gemma 426K ends a line in the inject rhyme group cleanly
20/720 times at baseline and 17/720 under suppress-only, but 0/720 under
either condition that injects (Fisher p = 1.7e-6). Injecting at the newline
does not make the model compose toward the injected rhyme; it derails the
line so that the model no longer composes toward any rhyme.

## Paper integration (2026-09-14)

§4.4 rewritten around the insertion-versus-redirection distinction; abstract,
§1 contribution 3, §7 verdicts and readings, reproducibility lesson 3b and
Limitations updated; Table 2 sample sizes revised; Table 6 (pooled results with
insertion counts) and Table 7 (the six-criterion redirect recount) added;
Figure 2's caption extended with the 36-sweep agreement. The recount is
labelled exploratory in the text, in Table 7's caption and in Limitations,
since it was not registered here.

Reproduce the paper's numbers from the committed data:

```
python scripts/horizon_stats.py --pool data/horizon-power/fullline_*.json
python scripts/horizon_leakage.py data/horizon-power/fullline_*.json
python scripts/horizon_sweeps.py  data/horizon-power/fullline_*.json
python scripts/verify_paper_numbers.py      # 17/17, exit 0
```
