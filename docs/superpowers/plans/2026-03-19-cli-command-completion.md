# CLI Command Completion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add interactive slash-command dropdowns and direct `/llm` model selection in the terminal CLI.

**Architecture:** Keep the change contained to `cli.py` by extending the existing `prompt_toolkit` completer and routing `/llm` with no numeric argument into an interactive chooser. Add focused unit tests that stub external dependencies so the CLI logic can be verified without requiring the full runtime stack.

**Tech Stack:** Python, `unittest`, `prompt_toolkit` integration points, Rich console output

---

### Task 1: Add focused CLI behavior tests

**Files:**
- Create: `tests/test_cli_interactions.py`
- Test: `tests/test_cli_interactions.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- slash command completions matching `/l` to `/llm`
- `/` showing all slash command options
- `/llm` selection choices being derived from `agent.list_llms()`
- selecting an LLM option invoking `agent.next_llm(index)`

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: FAIL because the new CLI helper functions do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add helper functions in `cli.py` for:
- building slash command completions
- building `/llm` completions from current agent state
- interactive `/llm` selection and switching

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: PASS

### Task 2: Wire interactive behavior into the prompt session

**Files:**
- Modify: `cli.py`
- Test: `tests/test_cli_interactions.py`

- [ ] **Step 1: Write the failing test**

Add/extend tests so `/llm` without a numeric argument routes into chooser behavior instead of only printing strings.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: FAIL because `/llm` still falls back to the old list-print behavior.

- [ ] **Step 3: Write minimal implementation**

Update `handle_command()` and prompt helpers so:
- `/` and `/l` provide dropdown completions
- `/llm` and `/llm ` provide model options navigable by arrow keys
- choosing an option executes the switch immediately

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli_interactions -v`
Expected: PASS
