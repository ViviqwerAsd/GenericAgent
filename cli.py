#!/usr/bin/env python3
"""GenericAgent CLI — Claude Code-style terminal interface."""

import importlib.util
import os, signal, sys, re, threading, time, queue, tempfile, subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.syntax import Syntax
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.filters import has_completions
from prompt_toolkit.patch_stdout import patch_stdout

from agentmain import GeneraticAgent

console = Console()
auto_mode = False
last_reply_time = 0
last_auto_trigger_time = None
AUTO_TASK_TEXT = "[AUTO]🤖 用户已经离开超过30分钟，作为自主智能体，请阅读自动化sop，执行自动任务。"
AUTO_IDLE_SECONDS = 1800
AUTO_MIN_INTERVAL = 120
CONFIG_PATH = os.path.join(PROJECT_ROOT, "mykey.py")
MODEL_PROVIDERS = {
    "OpenAI": {
        "prefix": "oai_config",
        "fields": [
            ("apikey", "OpenAI API key", None, True),
            ("apibase", "API base", "https://api.openai.com/v1", False),
            ("model", "Model name", "gpt-5.4", True),
        ],
    },
    "Anthropic": {
        "prefix": "claude_config",
        "fields": [
            ("apikey", "Anthropic API key", None, True),
            ("apibase", "API base", "https://api.anthropic.com", False),
            ("model", "Model name", "claude-sonnet-4-5", True),
        ],
    },
    "Google Gemini": {
        "prefix": "google_config",
        "fields": [
            ("google_api_key", "Google API key", None, True),
            ("model", "Model name", "gemini-2.0-flash-001", True),
        ],
    },
    "xAI": {
        "prefix": "xai_config",
        "fields": [
            ("apikey", "xAI API key", None, True),
            ("apibase", "API base", "https://api.x.ai/v1", False),
            ("model", "Model name", "grok-4-1-fast-non-reasoning", True),
        ],
    },
    "OpenAI-Compatible": {
        "prefix": "oai_config",
        "fields": [
            ("apikey", "API key", None, True),
            ("apibase", "API base", None, True),
            ("model", "Model name", None, True),
        ],
    },
}
BOT_SPECS = {
    "Telegram": [("tg_bot_token", "Bot token"), ("tg_allowed_users", "Your Telegram user ID (comma separated if multiple)")],
    "QQ": [("qq_app_id", "App ID"), ("qq_app_secret", "App Secret"), ("qq_allowed_users", "Allowed user openids (comma separated)")],
    "Feishu": [("fs_app_id", "App ID"), ("fs_app_secret", "App Secret"), ("fs_allowed_users", "Allowed user IDs (comma separated)")],
    "WeCom": [("wecom_bot_id", "Bot ID"), ("wecom_secret", "Bot Secret"), ("wecom_allowed_users", "Allowed user IDs (comma separated)"), ("wecom_welcome_message", "Welcome message")],
    "DingTalk": [("dingtalk_client_id", "Client ID"), ("dingtalk_client_secret", "Client Secret"), ("dingtalk_allowed_users", "Allowed user IDs (comma separated)")],
}

# ── Slash command definitions ───────────────────────────────────────────────

COMMANDS = {
    "/help":     "Show this help",
    "/stop":     "Stop current task",
    "/new":      "Clear history, new conversation",
    "/model":    "List / switch / add models  (/model, /model <n>, /model /add)",
    "/chatbot":  "Start configured chat bots",
    "/auto":     "Toggle autonomous mode",
    "/auto-now": "Trigger idle autonomous task now",
    "/reinject": "Re-inject system prompt",
    "/exit":     "Quit",
}
CHATBOT_SPECS = {
    "Telegram": {"script": os.path.join("frontends", "tgapp.py"), "required": ["tg_bot_token"]},
    "QQ": {"script": os.path.join("frontends", "qqapp.py"), "required": ["qq_app_id", "qq_app_secret"]},
    "Feishu": {"script": os.path.join("frontends", "fsapp.py"), "required": ["fs_app_id", "fs_app_secret"]},
    "WeCom": {"script": os.path.join("frontends", "wecomapp.py"), "required": ["wecom_bot_id", "wecom_secret"]},
    "DingTalk": {"script": os.path.join("frontends", "dingtalkapp.py"), "required": ["dingtalk_client_id", "dingtalk_client_secret"]},
}
CHATBOT_DEPENDENCIES = {
    "Telegram": ["telegram"],
    "QQ": ["botpy"],
    "Feishu": ["lark_oapi"],
    "WeCom": ["wecom_aibot_sdk"],
    "DingTalk": ["dingtalk_stream"],
}
chatbot_processes = {}


class UserCancelled(Exception):
    """Raised when the user aborts an interactive CLI flow."""


# ── Auto-completer ─────────────────────────────────────────────────────────

def get_llm_selector_options(agent):
    """Return structured LLM choices for interactive selection and completion."""
    options = []
    if not agent or not getattr(agent, "llmclient", None):
        return options

    for i, name, active in agent.list_llms():
        marker = "active" if active else "available"
        options.append({
            "index": i,
            "name": name,
            "active": active,
            "command": f"/model {i}",
            "label": f"[{i}] {name} ({marker})",
        })
    return options


def get_model_selector_options(agent):
    options = get_llm_selector_options(agent)
    options.append({
        "index": "/add",
        "name": "Add a new model",
        "active": False,
        "command": "/model /add",
        "label": "[add] Add a new model",
    })
    return options


