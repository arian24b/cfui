import json

import pytest

from cfui import App, Arg, ui


@pytest.fixture
def app():
    a = App("demo", repo="https://example.com/demo", version="1.2.3")
    a.seen = []

    @a.command("greet", "Say hi", args=[Arg("--name", required=True, help="who"), Arg("--loud", action="store_true")])
    def greet(ns):
        a.seen.append((ns.name, ns.loud))

    g = a.group("cfg", "Config")

    @g.command("show", "Show config")
    def show(ns):
        a.seen.append("show")

    @a.command("boom", "Fails")
    def boom(ns):
        raise SystemExit("legacy message")

    return a


def test_dispatch_group_and_flags(app):
    assert app.run(["greet", "--name", "x", "--loud", "-q"]) == 0
    assert app.run(["cfg", "show"]) == 0
    assert app.seen == [("x", True), "show"]


def test_missing_required_non_interactive(app, capsys):
    assert app.run(["greet"]) == 2
    err = capsys.readouterr().err
    assert "--name is required. Pass --name <value> or run interactively." in err and "┌ Error" in err


def test_missing_required_prompts(app, monkeypatch):
    monkeypatch.setattr(ui, "interactive", lambda: True)
    monkeypatch.setattr(ui, "_read", lambda prompt, secret=False: "bob")
    assert app.run(["greet"]) == 0
    assert app.seen == [("bob", False)]


def test_cancel_is_130(app, monkeypatch):
    monkeypatch.setattr(ui, "interactive", lambda: True)

    def cancel(*a, **k):
        raise ui.Cancel

    monkeypatch.setattr(ui, "_read", cancel)
    assert app.run(["greet"]) == 130


def test_version_help_unknown(app, capsys):
    assert app.run(["-v"]) == 0
    assert app.run(["version"]) == 0
    out = capsys.readouterr().out
    assert out.count("demo 1.2.3") == 2 and "https://example.com/demo" in out
    assert app.run(["--help"]) == 0
    assert "demo greet" in capsys.readouterr().out
    assert app.run(["help", "greet"]) == 0
    assert "--name <NAME>" in capsys.readouterr().out
    assert app.run(["nope"]) == 2
    assert app.run(["boom"]) == 1
    assert "legacy message" in capsys.readouterr().err


def test_json_and_no_color(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    ui.data({"a": [1, True, None]})
    assert json.loads(capsys.readouterr().out) == {"a": [1, True, None]}
    ui.error_box("bad", "fix it")
    assert capsys.readouterr().err.splitlines()[1:] == ["┌ Error", "│ bad", "│", "│ fix it", "└"]


def test_default_command(capsys):
    a = App("d", repo="r", version="1", default="go")
    a.command("go", args=[Arg("--x")])(lambda ns: print("went", ns.x))
    assert a.run(["--x", "1"]) == 0
    assert "went 1" in capsys.readouterr().out


def test_required_list_positional(monkeypatch):
    got = []
    a = App("d", repo="r", version="1")
    a.command("rm", args=[Arg("ids", type=int, nargs="+", required=True, prompt="IDs")])(lambda ns: got.append(ns.ids))
    assert a.run(["rm", "1", "2"]) == 0
    monkeypatch.setattr(ui, "interactive", lambda: True)
    monkeypatch.setattr(ui, "_read", lambda prompt, secret=False: "3, 4")
    assert a.run(["rm"]) == 0
    assert got == [[1, 2], [3, 4]]


def test_raw_and_grouped_help(capsys):
    a = App("d", repo="r", version="1")
    seen = []
    a.command("wp", "passthrough", raw=True)(lambda ns: seen.append(ns.args))
    a.command("go", args=[Arg("--x", group="Special"), Arg("--y")], help_args=[Arg("--x", group="Special")])(
        lambda ns: None
    )
    assert a.run(["wp", "-q", "--help", "x"]) == 0
    assert seen == [["-q", "--help", "x"]]
    assert a.run(["go", "-h"]) == 0
    out = capsys.readouterr().out
    assert "Special" in out and "--y" not in out


def test_common_config_group_and_helpers(capsys):
    from cfui import add_config, parse_value, run_parallel

    store = {"debug": False, "n": 1}
    a = App("d", repo="r", version="1")
    add_config(
        a, items=lambda: store, get=store.__getitem__, set=store.__setitem__, reset=store.clear, path=lambda: "/x.json"
    )
    assert a.run(["config", "set", "n", "5"]) == 0 and store["n"] == 5
    assert a.run(["config", "get", "debug"]) == 0
    assert a.run(["config", "reset"]) == 2  # off a TTY needs --yes
    assert a.run(["config", "reset", "-y"]) == 0 and store == {}
    assert parse_value("a, b") == ["a", "b"] and parse_value("-3") == -3 and parse_value("auto") is None
    assert run_parallel([1, 2, 3], lambda i: 1 / (i - 2), 2) == [2]


def test_bundled_skill_installs(tmp_path):
    from cfui.__main__ import app as cfui_app

    assert cfui_app.run(["skill", "--install", str(tmp_path)]) == 0
    assert "cfuicli" in (tmp_path / "cf-cli-ui" / "SKILL.md").read_text()
