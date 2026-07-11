# PLAN.md

Execute this plan **one step at a time, in order**, and wait for confirmation between
steps before moving to the next. Each step names which role from `AGENTS.md` to act as,
what it may touch, and a "done when" checklist you must satisfy before stopping.

Do not jump ahead to a later step's files. Do not do multiple steps in one pass unless
explicitly told to.

---

## Requirements (source of truth)

See `docs/requirements.md`. That file is the only requirements source — no step should
introduce features not implied by it. Step 0 creates it; every step after that reads
from it rather than from any copy pasted elsewhere.

---

## Step 0 — Project scaffold

**Role:** none in particular — this is plain project setup.
**Touches:** repo root, `pyproject.toml`, empty folders.

`docs/requirements.md` already exists in the repo — do not recreate, overwrite, or
edit it in this step. Treat it as given.

1. Initialize a `uv` project at the repo root (Python 3.13).
2. Add `gradio` as the project's only third-party dependency.
3. Create the folder structure from `AGENTS.md` (`backend/`, `frontend/`, `tests/`),
   each with a `.gitkeep` or nothing if `uv`/git doesn't need placeholders. `docs/`
   already exists (it holds `requirements.md`).

**Done when:** `uv run python -c "import gradio; print(gradio.__version__)"` succeeds,
`backend/`, `frontend/`, `tests/` exist, and `docs/requirements.md` is confirmed present
and untouched.

---

## Step 1 — Design

**Role:** Architecture / Design (AGENTS.md → Role 1)
**Touches:** `docs/design.md` only.
**Reads:** `docs/requirements.md`.

1. Act as Role 1. Read `docs/requirements.md`.
2. Produce a complete design: modules, classes, function/method signatures (no
   implementations) needed to satisfy every requirement.
3. Include the Gradio 6 API guidance and error-handling contract as required by
   Role 1's responsibilities in AGENTS.md.
4. Write the result to `docs/design.md`.

**Done when:** `docs/design.md` exists and satisfies Role 1's "done when" checklist in
AGENTS.md. Stop and show the design for review before continuing to Step 2.

---

## Step 2 — Backend implementation

**Role:** Backend Implementation (AGENTS.md → Role 2)
**Touches:** `backend/*.py` only.
**Reads:** `docs/requirements.md`, `docs/design.md`.

1. Act as Role 2. Implement every module/class/function specified in `docs/design.md`.
2. Standard library only — no third-party imports.
3. Manually exercise the main flows and guardrail cases yourself (`uv run
   backend/<module>.py` or a scratch script) before declaring this step done.

**Done when:** Role 2's "done when" checklist in AGENTS.md is satisfied. Stop and report
what was built (files, classes, any deviations from `docs/design.md` and why) before
continuing to Step 3.

---

## Step 3 — Frontend implementation

**Role:** Frontend Implementation (AGENTS.md → Role 3)
**Touches:** `frontend/app.py`, `frontend/_validate.py` only.
**Reads:** `docs/design.md`, `backend/*.py` (import, don't modify).

1. Act as Role 3. Build `frontend/app.py`: a single-file Gradio 6 UI over the backend,
   single-user, using the specified color palette and correct Gradio 6 API per the
   cheat sheet in AGENTS.md.
2. Build `frontend/_validate.py`: imports `app.py`, constructs the `Blocks` object,
   confirms no error. Must not call `.launch()`.
3. Run `uv run frontend/_validate.py` yourself and confirm it passes.
4. Check the UI in both light and dark mode.

**Done when:** Role 3's "done when" checklist in AGENTS.md is satisfied. Stop and report
before continuing to Step 4.

---

## Step 4 — Testing

**Role:** Testing (AGENTS.md → Role 4)
**Touches:** `tests/test_account.py`, `docs/test_summary.md`, and `backend/*.py` (only
to fix defects tests reveal).
**Reads:** `docs/design.md`, `backend/*.py`.

1. Act as Role 4. Write unit tests for the backend only, using stdlib `unittest`.
2. Cover normal flows and every guardrail case from the requirements.
3. Run the tests. Fix any genuine backend defects and rerun until everything passes.
4. Re-run `uv run frontend/_validate.py` to confirm your backend fixes (if any) didn't
   break the frontend's contract.
5. Write a short pass/fail summary to `docs/test_summary.md`.

**Done when:** Role 4's "done when" checklist in AGENTS.md is satisfied — all tests
pass, the frontend still validates, and `docs/test_summary.md` is accurate.

---

## After Step 4

The project is complete when:
- `docs/requirements.md`, `docs/design.md`, `docs/test_summary.md` all exist and are
  accurate.
- `backend/*.py` implements the full design and passes all unit tests.
- `frontend/app.py` runs, demonstrates every capability, and looks correct in light and
  dark mode.
- `frontend/_validate.py` passes.

Do not add features, folders, or files beyond what these four steps produced without a
new instruction — if something is missing, that's a signal to revisit the relevant step,
not to freelance in a later one.