def get_runtime_model_options(agent, path=CONFIG_PATH):
    values = load_config_values(path)
    entries = get_model_config_entries(values)
    if entries:
        active_index = next((i for i, (_, _, active) in enumerate(agent.list_llms()) if active), None) if agent and getattr(agent, "llmclient", None) else None
        return [{
            "index": idx,
            "name": entry["provider"],
            "active": idx == active_index,
            "command": f"/model {idx}",
            "label": entry["label"],
        } for idx, entry in enumerate(entries)]
    return get_llm_selector_options(agent)


def load_config_values(path=CONFIG_PATH):
    if not os.path.exists(path):
        return {}
    namespace = {}
    with open(path, encoding="utf-8") as f:
        exec(compile(f.read(), path, "exec"), {}, namespace)
    return {k: v for k, v in namespace.items() if not k.startswith("_")}


def is_model_config_key(key, value):
    if key == "sider_cookie" and isinstance(value, str):
        return True
    if not isinstance(value, dict):
        return False
    return key.startswith(("oai_config", "claude_config", "xai_config", "google_config"))


def infer_provider_from_entry(key, value):
    if key.startswith("claude_config"):
        return "Anthropic"
    if key.startswith("xai_config"):
        return "xAI"
    if key.startswith("google_config"):
        return "Google Gemini"
    if key.startswith("oai_config"):
        base = str(value.get("apibase", "")).lower()
        if "openai.com" in base or not base:
            return "OpenAI"
        return "OpenAI-Compatible"
    if key == "sider_cookie":
        return "Sider"
    return "OpenAI-Compatible"


def get_model_config_entries(values):
    default_key = values.get("default_model_key")
    entries = []
    for key, value in values.items():
        if not is_model_config_key(key, value):
            continue
        model_name = value.get("model", key) if isinstance(value, dict) else key
        entries.append({
            "key": key,
            "value": value,
            "provider": infer_provider_from_entry(key, value),
            "model": model_name,
            "is_default": key == default_key,
            "label": f"{key}: {model_name}" + (" [default]" if key == default_key else ""),
        })
    if default_key:
        entries = [entry for entry in entries if entry["key"] == default_key] + [entry for entry in entries if entry["key"] != default_key]
    return entries


def _next_config_key(existing, prefix):
    if prefix not in existing:
        return prefix
    idx = 2
    while f"{prefix}{idx}" in existing:
        idx += 1
    return f"{prefix}{idx}"


def build_model_config_entry(provider, answers, existing):
    spec = MODEL_PROVIDERS[provider]
    key = _next_config_key(existing, spec["prefix"])
    payload = dict(answers)
    return key, payload


def _format_value(value):
    if isinstance(value, dict):
        items = []
        for k, v in value.items():
            items.append(f"    {k!r}: {_format_value(v)},")
        return "{\n" + "\n".join(items) + "\n}"
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(v) for v in value) + "]"
    return repr(value)


