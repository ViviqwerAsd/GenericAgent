# CLI TUI Frontend Design

## Overview
Replace the Streamlit web frontend with a pure terminal TUI using Rich + prompt_toolkit, providing a Claude Code-like CLI experience.

## Architecture
Single file `cli.py` (~300 lines), parallel to existing `stapp.py`. Zero backend changes.

### Dependencies
- `rich` — Markdown rendering, syntax highlighting, panels, spinners
- `prompt_toolkit` — Input with history, multi-line editing

### Components
```
cli.py
  main()              — Entry: init agent, print banner, enter input loop
  print_banner()      — Logo + LLM info
  input_loop()        — prompt_toolkit loop, dispatches /commands and user queries
  stream_output()     — Consume display_queue, render with Rich Live
  handle_command()    — /stop /new /llm /auto /reinject /help /exit
```

### Backend Integration
Reuse `GeneraticAgent` unchanged:
```python
agent = GeneraticAgent()
threading.Thread(target=agent.run, daemon=True).start()
dq = agent.put_task(user_input)
# consume dq.get() → {next: text} / {done: text}
```

## Output Rendering
Parse agent stream markers for differentiated rendering:

| Content | Rendering |
|---------|-----------|
| `**LLM Running (Turn N)**` | Spinner + blue "Turn N" |
| `🛠️ **正在调用工具:** \`name\`` | Yellow panel header |
| Tool args/results (fenced code) | Syntax-highlighted code |
| `<thinking>` | Dim italic |
| `<summary>` | Green panel |
| Normal markdown | Rich Markdown |

## Slash Commands
```
/help              Show help
/stop              Abort current task
/new               Clear history, start new conversation
/llm               List available LLMs
/llm <n>           Switch to LLM #n
/auto              Toggle autonomous mode
/reinject          Re-inject system prompt
/exit or Ctrl+C    Quit
```

## Input UX
- `> ` prompt via prompt_toolkit
- Arrow keys for history
- Enter to submit, Escape+Enter for multi-line
- Input disabled while agent is running (shows spinner)
