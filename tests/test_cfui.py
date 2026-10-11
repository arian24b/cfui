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