def render_config_py(values):
    lines = []
    for key in sorted(values):
        lines.append(f"{key} = {_format_value(values[key])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def save_config_values(values, path=CONFIG_PATH):
    content = render_config_py(values)
    fd, tmp_path = tempfile.mkstemp(prefix="mykey_", suffix=".py", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def parse_csv_list(raw):
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def choose_option(question, options):
    while True:
        answer = interactive_select(question, options)
        if answer in options:
            return answer
        lowered = str(answer).strip().lower()
        for option in options:
            if option.lower() == lowered:
                return option
        console.print(Text("  Please choose one of the listed options.", style="yellow"))


def prompt_text_input(label, default=None, secret=False, allow_empty=False):
    prompt_label = f"{label}"
    if default:
        prompt_label += f" [{default}]"
    prompt_label += ": "
    session = PromptSession()
    while True:
        try:
            answer = session.prompt(HTML(f'<b><style fg="ansicyan">{prompt_label}</style></b>'), is_password=secret).strip()
        except (EOFError, KeyboardInterrupt):
            raise UserCancelled()
        if answer:
            return answer
        if default is not None:
            return default
        if allow_empty:
            return ""
        console.print(Text("  This field is required.", style="yellow"))


def collect_model_answers(provider):
    answers = {}
    for field, label, default, required in MODEL_PROVIDERS[provider]["fields"]:
        answer = prompt_text_input(label, default=default, secret="key" in field.lower(), allow_empty=not required)
        answers[field] = answer
    return answers


def test_model_connection(provider, answers):
    try:
        if provider == "Anthropic":
            from llmcore import ClaudeSession
            session = ClaudeSession(answers)
        elif provider == "Google Gemini":
            from llmcore import GeminiSession
            session = GeminiSession(answers)
        elif provider == "xAI":
            from llmcore import XaiSession
            session = XaiSession(answers)
        else:
            from llmcore import LLMSession
            session = LLMSession(answers)
        response = session.ask("Reply with OK only.", stream=False)
        text = response if isinstance(response, str) else str(response)
        if text.startswith("Error:") or "[GeminiError]" in text:
            return False, text
        return True, text[:200]
    except Exception as exc:
        return False, str(exc)


def finalize_model_setup(agent, provider, answers, existing, tester=None, path=CONFIG_PATH, existing_key=None):
    tester = tester or test_model_connection
    ok, message = tester(provider, answers)
    if ok:
        key = existing_key or build_model_config_entry(provider, answers, existing)[0]
        existing[key] = dict(answers)
        save_config_values(existing, path=path)
        if agent is not None:
            agent.reload_backends()
        console.print(Text(f"  ✓ Connection test passed: {message}", style="green"))
        console.print(Text(f"  ✓ Saved model config to {path}", style="green"))
        return True

    console.print(Text(f"  ✗ Connection test failed: {message}", style="red"))
    choice = choose_option("What do you want to do?", ["Retry", "Save anyway", "Cancel"])
    if choice == "Save anyway":
        key = existing_key or build_model_config_entry(provider, answers, existing)[0]
        existing[key] = dict(answers)
        save_config_values(existing, path=path)
        if agent is not None:
            agent.reload_backends()
        console.print(Text(f"  ✓ Saved model config to {path}", style="green"))
        return True
    return False


def collect_bot_settings():
    updates = {}
    wants_bots = choose_option("Configure chat bot integrations now?", ["Skip for now", "Yes"])
    if wants_bots != "Yes":
        return updates
    while True:
        bot = choose_option("Choose a bot to configure", list(BOT_SPECS.keys()) + ["Done"])
        if bot == "Done":
            return updates
        for field, label in BOT_SPECS[bot]:
            if field.endswith("_users"):
                if bot == "Telegram":
                    raw = prompt_text_input(label, allow_empty=False)
                    updates[field] = parse_csv_list(raw)
                    continue
                updates[field] = ["*"]
                continue
            raw = prompt_text_input(label, allow_empty=False, secret="secret" in field.lower() or "token" in field.lower())
            updates[field] = parse_csv_list(raw) if field.endswith("_users") else raw


def get_configured_chatbots(values):
    configured = []
    for name, spec in CHATBOT_SPECS.items():
        if all(values.get(field) for field in spec["required"]):
            configured.append(name)
    return configured


def get_running_chatbots():
    running = set()
    stale = []
    for name, proc in chatbot_processes.items():
        if proc.poll() is None:
            running.add(name)
        else:
            stale.append(name)
    for name in stale:
        chatbot_processes.pop(name, None)
    for name in CHATBOT_SPECS:
        if find_external_chatbot_pids(name):
            running.add(name)
    return sorted(running)


def _has_config_value(value):
    if isinstance(value, (list, tuple, set)):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip()) if value is not None else False


def find_external_chatbot_pids(name):
    script_path = os.path.join(PROJECT_ROOT, CHATBOT_SPECS[name]["script"])
    current_pid = os.getpid()
    pids = set()
    try:
        result = subprocess.run(
            ["pgrep", "-f", script_path],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid != current_pid:
                    pids.add(pid)
    except Exception:
        return []
    return sorted(pids)


def chatbot_preflight(name, values):
    spec = CHATBOT_SPECS[name]
    issues = []

    for field in spec["required"]:
        if not _has_config_value(values.get(field)):
            issues.append(f"Missing required setting: {field}")

    if not get_model_config_entries(values):
        issues.append("No saved model found. Configure a model first with /model.")

    if name == "Telegram":
        allowed = values.get("tg_allowed_users")
        if not _has_config_value(allowed):
            issues.append("Missing required setting: tg_allowed_users")
        elif "*" in {str(item).strip() for item in (allowed if isinstance(allowed, (list, tuple, set)) else [allowed])}:
            issues.append("Telegram requires your own user_id; tg_allowed_users cannot be ['*'].")

    for module_name in CHATBOT_DEPENDENCIES.get(name, []):
        try:
            found = importlib.util.find_spec(module_name)
        except Exception:
            found = None
        if found is None:
            issues.append(f"Missing Python dependency: {module_name}")

    return not issues, issues


def start_chatbot_process(name, path=CONFIG_PATH):
    spec = CHATBOT_SPECS[name]
    existing = chatbot_processes.get(name)
    if existing and existing.poll() is None:
        console.print(Text(f"  {name} bot is already running.", style="yellow"))
        return True
    if find_external_chatbot_pids(name):
        console.print(Text(f"  {name} bot is already running.", style="yellow"))
        return True
    values = load_config_values(path)
    ok, issues = chatbot_preflight(name, values)
    if not ok:
        console.print(Text(f"  ✗ {name} bot cannot start yet.", style="red"))
        for issue in issues:
            console.print(Text(f"    - {issue}", style="yellow"))
        return False
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, spec["script"])]
    proc = subprocess.Popen(
        cmd,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        cwd=PROJECT_ROOT,
    )
    chatbot_processes[name] = proc
    console.print(Text(f"  ✓ Started {name} bot.", style="green"))
    return True


def stop_chatbot_process(name):
    proc = chatbot_processes.get(name)
    stopped = False
    if not proc or proc.poll() is not None:
        chatbot_processes.pop(name, None)
    else:
        terminator = getattr(proc, "terminate", None)
        if callable(terminator):
            terminator()
            stopped = True
    tracked_pid = getattr(proc, "pid", None) if proc else None
    for pid in find_external_chatbot_pids(name):
        if tracked_pid is not None and pid == tracked_pid:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            stopped = True
        except OSError:
            continue
    chatbot_processes.pop(name, None)
    if not stopped:
        console.print(Text(f"  {name} bot is not running.", style="yellow"))
        return False
    console.print(Text(f"  ✓ Stopped {name} bot.", style="green"))
    return True


