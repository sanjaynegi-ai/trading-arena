# AGENTS.md

This file defines the roles, responsibilities, and hard constraints for building this
project. Each role below corresponds to one phase of work in `PLAN.md`. When you (or an
AI coding assistant) pick up a step from the plan, read the matching role section first —
it tells you what you're allowed to touch, what you're not allowed to use, and what
"done" looks like.

There is no orchestration framework involved. Each role is a lens for one phase of a
plain Python project. One person (or one assistant, one step at a time) can execute all
of them.

---

## Project summary

A simple account management system for a trading simulation platform — deposits,
withdrawals, buying/selling shares, portfolio valuation, profit/loss reporting,
transaction history, with balance/holdings guardrails — exposed through a single-user
Gradio dashboard.

Full requirements are captured in `docs/requirements.md` (see PLAN.md Step 0) and must
not be reinterpreted or expanded mid-build — every role builds strictly against that
document plus `docs/design.md` once it exists.

---

## Project structure

```
project/
├── AGENTS.md
├── PLAN.md
├── pyproject.toml            # uv project file
├── backend/
│   └── account.py            # core domain logic — stdlib only
├── frontend/
│   ├── app.py                # Gradio 6 UI, single file
│   └── _validate.py          # constructs app.py's Blocks, no .launch()
├── tests/
│   └── test_account.py       # unittest, stdlib only
└── docs/
    ├── requirements.md
    ├── design.md              # output of Role 1
    └── test_summary.md        # output of Role 4
```

No `dashboard/` folder — the Gradio app in `frontend/` *is* the dashboard, there's no
separate charting/reporting surface. No `memory/` folder — state lives in-process inside
the backend objects for the lifetime of the app; the requirements describe a live
simulation, not a persisted store. If a later requirement calls for saving state across
restarts, add a `storage/` folder and a Step in PLAN.md for it rather than retrofitting
this decision silently.

---

## Global constraints (apply to every role)

- **Python only**, run via `uv run <file>` inside this project's `uv` environment.
- All backend and test code use **only the Python standard library**. No third-party
  packages, no exceptions.
- The frontend uses **Gradio only** as a third-party dependency. No other UI or plotting
  libraries.
- Everything lives flat in its role's folder — don't invent subpackages or `__init__.py`
  hierarchies unless a step explicitly calls for it.
- No network calls, no filesystem persistence, no database, unless a requirement
  explicitly asks for it.
- Every role works from the **design document** (`docs/design.md`) once it exists —
  function signatures, class names, and module boundaries defined there are contracts,
  not suggestions. If a contract turns out to be wrong once you're implementing it,
  fix the design doc and note the change, don't silently diverge from it.
- Success is defined per-role below, but the whole-project success criterion is: **the
  system runs, meets every requirement in `docs/requirements.md`, and the Gradio app
  opens and works.**

---

## Role 1 — Architecture / Design

**Owns:** `docs/design.md`
**Touches nothing else.** Does not write implementation code.

**Responsibilities**
- Read `docs/requirements.md` in full.
- Design the module(s), classes, and functions needed to satisfy every requirement.
- Specify function/method signatures (names, parameters, types, return types) — no
  function bodies, no implementation.
- Decide the shape of the backend's public API precisely enough that the backend
  implementation and the frontend implementation can both be built against it without
  needing to talk to each other.
- Write explicit Gradio 6 UI guidance for whoever builds the frontend (see the cheat
  sheet below) — correct kwargs, correct event-binding pattern, and anything that
  differs from older Gradio versions — since the frontend implementation step won't
  independently research this.
- Call out how errors/invalid operations (overdraft, insufficient shares, unknown
  ticker, etc.) should surface from the backend so the frontend can display them
  cleanly (e.g., raised exceptions with clear messages vs. return codes — pick one and
  say so).

**Output format:** Markdown only, written to `docs/design.md`. No code blocks containing
full implementations — signatures only.

**Done when:** `docs/design.md` exists and fully specifies, in enough detail that Role 2
and Role 3 could work from it without further questions:
- the backend module(s), classes, and every public method's signature
- the error-handling contract
- what `frontend/app.py` needs to import and call
- what `get_share_price(ticker)` looks like (a stub with fixed test prices for AAPL,
  TSLA, GOOGL is expected per the requirements — decide where it lives: on the backend
  module or as a standalone function, and specify its signature)

---

## Role 2 — Backend Implementation

**Owns:** `backend/*.py`
**Does not touch:** `frontend/`, `tests/`. Does not write UI code.

**Responsibilities**
- Implement the module(s), classes, and functions specified in `docs/design.md` exactly
  as designed. If a signature genuinely can't work as specified, fix the design doc and
  explain the change — don't quietly rename things.
- Standard library only. No third-party imports.
- Write clean, readable, well-typed Python (type hints throughout).
- Self-check your own code by running it (`uv run backend/account.py` or a small
  throwaway script) before declaring the step done — don't hand off untested code.

**Done when:** every function/class in `docs/design.md`'s backend section exists in
`backend/`, runs without errors, and manually exercising the main flows (deposit,
withdraw, buy, sell, report holdings, report P&L, list transactions, and the guardrail
cases — overdraft, over-buying, over-selling) behaves as the requirements describe.

---

