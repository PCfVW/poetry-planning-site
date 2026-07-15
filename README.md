# Poetry Planning Site: Stress-Test Artifacts (anonymized review copy)

Companion repository for *"Planning or Improvisation? Stress-Testing the Poetry
Planning Site on Open Models and Open Cross-Layer Transcoders"* (under review).
Names of people, projects, and one upstream library are masked or neutralized
for double-blind review; free-text provenance notes inside data files were
anonymized, measurements were not touched.

## Layout

| Path | Contents |
|---|---|
| `candle-mi/` | Source snapshot of the mechanistic-interpretability library (name masked) with the six experiment programs under `examples/` |
| `scripts/` | Python analysis layer (no GPU required) |
| `data/` | Every committed artifact behind every number in the paper, one directory per experiment |
| `figures/` | The exported figure PDFs and the Wolfram script that produces them |

## Tier 0 — verify (no installation)

Every number in the paper maps to a committed JSON:

| Paper artifact | Data |
|---|---|
| Table 2 (seven cells) | `data/figure13-<cell>/figure13_*_grid*.json` |
| Fig. 1, Fig. 2, appendix strength figure | `figures/fig_*.pdf` |
| §4.1 localization null, App. C | derived from the grids (see Tier 1) |
| §4.1 prompt breadth (8/8) | `data/figure13-controls/breadth_*.json` (+ raw sweeps in `_runs/`) |
| §4.2 census rates, App. C table | `data/figure13-newline/census_*.json(.gz)` |
| §4.3 composition horizon (m1--m4), App. C | `data/figure13-newline/fullline_*.json` |
| §5 inject-only / feature-choice ablations | the `*_inject_only_grid.json` / `*_grid_v2.json` variants per cell |
| §5 random baselines | `data/figure13-controls/random_*.json` |
| §6 contrastive-steering replication | `data/maar-replication/*.json` |
| §6 per-layer transcoder comparison | `data/clt-vs-plt/*.json` |

## Tier 1 — re-derive (Python >= 3.10, minutes, no GPU)

`pip install nltk` (the CMU Pronouncing Dictionary downloads itself on first
use). All four commands below were run from the repository root on this exact
tree; each reproduces the corresponding paper numbers.

```bash
# Table 2, one cell at a time: per-strength profile, best ratio, spike position
python scripts/inspect_grid.py data/figure13-gemma-426k/figure13_out_grid.json

# §4.1 / App. C localization null model (3.3e-8, 2.6e-10, 4.2e-8)
python scripts/newline_localization_null.py

# §4.1 prompt breadth: re-aggregates the raw per-prompt sweeps (8/8, 7.2e-13)
python scripts/breadth_aggregate.py

# §4.3 / App. C m1 tables with exact binomial CIs, one file or several
python scripts/newline_steering_classify.py data/figure13-newline/fullline_*.json
```

The census tables re-derive from the committed classified censuses
(`census_*.json`, the Qwen ones gzipped); their full regeneration from raw
vocabulary scans is Tier 2 (`scripts/newline_census_classify.py` documents the
pipeline). Figures regenerate with Wolfram:
`wolframscript -file figures/make_figures.wl` (optional; the PDFs are committed).

## Tier 2 — regenerate (Rust + GPU + model downloads, hours)

Requirements: Rust >= 1.88, a CUDA GPU with 16 GB VRAM (every experiment in
the paper ran on one consumer RTX 5060 Ti), and HuggingFace access.
**Gemma 2 and Llama 3.2 are gated models**: accept their licenses with your
own HuggingFace account and export `HF_TOKEN`. Qwen3 is ungated. One-time
downloads run 17 to 41 GiB per (model, CLT) cell.

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

## Conventions

Python: 2-space indentation, lines <= 100, PEP-604 type hints, doctests as the
correctness gate for pure helpers, argparse with kebab-case flags. Rust: the
crate's lint posture is declared in `candle-mi/Cargo.toml` (`#![deny(warnings)]`
plus clippy pedantic/nursery).

## License

MIT (see `LICENSE`). Anonymous Authors, 2026.