def configure_chatbot_settings(path=CONFIG_PATH):
    values = load_config_values(path)
    updates = collect_bot_settings()
    if not updates:
        return False
    values.update(updates)
    save_config_values(values, path=path)
    console.print(Text(f"  ✓ Saved chat bot settings to {path}", style="green"))
    return True


def manage_chatbots(path=CONFIG_PATH, action_selector=None):
    values = load_config_values(path)
    configured = get_configured_chatbots(values)
    running = get_running_chatbots()
    blocked = {
        name: issues
        for name in configured
        for ok, issues in [chatbot_preflight(name, values)]
        if not ok
    }
    actions = ["Status", "Start", "Stop", "Configure", "Cancel"]
    action = action_selector(actions) if action_selector else choose_option("Chat bot panel", actions)
    if action == "Status":
        stopped = [name for name in configured if name not in running]
        ready = [name for name in configured if name not in blocked]
        console.print()
        console.print(Panel(
            Text(
                "Configured: " + (", ".join(configured) if configured else "none") + "\n"
                "Running: " + (", ".join(running) if running else "none") + "\n"
                "Ready to start: " + (", ".join(ready) if ready else "none") + "\n"
                "Configured but stopped: " + (", ".join(stopped) if stopped else "none") + "\n"
                "Blocked: " + (", ".join(f"{name} ({'; '.join(issues)})" for name, issues in blocked.items()) if blocked else "none"),
                style="bold",
            ),
            title="[bold cyan]Chat Bot Status[/bold cyan]",
            border_style="cyan",
        ))
        return {"configured": configured, "running": running, "stopped": stopped, "ready": ready, "blocked": blocked}
    if action == "Start":
        if not configured:
            console.print(Text("  ✗ No configured chat bots found. Add bot settings first.", style="red"))
            return False
        chosen = choose_option("Choose a chat bot to start", configured + ["Cancel"])
        if chosen == "Cancel":
            return False
        return start_chatbot_process(chosen, path=path)
    if action == "Stop":
        if not running:
            console.print(Text("  ✗ No running chat bots.", style="red"))
            return False
        chosen = choose_option("Choose a chat bot to stop", running + ["Cancel"])
        if chosen == "Cancel":
            return False
        return stop_chatbot_process(chosen)
    if action == "Configure":
        return configure_chatbot_settings(path=path)
    return False


def run_model_setup_wizard(agent=None, include_bots=False, path=CONFIG_PATH):
    existing = load_config_values(path)
    existing_keys = {k for k, v in existing.items() if is_model_config_key(k, v)}
    console.print()
    console.print(Panel(Text("Welcome to GenericAgent setup. Let's add your first model.", style="bold"), border_style="cyan", title="[bold cyan]First Run Setup[/bold cyan]"))
    provider = choose_option("Choose a model provider", list(MODEL_PROVIDERS.keys()))
    answers = collect_model_answers(provider)
    if not finalize_model_setup(agent=agent, provider=provider, answers=answers, existing=existing, path=path):
        return None, None
    existing = load_config_values(path)
    current_keys = {k for k, v in existing.items() if is_model_config_key(k, v)}
    new_keys = list(current_keys - existing_keys)
    key = new_keys[0] if new_keys else None
    payload = existing.get(key) if key else None
    if include_bots:
        existing.update(collect_bot_settings())
        save_config_values(existing, path=path)
    return key, payload


def choose_model_entry(values, question, selector=None):
    entries = get_model_config_entries(values)
    if not entries:
        console.print(Text("  ✗ No saved models found.", style="red"))
        return None, entries
    if selector is None:
        selected = interactive_select(question, [entry["label"] for entry in entries])
        chosen = next((entry for entry in entries if entry["label"] == selected), None)
    else:
        selected = selector(entries)
        chosen = selected if isinstance(selected, dict) else next((entry for entry in entries if entry["key"] == selected), None)
    return chosen, entries


def edit_model_config(agent=None, selector=None, tester=None, path=CONFIG_PATH):
    values = load_config_values(path)
    chosen, _ = choose_model_entry(values, "Choose a model to edit", selector=selector)
    if not chosen or not isinstance(chosen["value"], dict):
        return False
    provider = infer_provider_from_entry(chosen["key"], chosen["value"])
    answers = {}
    for field, label, default, required in MODEL_PROVIDERS[provider]["fields"]:
        answers[field] = prompt_text_input(label, default=chosen["value"].get(field, default), secret="key" in field.lower(), allow_empty=not required)
    return finalize_model_setup(agent=agent, provider=provider, answers=answers, existing=values, tester=tester, path=path, existing_key=chosen["key"])


def remove_model_config(agent=None, selector=None, path=CONFIG_PATH):
    values = load_config_values(path)
    chosen, entries = choose_model_entry(values, "Choose a model to remove", selector=selector)
    if not chosen:
        return False
    action = choose_option(f"Remove {chosen['key']}?", ["Remove", "Cancel"])
    if action != "Remove":
        return False
    values.pop(chosen["key"], None)
    if values.get("default_model_key") == chosen["key"]:
        remaining = [entry for entry in entries if entry["key"] != chosen["key"]]
        if remaining:
            values["default_model_key"] = remaining[0]["key"]
        else:
            values.pop("default_model_key", None)
    save_config_values(values, path=path)
    if agent is not None:
        agent.reload_backends()
    console.print(Text(f"  ✓ Removed model {chosen['key']}", style="green"))
    return True


