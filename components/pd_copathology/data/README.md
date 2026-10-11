# Data directory

**PPMI participant-level data must never be committed to Git.**

PPMI data is distributed under a data use agreement. Everything in the
subdirectories below stays on your machine only.

| Directory    | Contents                                             | Tracked by Git |
| ------------ | ---------------------------------------------------- | -------------- |
| `raw/`       | **Intentionally unused - must stay empty** (see below) | No           |
| `interim/`   | Cleaned and merged intermediate tables               | No             |
| `processed/` | Model-ready feature and target tables                | No             |
| `splits/`    | Participant-level train/validation/test assignments  | No             |

Only this README and the `.gitkeep` placeholders are tracked. The ignore rules
are in the repository root `.gitignore`.

## Raw PPMI data lives outside the repository

- Raw PPMI data are stored outside this repository, not in `data/raw/`.
- The source location is provided through the `PPMI_DATA_ROOT` environment
  variable. Copy `components/pd_copathology/.env.example` to `.env` and set
  your own local path there; `.env` is ignored by Git.
- The raw source is treated as read-only. Code reads from `PPMI_DATA_ROOT` and
  never writes, renames or edits anything there.
- `data/raw/` is intentionally unused and must remain empty permanently.
  Participant-level PPMI files must never be copied into it "for convenience".
- Only safe aggregate reports (no participant-level rows) may be committed
  later, under `reports/`.

## Rules

- Do not copy PPMI files anywhere in the repository.
- Do not paste participant-level rows into notebooks, reports, issues or
  commit messages. Notebook outputs are stripped on commit by `nbstripout`
  (see the root `.gitattributes`); run `nbstripout --install` once per clone
  to enable it.
- Files written to `reports/` must be aggregate only.
- Run `git status` before every commit and confirm nothing under `data/` is
  staged.

## Provenance

Record here, once the download is done:

- Download date:
- PPMI data release / cut:
- Tables downloaded:
