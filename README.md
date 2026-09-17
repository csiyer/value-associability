# Value Associability Project

This project tests how image memorability affects value-based episodic choice, using a task adapted from [Duncan and Shohamy 2016](http://duncanlab.org/wp-content/uploads/2018/04/Duncan_2016.pdf). Participants choose between cards with random values; sometimes a card reappears, and participants can use memory for its value to guide their choice.

## Repo layout

- `tasks/` — task code (jsPsych). `task/` is the main (Duncan & Shohamy-style) version; `task-direct/`, `task-matched/`, `task-mixed/` are variants (direct value-memory test, matched-memorability, mixed-memorability). See `tasks/README.md` for sequence-design details.
- `stimuli/` — THINGS-dataset images selected for high/medium/low memorability, used across all task versions. Rebuild with `stimuli/select_stimuli.py`.
- `data/` — raw + combined participant data for the current preregistered sample, one subfolder per task version (`main/`, `direct/`, `matched_memorability/`, `mixed_memorability/`). Drop raw per-participant CSVs into the matching subfolder as they come in.
- `scripts/` — utilities that operate on `data/`:
  - `combine_data.py` — combines each version's raw CSVs into `data/episodic_choice_data[-<version>].csv`
  - `count_participants.py` — applies exclusion criteria and prints participant counts per task
  - `extract_bonus.py` — prints unpaid participant bonuses per task version
  - `check_sequences.ipynb` — sanity-checks the pre-built trial sequences in `tasks/*/sequences/`
- `analysis/` — statistical analysis and figures, run on the combined CSVs in `data/`. Run R/notebook files with working directory set to `analysis/`.
- `figures/` — output figures, one subfolder per task version, mirroring `data/`.
- `pilot/` — all previously collected data, analyses, and figures, kept for reference. `pilot/episodic-choice-task/` is the direct predecessor of the current `tasks/`+`data/`+`analysis/` setup (before this reorg); `pilot/li_bainbridge_bakkour_2022/` is a reanalysis of external data; `pilot/ALL_PREVIOUS/` holds earlier, now-superseded pilots.
- `archive/` — deprecated/one-off code no longer in active use.

## Workflow for new data

1. Collect data, drop raw per-participant CSVs into the relevant `data/<version>/` subfolder.
2. Run `scripts/combine_data.py` to update the combined per-version CSVs, `scripts/count_participants.py` to check exclusions/N, and `scripts/extract_bonus.py` for participant payment.
3. Run the corresponding script(s)/notebook in `analysis/` to update figures in `figures/`.

## Exclusion criteria

1. Pass AI checks
2. Pass all attention checks
3. Old-trial (or recognition, for the direct task) performance significantly above chance (binomial test)
4. Complete data (see `scripts/count_participants.py` for per-task thresholds)
5. Direct task only: miss rate ≤ 20% on recognition and value-report trials