def set_default_model_config(agent=None, selector=None, path=CONFIG_PATH):
    values = load_config_values(path)
    chosen, _ = choose_model_entry(values, "Choose the default model", selector=selector)
    if not chosen:
        return False
    values["default_model_key"] = chosen["key"]
    save_config_values(values, path=path)
    if agent is not None:
        agent.reload_backends()
    console.print(Text(f"  ✓ Default model set to {chosen['key']}", style="green"))
    return True


def build_completions(text, agent=None):
    """Build prompt_toolkit Completion objects for slash commands and /llm options."""
    raw = text or ""
    stripped = raw.lstrip()
    if not stripped.startswith('/'):
        return []

    if stripped.startswith('/llm'):
        stripped = stripped.replace('/llm', '/model', 1)

    if stripped.startswith('/model'):
        suffix = stripped[len('/model'):]
        if suffix == "" or suffix.startswith(" "):
            typed = suffix[1:] if suffix.startswith(" ") else ""
            insert_prefix = "" if suffix.startswith(" ") else " "
            completions = []
            for option in get_runtime_model_options(agent):
                idx_text = str(option["index"])
                if idx_text.startswith(typed):
                    completions.append(Completion(
                        f"{insert_prefix}{idx_text[len(typed):]}",
                        start_position=0,
                        display=option["command"],
                        display_meta=option["name"],
                    ))
            for option in [
                {"index": "/add", "name": "Add a new model", "command": "/model /add"},
                {"index": "/edit", "name": "Edit an existing model", "command": "/model /edit"},
                {"index": "/remove", "name": "Remove a saved model", "command": "/model /remove"},
                {"index": "/default", "name": "Set default model", "command": "/model /default"},
            ]:
                idx_text = str(option["index"])
                if idx_text.startswith(typed):
                    completions.append(Completion(
                        f"{insert_prefix}{idx_text[len(typed):]}",
                        start_position=0,
                        display=option["command"],
                        display_meta=option["name"],
                    ))
            if completions:
                return completions

    completions = []
    for cmd, desc in COMMANDS.items():
        if cmd.startswith(stripped):
            completions.append(Completion(
                cmd[len(stripped):],
                start_position=0,
                display=cmd,
                display_meta=desc,
            ))
    return completions


def build_candidate_completions(text, candidates):
    """Build Completion objects for ask_user candidates while allowing free-form input."""
    typed = text or ""
    completions = []
    for candidate in candidates or []:
        option = str(candidate)
        if option.startswith(typed):
            completions.append(Completion(
                option[len(typed):],
                start_position=0,
                display=option,
            ))
    return completions


def should_trigger_autonomous_task(enabled, last_reply, last_trigger, now=None, idle_seconds=AUTO_IDLE_SECONDS, min_interval=AUTO_MIN_INTERVAL):
    """Return True when idle autonomous mode should enqueue a new task."""
    if not enabled:
        return False
    now = time.time() if now is None else now
    if last_trigger is not None and now - last_trigger < min_interval:
        return False
    if not last_reply:
        return False
    effective_last_reply = last_reply
    return now - effective_last_reply > idle_seconds


def enqueue_autonomous_task(agent):
    """Queue one autonomous task using reflect source."""
    global last_auto_trigger_time
    last_auto_trigger_time = time.time()
    return agent.put_task(AUTO_TASK_TEXT, source="reflect")


def run_task_queue(display_queue, heading=None):
    """Drain a queued task and render its output."""
    global last_reply_time
    console.print()
    if heading:
        console.print(Text(heading, style="bold cyan"))
    try:
        final_text, result = stream_output(display_queue)
    except KeyboardInterrupt:
        console.print(Text("\n  ■ Interrupted.", style="yellow"))
        console.print()
        return None, None
    console.print()
    last_reply_time = int(time.time())
    return final_text, result


def start_idle_monitor(agent, on_trigger=None, poll_interval=5):
    """Start background idle monitor for autonomous mode."""
    def monitor():
        while True:
            time.sleep(poll_interval)
            try:
                now = time.time()
                if agent.is_running:
                    continue
                if should_trigger_autonomous_task(auto_mode, last_reply_time, last_auto_trigger_time, now=now):
                    dq = enqueue_autonomous_task(agent)
                    if on_trigger:
                        on_trigger(dq)
            except Exception as exc:
                console.print(Text(f"[Idle Monitor] Error: {exc}", style="red"))

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    return thread


def select_llm_interactively(agent, llm_selector=None):
    """Select an LLM interactively and switch the active backend."""
    options = get_llm_selector_options(agent)
    if not options:
        console.print(Text("  ✗ No LLM configured.", style="red"))
        return False

    if llm_selector is None:
        labels = [option["label"] for option in options]
        selected = interactive_select("Select an LLM:", labels)
        if not selected:
            return False
        chosen = next((option for option in options if option["label"] == selected), None)
        if not chosen:
            return False
        target_index = chosen["index"]
    else:
        selected = llm_selector(options)
        if selected is None or selected == "":
            return False
        if isinstance(selected, dict):
            target_index = int(selected["index"])
        else:
            target_index = int(selected)

    agent.next_llm(target_index)
    console.print(Text(f"  ✓ Switched to LLM #{target_index}: {agent.get_llm_name()}", style="green"))
    return True