## Role 3 — Frontend Implementation (Gradio)

**Owns:** `frontend/app.py`, `frontend/_validate.py`
**Does not touch:** `backend/` (import from it, don't modify it), `tests/`.

**Responsibilities**
- Build a single-file Gradio 6 UI (`frontend/app.py`) that demonstrates the backend
  end-to-end, assuming exactly one user.
- Professional, polished, clean layout — this is a demo surface for the whole system,
  not a debug console.
- Color palette: `#ecad0a`, `#209dd7`, `#753991`, plus grays — must read correctly in
  both light and dark mode (don't hardcode colors that only work on a light background;
  use Gradio's theming rather than raw hex where possible, and test both modes).
- Gradio is the **only** third-party import allowed here.
- Write `frontend/_validate.py`: imports `app.py`, constructs the `Blocks` object, and
  confirms it builds without error. **Must not call `.launch()`** — that blocks until
  timeout and will hang the run.
- Run `_validate.py` yourself (`uv run frontend/_validate.py`) and confirm it passes
  before declaring the step done.

### Gradio 6 API cheat sheet (verified against the official migration guide)

Gradio 6 made several breaking changes from 5.x. Build against these directly:

- **Use `gr.Blocks()`** as the top-level container (not the older `gr.Interface`
  shortcut) so layout and multiple components are under your control.
- **Component updates:** don't use the old `Component.update(...)` classmethod pattern —
  it's gone. To change a component's state from an event handler, return a new
  constructed instance of the component (e.g. `return gr.Textbox(value="new text")`) or
  use the standalone `gr.update(...)` helper — do not mix the two idioms in the same
  file.
- **`gr.HTML`:** the `padding` kwarg now defaults to `False` (it used to default to
  `True`). If you want the old spacing, set `padding=True` explicitly.
- **`gr.Dataframe`:** if you use it, `row_count`/`col_count` no longer take the old
  `(3, "fixed")` / `(3, "dynamic")` tuple shorthand for everything — there are now
  separate parameters: `column_count`, `column_limits` (tuple of `(min, max)`), and
  `row_limits` (tuple of `(min, max)`). Use these explicitly rather than the old tuple
  form.
- **`.launch()`:** the old `show_api=True/False` kwarg is gone. Use
  `footer_links=["api", "gradio", "settings"]` (omit for default) or
  `footer_links=["gradio", "settings"]` to hide the API link.
- **Event listeners** (`.click()`, `.change()`, etc.): `show_api` and `api_name=False`
  are gone. Use `api_visibility="public" | "undocumented" | "private"` instead.
- **`cache_examples`:** only accepts `True`/`False` now — the old `"lazy"` string value
  is invalid. If you want lazy caching, pass `cache_examples=True, cache_mode="lazy"`.
- If you reach for `gr.Chatbot`-style multimodal messages (unlikely for this project,
  but noted for completeness): message content is now a structured list mixing text and
  file/image entries, matching OpenAI's message format, rather than the old tuple
  shorthand.

If you hit a Gradio 6 API surface not covered above, check the installed package's own
docstrings/signatures (`python -c "import gradio; help(gradio.X)"`) before guessing —
don't assume 5.x behavior carries over.

**Done when:** `frontend/app.py` runs standalone, demonstrates every backend capability
through the UI, looks correct in both light and dark mode, and `frontend/_validate.py`
runs clean (exits without error, doesn't call `.launch()`).

---

## Role 4 — Testing

**Owns:** `tests/test_account.py`, `docs/test_summary.md`
**May patch:** `backend/*.py`, only to fix defects the tests reveal.
**Does not touch:** `frontend/`.

**Responsibilities**
- Write unit tests for the backend module(s) only — do not test `frontend/app.py`.
- Standard library only: use `unittest`. No `pytest`, no third-party test tools.
- Cover the normal flows (deposit, withdraw, buy, sell, report holdings, report P&L,
  transaction history) and the guardrail/edge cases from the requirements (overdraft
  prevented, can't buy more than affordable, can't sell shares not held).
- Run the tests. If any fail because of a genuine backend defect, fix the backend and
  rerun until everything passes. If a test itself was wrong, fix the test.
- Before finishing, make sure `frontend/_validate.py` still passes — any backend change
  you made must not break the frontend's contract with the backend (same public
  signatures, same behavior for valid inputs).
- Write a short results summary to `docs/test_summary.md`: how many tests, pass/fail
  count, and a one-line note on anything you had to fix.

**Done when:** all unit tests pass, `frontend/_validate.py` still passes after any
backend fixes, and `docs/test_summary.md` reflects the final state accurately.

---

## Working agreement between roles

- Each role's output is the next role's input. Don't skip ahead — Role 2 shouldn't
  invent backend structure that contradicts `docs/design.md`; Role 3 shouldn't guess at
  backend signatures instead of reading `backend/*.py` and `docs/design.md` directly.
- If a later role finds an earlier role's contract is wrong or incomplete, fix the
  earlier artifact (the design doc, or the backend signature) and note why — don't paper
  over it with a workaround in your own layer.
- Nothing here authorizes scope creep. If the requirements are ambiguous, make the
  smallest reasonable interpretation and note the assumption in `docs/design.md` rather
  than guessing silently or expanding scope.
