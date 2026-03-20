# CLI Frontend Rollup

> Summary of the March 2026 CLI/TUI iteration for GenericAgent.

## Scope

This round completed the transition from a basic terminal loop to a guided CLI/TUI frontend with onboarding, command completion, model management, chatbot management, and idle autonomous mode.

## Implemented Changes

### 1. CLI/TUI interaction upgrades

- Added slash-command completion with dropdown suggestions.
- Added `/model` command to replace `/llm` in the main CLI.
- Added interactive model switching, add, edit, remove, and default selection flows.
- Added candidate dropdown selection for `ask_user` prompts.
- Added prompt styling so completion menus fit the CLI theme better.

### 2. First-run onboarding

- `python cli.py` now launches an interactive first-run wizard if no model is configured.
- The wizard guides users through provider selection, `apikey`, `apibase`, and `model`.
- Model setup includes an automatic connection test before saving.
- `mykey.py` is written directly by the wizard, so users do not need to copy `mykey_template.py`.

### 3. Chatbot management

- Added `/chatbot` management panel with `Status`, `Start`, `Stop`, and `Configure`.
- Added chatbot preflight checks for required config, installed dependencies, and model availability.
- Added detection of externally running chatbot processes so the panel reflects real runtime state.
- Added stop support for both tracked subprocesses and externally running chatbot instances.
- Bot configuration now defaults `*_allowed_users` to `['*']` so onboarding can skip that input.

### 4. Autonomous mode

- Completed `/auto` as the idle autonomous mode toggle.
- Added `/auto-now` to trigger one autonomous task immediately.
- Added an idle monitor with cooldown handling in the CLI runtime.

### 5. Documentation and tests

- Added and extended CLI interaction tests for completion, model management, onboarding, and chatbot behavior.
- Updated public docs to describe CLI onboarding, `/model`, and `/chatbot`.

## Key Files

- `cli.py`
- `agentmain.py`
- `llmcore.py`
- `tgapp.py`
- `qqapp.py`
- `fsapp.py`
- `wecomapp.py`
- `dingtalkapp.py`
- `tests/test_cli_interactions.py`

## Verification

- `conda run -n edit-to-learn python -m unittest tests.test_cli_interactions -v`
- `conda run -n edit-to-learn python -m py_compile cli.py tgapp.py qqapp.py fsapp.py wecomapp.py dingtalkapp.py agentmain.py llmcore.py tests/test_cli_interactions.py`
