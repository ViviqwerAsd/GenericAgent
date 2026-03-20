import importlib
import os
import subprocess
import sys
import tempfile
import types
import unittest


def install_cli_stubs():
    rich = types.ModuleType("rich")
    sys.modules.setdefault("rich", rich)

    rich_console = types.ModuleType("rich.console")
    rich_console.Console = type("Console", (), {"print": lambda self, *args, **kwargs: None})
    rich_console.Group = lambda *args: list(args)
    sys.modules["rich.console"] = rich_console

    rich_markdown = types.ModuleType("rich.markdown")
    rich_markdown.Markdown = lambda text: text
    sys.modules["rich.markdown"] = rich_markdown

    rich_panel = types.ModuleType("rich.panel")
    rich_panel.Panel = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    sys.modules["rich.panel"] = rich_panel

    rich_text = types.ModuleType("rich.text")
    rich_text.Text = lambda *args, **kwargs: "".join(str(a) for a in args)
    sys.modules["rich.text"] = rich_text

    rich_live = types.ModuleType("rich.live")

    class Live:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, *args, **kwargs):
            return None

    rich_live.Live = Live
    sys.modules["rich.live"] = rich_live

    rich_syntax = types.ModuleType("rich.syntax")
    rich_syntax.Syntax = lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
    sys.modules["rich.syntax"] = rich_syntax

    rich_table = types.ModuleType("rich.table")

    class Table:
        def __init__(self, *args, **kwargs):
            self.rows = []

        def add_column(self, *args, **kwargs):
            return None

        def add_row(self, *args, **kwargs):
            self.rows.append(args)

    rich_table.Table = Table
    sys.modules["rich.table"] = rich_table

    prompt_toolkit = types.ModuleType("prompt_toolkit")

    class PromptSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def prompt(self, *args, **kwargs):
            return ""

    prompt_toolkit.PromptSession = PromptSession
    sys.modules["prompt_toolkit"] = prompt_toolkit

    history = types.ModuleType("prompt_toolkit.history")
    history.InMemoryHistory = type("InMemoryHistory", (), {})
    sys.modules["prompt_toolkit.history"] = history

    key_binding = types.ModuleType("prompt_toolkit.key_binding")

    class KeyBindings:
        def add(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    key_binding.KeyBindings = KeyBindings
    sys.modules["prompt_toolkit.key_binding"] = key_binding

    keys = types.ModuleType("prompt_toolkit.keys")
    keys.Keys = type("Keys", (), {"Escape": "escape", "Enter": "enter"})
    sys.modules["prompt_toolkit.keys"] = keys

    formatted_text = types.ModuleType("prompt_toolkit.formatted_text")
    formatted_text.HTML = lambda text: text
    sys.modules["prompt_toolkit.formatted_text"] = formatted_text

    completion = types.ModuleType("prompt_toolkit.completion")

    class Completer:
        pass

    class Completion:
        def __init__(self, text, start_position=0, display=None, display_meta=None):
            self.text = text
            self.start_position = start_position
            self.display = display
            self.display_meta = display_meta

    completion.Completer = Completer
    completion.Completion = Completion
    sys.modules["prompt_toolkit.completion"] = completion

    styles = types.ModuleType("prompt_toolkit.styles")
    styles.Style = type("Style", (), {"from_dict": staticmethod(lambda data: data)})
    sys.modules["prompt_toolkit.styles"] = styles

    shortcuts = types.ModuleType("prompt_toolkit.shortcuts")
    shortcuts.CompleteStyle = type("CompleteStyle", (), {"COLUMN": "COLUMN"})
    sys.modules["prompt_toolkit.shortcuts"] = shortcuts

    filters = types.ModuleType("prompt_toolkit.filters")
    filters.has_completions = True
    sys.modules["prompt_toolkit.filters"] = filters

    patch_stdout = types.ModuleType("prompt_toolkit.patch_stdout")

    class patch_stdout_context:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    patch_stdout.patch_stdout = patch_stdout_context
    sys.modules["prompt_toolkit.patch_stdout"] = patch_stdout

    agentmain = types.ModuleType("agentmain")
    agentmain.GeneraticAgent = object
    sys.modules["agentmain"] = agentmain


class DummyAgent:
    def __init__(self):
        self.selected = None
        self.llmclient = types.SimpleNamespace(last_tools="")
        self.tasks = []
        self.is_running = False

    def list_llms(self):
        return [
            (0, "Claude/test-a", False),
            (1, "OpenAI/test-b", True),
            (2, "XAI/test-c", False),
        ]

    def next_llm(self, idx):
        self.selected = idx

    def get_llm_name(self):
        return "OpenAI/test-b"

    def abort(self):
        return None

    def put_task(self, query, source="user", images=None):
        self.tasks.append({"query": query, "source": source, "images": images or []})
        return None

    def reload_backends(self):
        self.llmclient = types.SimpleNamespace(last_tools="")
        return True


class CliInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_cli_stubs()
        cls.cli = importlib.import_module("cli")

    def test_slash_command_completion_matches_model_from_prefix(self):
        completions = self.cli.build_completions("/m", DummyAgent())
        displays = [item.display for item in completions]
        inserted = [item.text for item in completions]
        self.assertIn("/model", displays)
        self.assertIn("odel", inserted)

    def test_root_slash_completion_lists_commands(self):
        completions = self.cli.build_completions("/", DummyAgent())
        displays = [item.display for item in completions]
        self.assertIn("/help", displays)
        self.assertIn("/model", displays)

    def test_model_completion_builds_selectable_model_options(self):
        completions = self.cli.build_completions("/model", DummyAgent())
        displays = [item.display for item in completions]
        inserted = [item.text for item in completions]
        self.assertIn("/model 0", displays)
        self.assertIn("/model /add", displays)
        self.assertIn(" 0", inserted)

    def test_auto_completion_after_slash_prefix_filters_commands(self):
        displays = [item.display for item in self.cli.build_completions("/a", DummyAgent())]
        self.assertEqual(displays, ["/auto", "/auto-now"])

    def test_handle_command_model_without_number_uses_interactive_selector(self):
        agent = DummyAgent()
        chooser_calls = []
        original_runtime_options = self.cli.get_runtime_model_options

        def chooser(options):
            chooser_calls.append(options)
            return 2

        self.cli.get_runtime_model_options = lambda agent, path=None: [
            {"index": 0, "name": "Claude", "active": False, "command": "/model 0", "label": "Claude"},
            {"index": 1, "name": "OpenAI", "active": True, "command": "/model 1", "label": "OpenAI"},
            {"index": 2, "name": "xAI", "active": False, "command": "/model 2", "label": "xAI"},
        ]
        try:
            self.cli.handle_command(agent, "/model", llm_selector=chooser)
        finally:
            self.cli.get_runtime_model_options = original_runtime_options
        self.assertEqual(agent.selected, 2)
        self.assertEqual(len(chooser_calls), 1)
        self.assertEqual(chooser_calls[0][2]["index"], 2)

    def test_handle_command_model_add_runs_setup_wizard(self):
        agent = DummyAgent()
        original = self.cli.run_model_setup_wizard
        calls = []

        def fake_wizard(agent=None, include_bots=False, path=None):
            calls.append((agent, include_bots, path))
            return ("oai_config", {"model": "gpt-5.4"})

        self.cli.run_model_setup_wizard = fake_wizard
        try:
            self.cli.handle_command(agent, "/model /add")
        finally:
            self.cli.run_model_setup_wizard = original

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], agent)

    def test_handle_command_model_edit_runs_edit_flow(self):
        agent = DummyAgent()
        original = self.cli.edit_model_config
        calls = []

        def fake_edit(agent=None, selector=None, tester=None, path=None):
            calls.append((agent, selector, tester, path))
            return True

        self.cli.edit_model_config = fake_edit
        try:
            self.cli.handle_command(agent, "/model /edit")
        finally:
            self.cli.edit_model_config = original

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], agent)

    def test_handle_command_model_remove_runs_remove_flow(self):
        agent = DummyAgent()
        original = self.cli.remove_model_config
        calls = []

        def fake_remove(agent=None, selector=None, path=None):
            calls.append((agent, selector, path))
            return True

        self.cli.remove_model_config = fake_remove
        try:
            self.cli.handle_command(agent, "/model /remove")
        finally:
            self.cli.remove_model_config = original

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], agent)

    def test_handle_command_model_default_runs_default_flow(self):
        agent = DummyAgent()
        original = self.cli.set_default_model_config
        calls = []

        def fake_default(agent=None, selector=None, path=None):
            calls.append((agent, selector, path))
            return True

        self.cli.set_default_model_config = fake_default
        try:
            self.cli.handle_command(agent, "/model /default")
        finally:
            self.cli.set_default_model_config = original

        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][0], agent)

    def test_handle_command_chatbot_starts_selected_bot(self):
        agent = DummyAgent()
        original = self.cli.start_chatbot_process
        calls = []

        def fake_start(name, path=None):
            calls.append((name, path))
            return True

        self.cli.start_chatbot_process = fake_start
        original_choose = self.cli.choose_option
        original_load = self.cli.load_config_values
        choose_answers = iter(["Start", "QQ"])
        self.cli.choose_option = lambda question, options: next(choose_answers)
        self.cli.load_config_values = lambda path=None: {
            "qq_app_id": "1",
            "qq_app_secret": "2",
        }
        try:
            self.cli.handle_command(agent, "/chatbot")
        finally:
            self.cli.start_chatbot_process = original
            self.cli.choose_option = original_choose
            self.cli.load_config_values = original_load

        self.assertEqual(calls, [("QQ", self.cli.CONFIG_PATH)])

    def test_manage_chatbots_status_returns_snapshot(self):
        original_load = self.cli.load_config_values
        original_running = self.cli.get_running_chatbots
        self.cli.load_config_values = lambda path=None: {
            "qq_app_id": "1",
            "qq_app_secret": "2",
        }
        self.cli.get_running_chatbots = lambda: ["QQ"]
        try:
            result = self.cli.manage_chatbots(action_selector=lambda options: "Status")
        finally:
            self.cli.load_config_values = original_load
            self.cli.get_running_chatbots = original_running

        self.assertEqual(result["configured"], ["QQ"])
        self.assertEqual(result["running"], ["QQ"])

    def test_manage_chatbots_stop_stops_selected_running_bot(self):
        calls = []
        original_running = self.cli.get_running_chatbots
        original_stop = self.cli.stop_chatbot_process
        original_choose = self.cli.choose_option
        self.cli.get_running_chatbots = lambda: ["QQ"]
        self.cli.stop_chatbot_process = lambda name: calls.append(name) or True
        choose_answers = iter(["Stop", "QQ"])
        self.cli.choose_option = lambda question, options: next(choose_answers)
        try:
            result = self.cli.manage_chatbots()
        finally:
            self.cli.get_running_chatbots = original_running
            self.cli.stop_chatbot_process = original_stop
            self.cli.choose_option = original_choose

        self.assertTrue(result)
        self.assertEqual(calls, ["QQ"])

    def test_manage_chatbots_configure_invokes_bot_config_flow(self):
        calls = []
        original_configure = self.cli.configure_chatbot_settings
        original_choose = self.cli.choose_option
        self.cli.configure_chatbot_settings = lambda path=None: calls.append(path) or True
        choose_answers = iter(["Configure"])
        self.cli.choose_option = lambda question, options: next(choose_answers)
        try:
            result = self.cli.manage_chatbots()
        finally:
            self.cli.configure_chatbot_settings = original_configure
            self.cli.choose_option = original_choose

        self.assertTrue(result)
        self.assertEqual(calls, [self.cli.CONFIG_PATH])

    def test_collect_bot_settings_defaults_allowed_users_to_public(self):
        original_choose = self.cli.choose_option
        original_prompt = self.cli.prompt_text_input
        choose_answers = iter(["Yes", "Telegram", "Done"])
        prompt_answers = iter(["token-abc"])
        self.cli.choose_option = lambda question, options: next(choose_answers)
        self.cli.prompt_text_input = lambda label, default=None, secret=False, allow_empty=False: next(prompt_answers)
        try:
            updates = self.cli.collect_bot_settings()
        finally:
            self.cli.choose_option = original_choose
            self.cli.prompt_text_input = original_prompt

        self.assertEqual(updates["tg_bot_token"], "token-abc")
        self.assertEqual(updates["tg_allowed_users"], ["*"])

    def test_render_config_preserves_existing_bot_settings_when_adding_model(self):
        values = {
            "tg_bot_token": "abc",
            "tg_allowed_users": ["1"],
        }
        key, payload = self.cli.build_model_config_entry("OpenAI", {
            "apikey": "sk-test",
            "apibase": "https://api.openai.com/v1",
            "model": "gpt-5.4",
        }, values)
        values[key] = payload
        rendered = self.cli.render_config_py(values)
        self.assertIn("tg_bot_token", rendered)
        self.assertIn("oai_config", rendered)
        self.assertIn("gpt-5.4", rendered)

    def test_get_model_config_entries_marks_default(self):
        values = {
            "oai_config": {"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
            "claude_config": {"apikey": "sk-b", "apibase": "https://api.anthropic.com", "model": "claude-sonnet-4-5"},
            "default_model_key": "claude_config",
        }
        entries = self.cli.get_model_config_entries(values)
        self.assertEqual(entries[0]["key"], "claude_config")
        self.assertTrue(entries[0]["is_default"])
        self.assertEqual(entries[1]["key"], "oai_config")

    def test_get_runtime_model_options_uses_saved_configs(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            self.cli.save_config_values({
                "claude_config": {"apikey": "sk-b", "apibase": "https://api.anthropic.com", "model": "claude-sonnet-4-5"},
                "default_model_key": "claude_config",
            }, path=path)
            options = self.cli.get_runtime_model_options(DummyAgent(), path=path)
        self.assertEqual(options[0]["command"], "/model 0")
        self.assertIn("claude-sonnet-4-5", options[0]["label"])

    def test_set_default_model_config_persists_key(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            self.cli.save_config_values({
                "oai_config": {"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                "claude_config": {"apikey": "sk-b", "apibase": "https://api.anthropic.com", "model": "claude-sonnet-4-5"},
            }, path=path)

            self.cli.set_default_model_config(
                agent=DummyAgent(),
                selector=lambda options: next(option for option in options if option["key"] == "claude_config"),
                path=path,
            )
            loaded = self.cli.load_config_values(path=path)
        self.assertEqual(loaded["default_model_key"], "claude_config")

    def test_remove_model_config_deletes_selected_entry(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            self.cli.save_config_values({
                "oai_config": {"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                "claude_config": {"apikey": "sk-b", "apibase": "https://api.anthropic.com", "model": "claude-sonnet-4-5"},
                "default_model_key": "claude_config",
            }, path=path)

            original_choose = self.cli.choose_option
            self.cli.choose_option = lambda question, options: "Remove"
            try:
                self.cli.remove_model_config(
                    agent=DummyAgent(),
                    selector=lambda options: next(option for option in options if option["key"] == "oai_config"),
                    path=path,
                )
            finally:
                self.cli.choose_option = original_choose
            loaded = self.cli.load_config_values(path=path)
        self.assertNotIn("oai_config", loaded)
        self.assertEqual(loaded["default_model_key"], "claude_config")

    def test_configured_chatbots_detects_available_bots(self):
        bots = self.cli.get_configured_chatbots({
            "qq_app_id": "1",
            "qq_app_secret": "2",
            "fs_app_id": "3",
            "fs_app_secret": "4",
        })
        self.assertEqual(bots, ["QQ", "Feishu"])

    def test_chatbot_preflight_reports_missing_telegram_token(self):
        original_find_spec = importlib.util.find_spec
        importlib.util.find_spec = lambda name: object()
        try:
            ok, issues = self.cli.chatbot_preflight("Telegram", {
                "oai_config": {"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                "tg_allowed_users": ["*"],
            })
        finally:
            importlib.util.find_spec = original_find_spec
        self.assertFalse(ok)
        self.assertTrue(any("tg_bot_token" in issue for issue in issues))

    def test_chatbot_preflight_allows_public_telegram_default_when_model_exists(self):
        original_find_spec = importlib.util.find_spec
        importlib.util.find_spec = lambda name: object()
        try:
            ok, issues = self.cli.chatbot_preflight("Telegram", {
                "tg_bot_token": "abc",
                "oai_config": {"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                "tg_allowed_users": ["*"],
            })
        finally:
            importlib.util.find_spec = original_find_spec
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_start_chatbot_process_invokes_script(self):
        original_popen = subprocess.Popen
        calls = []
        original_preflight = self.cli.chatbot_preflight
        original_find = self.cli.find_external_chatbot_pids

        class FakeProc:
            def poll(self):
                return None

        subprocess.Popen = lambda cmd, creationflags=0, cwd=None: calls.append((cmd, creationflags, cwd)) or FakeProc()
        self.cli.chatbot_preflight = lambda name, values: (True, [])
        self.cli.find_external_chatbot_pids = lambda name: []
        try:
            started = self.cli.start_chatbot_process("QQ", path=self.cli.CONFIG_PATH)
        finally:
            subprocess.Popen = original_popen
            self.cli.chatbot_preflight = original_preflight
            self.cli.find_external_chatbot_pids = original_find

        self.assertTrue(started)
        self.assertTrue(calls)
        self.assertTrue(calls[0][0][-1].endswith("qqapp.py"))
        self.assertEqual(calls[0][2], self.cli.PROJECT_ROOT)

    def test_stop_chatbot_process_terminates_running_process(self):
        class FakeProc:
            def __init__(self):
                self.terminated = False

            def poll(self):
                return None

            def terminate(self):
                self.terminated = True

        proc = FakeProc()
        self.cli.chatbot_processes["QQ"] = proc
        try:
            stopped = self.cli.stop_chatbot_process("QQ")
        finally:
            self.cli.chatbot_processes.pop("QQ", None)

        self.assertTrue(stopped)
        self.assertTrue(proc.terminated)

    def test_get_running_chatbots_filters_exited_processes(self):
        class RunningProc:
            def poll(self):
                return None

        class DoneProc:
            def poll(self):
                return 0

        self.cli.chatbot_processes["QQ"] = RunningProc()
        self.cli.chatbot_processes["Feishu"] = DoneProc()
        original_find = self.cli.find_external_chatbot_pids
        self.cli.find_external_chatbot_pids = lambda name: []
        try:
            running = self.cli.get_running_chatbots()
        finally:
            self.cli.find_external_chatbot_pids = original_find
            self.cli.chatbot_processes.clear()

        self.assertEqual(running, ["QQ"])

    def test_get_running_chatbots_includes_external_bot_processes(self):
        original_find = self.cli.find_external_chatbot_pids
        self.cli.find_external_chatbot_pids = lambda name: [123] if name == "QQ" else []
        try:
            running = self.cli.get_running_chatbots()
        finally:
            self.cli.find_external_chatbot_pids = original_find

        self.assertEqual(running, ["QQ"])

    def test_stop_chatbot_process_terminates_external_processes(self):
        original_find = self.cli.find_external_chatbot_pids
        original_kill = self.cli.os.kill
        killed = []
        self.cli.find_external_chatbot_pids = lambda name: [321] if name == "QQ" else []
        self.cli.os.kill = lambda pid, sig: killed.append((pid, sig))
        try:
            stopped = self.cli.stop_chatbot_process("QQ")
        finally:
            self.cli.find_external_chatbot_pids = original_find
            self.cli.os.kill = original_kill

        self.assertTrue(stopped)
        self.assertEqual(len(killed), 1)
        self.assertEqual(killed[0][0], 321)

    def test_finalize_model_setup_saves_after_successful_connection_test(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            agent = DummyAgent()
            saved = self.cli.finalize_model_setup(
                agent=agent,
                provider="OpenAI",
                answers={"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                existing={},
                tester=lambda provider, answers: (True, "ok"),
                path=path,
            )
            loaded = self.cli.load_config_values(path=path)
        self.assertTrue(saved)
        self.assertIn("oai_config", loaded)

    def test_finalize_model_setup_retries_on_failed_connection_before_saving(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            agent = DummyAgent()
            calls = []

            def tester(provider, answers):
                calls.append((provider, answers["model"]))
                return (False, "boom")

            original_choose = self.cli.choose_option
            self.cli.choose_option = lambda question, options: "Cancel"
            try:
                saved = self.cli.finalize_model_setup(
                    agent=agent,
                    provider="OpenAI",
                    answers={"apikey": "sk-a", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
                    existing={},
                    tester=tester,
                    path=path,
                )
            finally:
                self.cli.choose_option = original_choose
        self.assertFalse(saved)
        self.assertEqual(len(calls), 1)
        self.assertFalse(os.path.exists(path))

    def test_save_and_load_config_roundtrip(self):
        values = {
            "oai_config": {"apikey": "sk-test", "apibase": "https://api.openai.com/v1", "model": "gpt-5.4"},
            "tg_allowed_users": ["123"],
        }
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mykey.py")
            self.cli.save_config_values(values, path=path)
            loaded = self.cli.load_config_values(path=path)
        self.assertEqual(loaded["oai_config"]["model"], "gpt-5.4")
        self.assertEqual(loaded["tg_allowed_users"], ["123"])

    def test_ask_user_completion_builds_candidate_options(self):
        completions = self.cli.build_candidate_completions("Op", ["Option A", "Other"])
        displays = [item.display for item in completions]
        inserted = [item.text for item in completions]
        self.assertIn("Option A", displays)
        self.assertIn("tion A", inserted)

    def test_interactive_select_returns_free_form_input_when_not_matching_candidate(self):
        original_prompt_session = self.cli.PromptSession

        class FakePromptSession:
            def __init__(self, *args, **kwargs):
                self.kwargs = kwargs

            def prompt(self, *args, **kwargs):
                return "custom answer"

        self.cli.PromptSession = FakePromptSession
        try:
            answer = self.cli.interactive_select("Choose one", ["Option A", "Option B"])
        finally:
            self.cli.PromptSession = original_prompt_session

        self.assertEqual(answer, "custom answer")

    def test_interactive_select_uses_selected_candidate_text(self):
        original_prompt_session = self.cli.PromptSession

        class FakePromptSession:
            last_kwargs = None
            pre_run_called = False

            def __init__(self, *args, **kwargs):
                FakePromptSession.last_kwargs = kwargs
                self.default_buffer = types.SimpleNamespace(
                    start_completion=lambda select_first=False: setattr(FakePromptSession, "pre_run_called", select_first)
                )

            def prompt(self, *args, **kwargs):
                pre_run = kwargs.get("pre_run")
                if pre_run:
                    pre_run()
                return "Option B"

        self.cli.PromptSession = FakePromptSession
        try:
            answer = self.cli.interactive_select("Choose one", ["Option A", "Option B"])
        finally:
            self.cli.PromptSession = original_prompt_session

        self.assertEqual(answer, "Option B")
        self.assertIsNotNone(FakePromptSession.last_kwargs.get("completer"))
        self.assertIsNotNone(FakePromptSession.last_kwargs.get("key_bindings"))
        self.assertEqual(FakePromptSession.last_kwargs.get("complete_style"), "COLUMN")
        self.assertTrue(FakePromptSession.pre_run_called)

    def test_auto_now_command_enqueues_reflect_task(self):
        agent = DummyAgent()
        self.cli.handle_command(agent, "/auto-now")
        self.assertEqual(agent.tasks[-1]["source"], "reflect")
        self.assertIn("[AUTO]", agent.tasks[-1]["query"])

    def test_idle_trigger_decision_checks_enabled_threshold_and_cooldown(self):
        now = 2000
        self.assertTrue(self.cli.should_trigger_autonomous_task(True, 100, None, now, idle_seconds=1800, min_interval=120))
        self.assertFalse(self.cli.should_trigger_autonomous_task(False, 100, None, now, idle_seconds=1800, min_interval=120))
        self.assertFalse(self.cli.should_trigger_autonomous_task(True, 0, None, now, idle_seconds=1800, min_interval=120))
        self.assertFalse(self.cli.should_trigger_autonomous_task(True, 500, None, now, idle_seconds=1800, min_interval=120))
        self.assertFalse(self.cli.should_trigger_autonomous_task(True, 100, 1950, now, idle_seconds=1800, min_interval=120))


if __name__ == "__main__":
    unittest.main()