def select_model_interactively(agent, selector=None):
    options = get_runtime_model_options(agent) + [
        {"index": "/edit", "name": "Edit an existing model", "active": False, "command": "/model /edit", "label": "[edit] Edit an existing model"},
        {"index": "/remove", "name": "Remove a saved model", "active": False, "command": "/model /remove", "label": "[remove] Remove a saved model"},
        {"index": "/default", "name": "Set default model", "active": False, "command": "/model /default", "label": "[default] Set default model"},
        {"index": "/add", "name": "Add a new model", "active": False, "command": "/model /add", "label": "[add] Add a new model"},
    ]
    if selector is None:
        labels = [option["label"] for option in options]
        selected = interactive_select("Select a model action:", labels)
        chosen = next((option for option in options if option["label"] == selected), None)
    else:
        selected = selector(options)
        if isinstance(selected, dict):
            chosen = selected
        else:
            chosen = next((option for option in options if option["index"] == selected), None)
    if not chosen:
        return False
    if chosen["index"] == "/add":
        run_model_setup_wizard(agent=agent, include_bots=False)
        return True
    if chosen["index"] == "/edit":
        return edit_model_config(agent=agent)
    if chosen["index"] == "/remove":
        return remove_model_config(agent=agent)
    if chosen["index"] == "/default":
        return set_default_model_config(agent=agent)
    agent.next_llm(int(chosen["index"]))
    console.print(Text(f"  ✓ Switched to model #{chosen['index']}: {agent.get_llm_name()}", style="green"))
    return True

class SlashCompleter(Completer):
    """Auto-complete slash commands as user types."""

    def __init__(self, agent=None):
        self.agent = agent

    def get_completions(self, document, complete_event):
        for completion in build_completions(document.text_before_cursor, self.agent):
            yield completion


class CandidateCompleter(Completer):
    """Auto-complete ask_user candidates while preserving free-form typing."""

    def __init__(self, candidates):
        self.candidates = candidates or []

    def get_completions(self, document, complete_event):
        for completion in build_candidate_completions(document.text_before_cursor, self.candidates):
            yield completion


def create_completion_key_bindings(base_kb=None):
    """Add menu navigation bindings while preserving default prompt behavior."""
    kb = base_kb or KeyBindings()

    @kb.add("down", filter=has_completions)
    def _(event):
        event.current_buffer.complete_next()

    @kb.add("up", filter=has_completions)
    def _(event):
        event.current_buffer.complete_previous()

    return kb


# ── Prompt styles ───────────────────────────────────────────────────────────

PT_STYLE = PTStyle.from_dict({
    'prompt': 'ansicyan bold',
    'bottom-toolbar': 'bg:#1a1a2e #e0e0e0',
    'bottom-toolbar.text': '',
    'completion-menu': 'bg:#10243f #9fd3ff',
    'completion-menu.completion': 'bg:#10243f #9fd3ff',
    'completion-menu.completion.current': 'bg:#1d4f91 #ffffff bold',
    'completion-menu.meta': 'bg:#10243f #6fb7ff',
    'completion-menu.meta.completion.current': 'bg:#1d4f91 #d7ecff',
    'scrollbar.background': 'bg:#10243f',
    'scrollbar.button': 'bg:#2f6db3',
})


# ── Banner ──────────────────────────────────────────────────────────────────

def print_banner(agent):
    console.print()
    title = Text()
    title.append("  ╭─ ", style="dim cyan")
    title.append("GenericAgent", style="bold cyan")
    title.append(" v1.0", style="dim")
    title.append(" ─╮", style="dim cyan")
    console.print(title)

    if agent.llmclient:
        llm_name = agent.get_llm_name()
        count = len(agent.llmclients)
        console.print(Text(f"  │  Model: {llm_name}  ({count} backends)", style="dim"))
    else:
        console.print(Text("  │  Model: not configured", style="bold red"))

    console.print(Text("  │  /help for commands · Esc+Enter for multiline", style="dim"))
    console.print(Text("  ╰─────────────────────────────────────────────╯", style="dim cyan"))
    console.print()


# ── Output rendering ────────────────────────────────────────────────────────

_RE_TURN = re.compile(r'\*\*LLM Running \(Turn (\d+)\) \.\.\.\*\*')
_RE_TOOL = re.compile(r'🛠️ \*\*正在调用工具:\*\* `([^`]+)`\s+📥\*\*参数:\*\*')
_RE_THINKING = re.compile(r'<thinking>(.*?)</thinking>', re.DOTALL)
_RE_SUMMARY = re.compile(r'<summary>(.*?)</summary>', re.DOTALL)


def _preprocess(text):
    """Strip XML tags that Rich Markdown can't handle."""
    text = _RE_THINKING.sub(lambda m: f'\n> *[thinking]* {m.group(1).strip()}\n', text)
    text = _RE_SUMMARY.sub(lambda m: f'\n---\n**Summary:** {m.group(1).strip()}\n---\n', text)
    text = re.sub(r'<file_content>\s*(.*?)\s*</file_content>', r'\n```\n\1\n```', text, flags=re.DOTALL)
    return text


