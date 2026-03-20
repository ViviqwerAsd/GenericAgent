# CLI Onboarding And Model Management Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-run CLI onboarding flow that writes `mykey.py`, rename `/llm` to `/model`, and support adding models later through `/model /add`.

**Architecture:** Keep onboarding and model management inside `cli.py` so the terminal frontend owns the interactive setup experience. Add focused unit tests around config serialization, command routing, and onboarding prompts, then minimally extend `agentmain.py` with a refresh path so new configs take effect without restarting.

**Tech Stack:** Python, `unittest`, `prompt_toolkit`, file I/O, existing `mykey.py` config format

---

### Task 1: Define onboarding/config helpers with tests

**Files:**
- Modify: `tests/test_cli_interactions.py`
- Modify: `cli.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- vendor-to-config serialization for OpenAI / Anthropic / Gemini / OpenAI-compatible
- `/model` completions replacing `/llm`
- `/model /add` routing into the onboarding flow
- preserving optional bot settings while appending model settings

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: FAIL because the onboarding helpers and `/model` command do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement helpers in `cli.py` to:
- build `mykey.py` content from structured answers
- read/merge existing config snippets
- expose `/model` command completions and `/model /add` handling

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: PASS

### Task 2: Add first-run onboarding flow

**Files:**
- Modify: `cli.py`
- Modify: `agentmain.py`
- Modify: `tests/test_cli_interactions.py`

- [ ] **Step 1: Write the failing test**

Add tests covering:
- missing-model startup entering onboarding flow instead of hard erroring
- onboarding writing a valid `mykey.py`
- onboarding reloading model backends after save

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: FAIL because `cli.py` still exits immediately on missing config.

- [ ] **Step 3: Write minimal implementation**

Implement:
- first-run wizard for model vendor selection and required fields
- optional bot-setup branch
- backend refresh hook after writing config

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: PASS

### Task 3: Verify command UX and docs alignment

**Files:**
- Modify: `cli.py`
- Modify: `README.md`
- Modify: `GETTING_STARTED.md`
- Test: `tests/test_cli_interactions.py`

- [ ] **Step 1: Write the failing test**

Extend tests so `/model` is the only CLI model-management command in help/completion output.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: FAIL because help text/docs still mention `/llm`.

- [ ] **Step 3: Write minimal implementation**

Update:
- CLI help text and command table
- beginner-facing docs to mention `python cli.py` onboarding
- command palette labels to use `/model`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: PASS
