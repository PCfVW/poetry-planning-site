# Poetry Planning Site: Stress-Test Artifacts

Companion repository for *"Planning or Improvisation? Stress-Testing the Poetry
Planning Site on Open Models and Open Cross-Layer Transcoders"*
(Éric Jacopin, 2026). Every number in the paper is backed by a committed
artifact here, and the paper's LaTeX source is in `paper/`.

The paper asks how far the rhyme-planning result of Lindsey et al. (2025,
Figure 13) generalizes to open models and open cross-layer transcoders. Short
answer: the single-effective-position signature reproduces everywhere, but the
effective position is adjacent to emission rather than at the newline, and no
probe recovers a newline-resident plan.

> An earlier version of this repository was an anonymized copy for double-blind
> review at BlackboxNLP 2026. That paper was rejected; this is the
> de-anonymized artifact set for the revised arXiv version, with the
> composition-horizon experiment rerun at 36 times its original sample size.

## Layout

| Path | Contents |
|---|---|
| `paper/` | The paper's LaTeX source and bibliography |
| `candle-mi/` | Source snapshot of the [candle-mi](https://github.com/mi-for-the-rust-of-us/candle-mi) mechanistic-interpretability library, with the experiment programs under `examples/` |
| `scripts/` | Python analysis layer (no GPU required) |
| `data/` | Every committed artifact behind every number in the paper, one directory per experiment |
| `figures/` | The exported figure PDFs and the Wolfram script that produces them |

A full clone is about 200 MB, most of it the dense JumpReLU feature censuses
under `data/figure13-newline/`.

## Tier 0 — verify (no installation)

| Paper artifact | Data |
|---|---|
| Table 3 (seven cells) | `data/figure13-<cell>/figure13_*_grid*.json` |
| Table 5 (newline census rates) | `data/figure13-newline/census_*.json(.gz)` |
| Table 6 (composition horizon) | `data/horizon-power/fullline_*.json` |
| Table 7 (redirect recount) | same files, via `scripts/horizon_leakage.py` |
| Table 8 (pair-level re-analysis) | `data/pairs/suppress_inject_sweep_*.json` |
| Figures 1--3 | `figures/fig_*.pdf` |
| §4.1 localization null and prompt breadth | `data/figure13-controls/breadth_*.json` (+ raw sweeps in `_runs/`) |
| §4.2 random controls, per position | `data/figure13-controls/random_*.json` |
| §5 inject-only / feature-choice ablations | the `*_inject_only_grid.json` / `*_grid_v2.json` variants per cell |
| §6 contrastive-steering replication | `data/maar-replication/*.json` |
| §6 per-layer transcoder comparison | `data/clt-vs-plt/*.json` |

The composition-horizon directory also carries the three canonical analysis
printouts (`ANALYSIS_pooled.txt`, `ANALYSIS_leakage.txt`, `ANALYSIS_sweeps.txt`),
the driver log, and the GPU spill log from the run.

## Tier 1 — re-derive (Python >= 3.10, minutes, no GPU)

`pip install nltk scipy` (the CMU Pronouncing Dictionary downloads itself on
first use). Each command below reproduces the corresponding paper numbers from
this tree.

```bash
# Table 3, one cell at a time: per-strength profile, best ratio, spike position
python scripts/inspect_grid.py data/figure13-gemma-426k/figure13_out_grid.json

# §4.1 / App. C localization null model (3.3e-8, 2.6e-10, 4.2e-8)
python scripts/newline_localization_null.py

# §4.1 prompt breadth: re-aggregates the raw per-prompt sweeps (8/8, 7.2e-13)
python scripts/breadth_aggregate.py

# Table 8: pair-level localization over 444 (prompt, inject) pairs
python scripts/pairs_reanalysis.py data/pairs/suppress_inject_sweep_*.json

# §4.3 steering-feature encoder activity at the censused positions
python scripts/steering_feature_activity.py data/figure13-newline/census_*.json

# Table 6 + the registered H1/H2 tests, pooled over prompts and seeds
python scripts/horizon_stats.py --pool data/horizon-power/fullline_*.json

# Table 7: insertion counts and the six-criterion redirect recount
python scripts/horizon_leakage.py data/horizon-power/fullline_*.json

# Figure 2's claim: 36 position sweeps, peak inside the composed line 36/36
python scripts/horizon_sweeps.py data/horizon-power/fullline_*.json

# Consistency gate: every horizon number asserted in the paper, checked
python scripts/verify_paper_numbers.py --tex paper/main.tex \
    --data 'data/horizon-power/fullline_*.json'
```

The last command exits non-zero if the paper and the data disagree; it passes
17 of 17 checks on this tree. Figures regenerate with Wolfram:
`wolframscript -file figures/make_figures.wl` (optional; the PDFs are
committed).

The Qwen3 censuses are gzipped; regenerating them from raw vocabulary scans is
Tier 2 (`scripts/newline_census_classify.py` documents the pipeline).

## Tier 2 — regenerate (Rust + GPU + model downloads, hours)

Requirements: Rust >= 1.91, a CUDA GPU with 16 GB VRAM (every experiment in the
paper ran on one consumer RTX 5060 Ti), and HuggingFace access.
**Gemma 2 and Llama 3.2 are gated models**: accept their licenses with your own
HuggingFace account and export `HF_TOKEN`. Qwen3 is ungated. One-time downloads
run 17 to 41 GiB per (model, CLT) cell.

The snapshot type-checks as staged:

```bash
cd candle-mi
cargo check --examples --features clt,transformer,mmap
```

Three commands per cell (Appendix B of the paper): pre-cache the model and the
CLT; run the vocabulary scan + CMU filter; run the position-by-strength grid:

```bash
cargo run --release --features clt,transformer,mmap --example vocab_scan -- \
    --model google/gemma-2-2b --clt-repo mntss/clt-gemma-2-2b-426k --output raw.json
python scripts/vocab_scan_cmudict_filter.py raw.json --clean-only-output --output clean.json
cargo run --release --features clt,transformer,mmap --example figure13_planning_poems -- \
    --preset gemma2-2b-426k --strength-grid 0.5,1,2.5,5,10,25,50,100 --output grid.json
```

The same example carries the control flags (`--no-suppress`, `--random-inject`,
`--random-direction`, `--random-init`, `--shuffle-weights`); the newline census
and composition-horizon experiments are `figure13_newline_census` and
`figure13_newline_steering`; the non-CLT baseline is `maar_contrastive_steering`
and the transcoder comparison `clt_vs_plt_planning_site`.

The composition-horizon experiment of §4.4 is driven by
`candle-mi/scripts/run_horizon_power.sh` in the upstream library repository: 36
runs, 8,640 sampled lines, about 3 hours on one RTX 5060 Ti, resumable. Its
registered criteria were fixed before the runs and are reproduced in Appendix C
of the paper.

## Conventions

Python: 2-space indentation, lines <= 100, PEP-604 type hints, doctests as the
correctness gate for pure helpers, argparse with kebab-case flags. Rust: the
crate's lint posture is declared in `candle-mi/Cargo.toml` (`#![deny(warnings)]`
plus clippy pedantic/nursery).

## Citation

```bibtex
@misc{jacopin2026planning,
  title  = {Planning or Improvisation? Stress-Testing the Poetry Planning Site
            on Open Models and Open Cross-Layer Transcoders},
  author = {Jacopin, \'{E}ric},
  year   = {2026},
  eprint = {arXiv},
  note   = {Artifacts: https://github.com/PCfVW/poetry-planning-site}
}
```

## License

Code, scripts and data: MIT (see `LICENSE`), Éric Jacopin, 2026. The paper
source under `paper/` is CC BY 4.0. The bundled `candle-mi/` snapshot keeps its
own dual MIT / Apache-2.0 terms.