def render_stream(text, is_done=False):
    """Convert agent stream text to a list of Rich renderables."""
    text = _preprocess(text)
    parts = []
    lines = text.split('\n')
    buf = []

    def flush_buf():
        if not buf:
            return
        md_text = '\n'.join(buf).strip()
        if md_text:
            parts.append(Markdown(md_text))
        buf.clear()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Turn marker
        m = _RE_TURN.match(line.strip())
        if m:
            flush_buf()
            parts.append(Text(f"● Turn {m.group(1)}", style="bold blue"))
            parts.append(Text())
            i += 1
            continue

        # Tool call
        m = _RE_TOOL.search(line)
        if m:
            flush_buf()
            tool_name = m.group(1)
            i += 1
            arg_lines = []
            in_fence = False
            while i < len(lines):
                if lines[i].startswith('````'):
                    if in_fence:
                        i += 1
                        break
                    in_fence = True
                    i += 1
                    continue
                if in_fence:
                    arg_lines.append(lines[i])
                else:
                    break
                i += 1
            arg_text = '\n'.join(arg_lines).strip()
            if arg_text:
                content = Syntax(arg_text, "json", theme="monokai", word_wrap=True) if arg_text.lstrip().startswith('{') else Text(arg_text, style="dim")
                parts.append(Panel(
                    content,
                    title=f"[yellow]tool:[/yellow] [bold yellow]{tool_name}[/bold yellow]",
                    border_style="yellow",
                    padding=(0, 1),
                ))
            else:
                parts.append(Text(f"  tool: {tool_name}", style="bold yellow"))
            continue

        # Tool result block (````` fenced)
        if line.strip().startswith('`````'):
            flush_buf()
            i += 1
            result_lines = []
            while i < len(lines):
                if lines[i].strip().startswith('`````'):
                    i += 1
                    break
                result_lines.append(lines[i])
                i += 1
            result_text = '\n'.join(result_lines).strip()
            if result_text:
                display = result_text if len(result_text) < 2000 else result_text[:2000] + "\n... (truncated)"
                parts.append(Panel(
                    Text(display, style="dim green"),
                    title="[green]result[/green]",
                    border_style="green",
                    padding=(0, 1),
                ))
            continue

        buf.append(line)
        i += 1

    flush_buf()

    if not is_done:
        parts.append(Text(" ▌", style="blink bold cyan"))

    return parts


def stream_output(display_queue):
    """Consume display_queue and render with Rich Live. Returns (final_text, result_dict)."""
    with Live(console=console, refresh_per_second=6, vertical_overflow="visible") as live:
        while True:
            try:
                item = display_queue.get(timeout=0.3)
            except queue.Empty:
                continue

            if 'done' in item:
                renderables = render_stream(item['done'], is_done=True)
                live.update(Group(*renderables))
                return item['done'], item.get('result')

            if 'next' in item:
                renderables = render_stream(item['next'], is_done=False)
                live.update(Group(*renderables))


# ── Interactive selection (for ask_user) ────────────────────────────────────

def interactive_select(question, candidates):
    """Show candidates as a numbered selectable list. Returns user's choice text."""
    console.print()
    console.print(Panel(
        Text(question, style="bold"),
        title="[bold magenta]Agent needs your input[/bold magenta]",
        border_style="magenta",
        padding=(0, 1),
    ))

    if candidates:
        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("key", style="bold cyan", width=4)
        table.add_column("option")
        for idx, c in enumerate(candidates):
            table.add_row(f"[{idx + 1}]", str(c))
        console.print(table)
        console.print(Text("  Enter number to select, or type a custom answer:", style="dim"))
        console.print()

        # Prompt for selection with dropdown suggestions plus free-form input.
        kb = create_completion_key_bindings()
        session = PromptSession(
            completer=CandidateCompleter(candidates),
            complete_while_typing=True,
            complete_style=CompleteStyle.COLUMN,
            reserve_space_for_menu=min(max(len(candidates), 4), 10),
            key_bindings=kb,
        )
        try:
            answer = session.prompt(
                HTML('<b><style fg="ansimagenta">? </style></b>'),
                pre_run=lambda: session.default_buffer.start_completion(select_first=True),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise UserCancelled()

        # Preserve legacy numeric shortcuts.
        if answer.isdigit():
            idx = int(answer) - 1
            if 0 <= idx < len(candidates):
                selected = str(candidates[idx])
                console.print(Text(f"  → {selected}", style="bold green"))
                return selected

        if answer in {str(candidate) for candidate in candidates}:
            console.print(Text(f"  → {answer}", style="bold green"))
        return answer
    else:
        # Free-form input
        session = PromptSession()
        try:
            answer = session.prompt(
                HTML('<b><style fg="ansimagenta">? </style></b>'),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise UserCancelled()
        return answer


# ── Slash commands ──────────────────────────────────────────────────────────

def handle_command(agent, cmd, llm_selector=None):
    """Handle /commands."""
    global auto_mode, last_reply_time
    parts = cmd.strip().split(None, 1)
    command = parts[0].lower()
    if command == "/llm":
        command = "/model"
    arg = parts[1].strip() if len(parts) > 1 else ""

    try:
        if command == "/help":
            table = Table(show_header=False, box=None, padding=(0, 2, 0, 0), title="Commands", title_style="bold cyan")
            table.add_column("cmd", style="bold white", min_width=14)
            table.add_column("desc", style="dim")
            for cmd_name, desc in COMMANDS.items():
                table.add_row(cmd_name, desc)
            console.print()
            console.print(table)
            console.print()
        elif command == "/stop":
            agent.abort()
            console.print(Text("  ■ Stopped.", style="yellow"))
        elif command == "/new":
            agent.abort()
            agent.history = []
            console.print(Text("  ✓ New conversation started.", style="green"))
        elif command == "/model":
            if arg == "/add":
                run_model_setup_wizard(agent=agent, include_bots=False)
            elif arg == "/edit":
                edit_model_config(agent=agent)
            elif arg == "/remove":
                remove_model_config(agent=agent)
            elif arg == "/default":
                set_default_model_config(agent=agent)
            elif arg:
                try:
                    n = int(arg)
                    agent.next_llm(n)
                    console.print(Text(f"  ✓ Switched to model #{n}: {agent.get_llm_name()}", style="green"))
                except (ValueError, IndexError):
                    console.print(Text(f"  ✗ Invalid model selection: {arg}", style="red"))
            else:
                select_model_interactively(agent, selector=llm_selector)
        elif command == "/chatbot":
            manage_chatbots()
        elif command == "/auto":
            auto_mode = not auto_mode
            if auto_mode and not last_reply_time:
                last_reply_time = int(time.time())
            state, color = ("ON", "green") if auto_mode else ("OFF", "red")
            console.print(Text(f"  Autonomous mode: {state}", style=f"bold {color}"))
        elif command == "/auto-now":
            last_reply_time = int(time.time()) - AUTO_IDLE_SECONDS
            enqueue_autonomous_task(agent)
            console.print(Text("  ✓ Idle autonomous task triggered.", style="green"))
        elif command == "/reinject":
            agent.llmclient.last_tools = ''
            console.print(Text("  ✓ System prompt will be re-injected next turn.", style="green"))
        elif command in ("/exit", "/quit"):
            console.print(Text("  Goodbye.", style="dim"))
            sys.exit(0)
        else:
            console.print(Text(f"  ✗ Unknown command: {command}. Type /help for available commands.", style="red"))
    except UserCancelled:
        console.print(Text("  ↩ Cancelled.", style="yellow"))


# ── Input setup ─────────────────────────────────────────────────────────────

def create_prompt_session(agent):
    """Create prompt_toolkit session with auto-complete and bottom toolbar."""
    kb = KeyBindings()

    @kb.add(Keys.Escape, Keys.Enter)
    def _(event):
        event.current_buffer.insert_text('\n')

    @kb.add("/")
    def _(event):
        event.current_buffer.insert_text("/")
        if event.current_buffer.text == "/":
            event.current_buffer.start_completion(select_first=False)

    @kb.add(" ")
    def _(event):
        event.current_buffer.insert_text(" ")
        if event.current_buffer.text.startswith("/model ") or event.current_buffer.text.startswith("/llm "):
            event.current_buffer.start_completion(select_first=True)

    kb = create_completion_key_bindings(kb)

    def bottom_toolbar():
        llm = agent.get_llm_name() if agent.llmclient else "N/A"
        status = "running" if agent.is_running else "idle"
        status_color = "ansired" if agent.is_running else "ansigreen"
        auto_str = " · auto:ON" if auto_mode else ""
        return HTML(
            f' Model: <b>{llm}</b>'
            f' │ status: <style fg="{status_color}"><b>{status}</b></style>'
            f'{auto_str}'
            f' │ <i>/help</i> for commands'
        )

    session = PromptSession(
        history=InMemoryHistory(),
        key_bindings=kb,
        completer=SlashCompleter(agent),
        complete_while_typing=True,
        complete_style=CompleteStyle.COLUMN,
        reserve_space_for_menu=8,
        multiline=False,
        enable_history_search=True,
        bottom_toolbar=bottom_toolbar,
        style=PT_STYLE,
    )
    return session


# ── Main loop ───────────────────────────────────────────────────────────────

def main():
    global last_reply_time
    agent = GeneraticAgent()
    if agent.llmclient is None:
        try:
            run_model_setup_wizard(agent=agent, include_bots=True)
        except UserCancelled:
            console.print(Text("  ↩ Setup cancelled.", style="yellow"))
        if agent.llmclient is None:
            console.print(Text("  ERROR: No usable model configured.", style="bold red"))
            sys.exit(1)

    threading.Thread(target=agent.run, daemon=True).start()
    start_idle_monitor(agent, on_trigger=lambda dq: run_task_queue(dq, heading="  Autonomous task"))
    print_banner(agent)

    session = create_prompt_session(agent)

    while True:
        try:
            with patch_stdout():
                user_input = session.prompt(
                    HTML('<b><style fg="ansicyan">❯ </style></b>'),
                ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print(Text("\n  Goodbye.", style="dim"))
            break

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith('/'):
            handle_command(agent, user_input)
            continue

        # Send task to agent
        dq = agent.put_task(user_input, source="user")
        final_text, result = run_task_queue(dq)
        if final_text is None and result is None:
            agent.abort()
            continue

        # Handle ask_user interactive selection
        if result and isinstance(result, dict) and result.get('result') == 'EXITED':
            data = result.get('data')
            if isinstance(data, dict) and data.get('status') == 'INTERRUPT':
                ask_data = data.get('data', {})
                question = ask_data.get('question', 'Please provide input:')
                candidates = ask_data.get('candidates', [])
                answer = interactive_select(question, candidates)
                if answer:
                    # Feed answer back as a new task
                    dq = agent.put_task(answer, source="user")
                    final_text, _ = run_task_queue(dq)
                    if final_text is None:
                        agent.abort()


if __name__ == '__main__':
    main()
