"""Tiny argparse framework: cf-style help, and ready-made help / version / update commands."""

import argparse
import asyncio
import importlib.metadata
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.request

from . import ui

_VALUE_ACTIONS = ("store", "append", "extend")
_BUILTIN = ("help", "version", "update")


class Arg:
    """An argparse argument. `required=True` means: prompt for it on a TTY, fail with a clear error otherwise."""

    def __init__(self, *flags, required=False, prompt=None, secret=False, group=None, **kw):
        self.flags, self.required, self.prompt, self.secret, self.kw = flags, required, prompt, secret, kw
        self.group = group  # help section title
        self.positional = not flags[0].startswith("-")
        if self.positional and required:  # we enforce it ourselves so we can prompt
            kw["nargs"] = "*" if kw.get("nargs") in ("+", "*") else "?"
        elif required:
            kw.pop("required", None)
        self.dest = kw.get("dest") or (flags[0] if self.positional else max(flags, key=len).lstrip("-").replace("-", "_"))

    def add_to(self, parser):
        parser.add_argument(*self.flags, **self.kw)

    @property
    def takes_value(self):
        return not self.positional and self.kw.get("action", "store") in _VALUE_ACTIONS

    def row(self):
        left = ", ".join(self.flags)
        if self.takes_value:
            left += f" <{self.kw.get('metavar') or self.dest.upper()}>"
        elif self.positional:
            left = f"<{self.flags[0]}>" if self.required else f"[{self.flags[0]}]"
        right = self.kw.get("help", "")
        if self.required:
            right += " [required]"
        if self.kw.get("choices"):
            right += f" [choices: {', '.join(map(str, self.kw['choices']))}]"
        d = self.kw.get("default")
        if d not in (None, False, "") and self.takes_value:
            right += f" [default: {d}]"
        return left, right.strip()


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ui.Fail(message, f"Run `{self.prog} --help` for usage.", code=2)


class Command:
    def __init__(self, name, help_="", fn=None, args=(), aliases=(), hidden=False, banner=False, raw=False, help_args=None):
        self.name, self.help, self.fn, self.args = name, help_, fn, list(args)
        self.raw, self.help_args = raw, help_args  # raw: gets the untouched argv tail as `.args`; help_args: subset shown in --help
        self.aliases, self.hidden, self.banner = aliases, hidden, banner
        self.commands = {}  # non-empty for a group

    def command(self, name, help="", args=(), aliases=(), hidden=False, banner=False, raw=False, help_args=None):
        def deco(fn):
            self.commands[name] = Command(name, help, fn, args, aliases, hidden, banner, raw, help_args)
            return fn

        return deco

    def group(self, name, help="", aliases=()):
        g = self.commands[name] = Command(name, help, aliases=aliases)
        return g

    def find(self, name):
        for c in self.commands.values():
            if name == c.name or name in c.aliases:
                return c


class App(Command):
    def __init__(self, name, repo, description="", pypi=None, version=None, docs=None, global_args=(), default=None, upgrade=None):
        super().__init__(name, description)
        self.repo, self.pypi, self.docs = repo, pypi or name, docs or repo
        self.version = version or _installed(self.pypi)
        self.global_args, self.default = list(global_args), default  # default: command used when none is named
        self.upgrade = upgrade  # optional () -> argv overriding how `update` upgrades (git checkouts, binaries...)
        self.env_quiet = re.sub(r"\W", "_", name).upper() + "_QUIET"
        self._builtins()

    # --- built-in commands -------------------------------------------------------------------------------------
    def _builtins(self):
        @self.command("help", "Show help for a command", args=[Arg("topic", nargs="*", help="Command path")])
        def _help(a):
            self.print_help(a.topic)

        @self.command("version", "Show version and repository")
        def _version(a):
            ui.out(self.version_text())

        @self.command("update", "Update to the latest version", banner=True,
                      args=[Arg("--check", action="store_true", help="Only compare versions")])
        def _update(a):
            return self.update(a.check)

    def version_text(self):
        return f"{self.name} {self.version}\nrepo   {self.repo}\npython {sys.version.split()[0]}"

    def update(self, check_only=False):
        latest = latest_version(self.pypi)
        ui.out(f"installed: {self.version}\nlatest:    {latest or 'unknown (offline or not published)'}")
        if check_only:
            return 0
        if latest and latest == self.version:
            ui.success("already up to date")
            return 0
        cmd = self.upgrade() if self.upgrade else upgrade_command(self.pypi)
        ui.hint("running: " + " ".join(cmd))
        return subprocess.call(cmd)

    # --- help --------------------------------------------------------------------------------------------------
    def print_help(self, path=()):
        node, names = self, [self.name]
        for p in path:
            nxt = node.find(p)
            if not nxt:
                raise ui.Fail(f"Unknown command: {' '.join([*names[1:], p])}", f"Run `{self.name} help` to list commands.", 2)
            node = nxt
            names.append(nxt.name)
        ui.banner(self.name, self.version)
        H = lambda s: ui.paint("brand", ui.bold(s))
        C = lambda s: ui.paint("info", s)
        use = " ".join(names)
        leaf = not node.commands
        line = f"{use} <command> [options]" if not leaf else f"{use}{_usage(node.args)} [options]"
        lines = [line, ""]
        if node.help:
            lines += [node.help, ""]
        if node.commands:
            lines.append(H("Commands"))
            cmds = sorted((c for c in node.commands.values() if not c.hidden), key=lambda c: c.name in _BUILTIN and node is self)
            rows = [(f"{use} {c.name}", c.help) for c in cmds]
            lines += _cols(rows, C)
            lines.append("")
        shown = (node.args if node.help_args is None else node.help_args) if leaf else self.global_args
        if shown and (leaf or node is self):
            sections: dict[str, list] = {}
            for a in shown:
                sections.setdefault(a.group or "Options", []).append(a.row())
            for title, rows in sections.items():
                lines += [H(title), *_cols(rows, C), ""]
        lines.append(H("Global flags"))
        lines += _cols([("-q, --quiet", "Suppress non-essential output [boolean] [default: false]"),
                        ("-h, --help", "Show help [boolean]")]
                       + ([("-v, --version", "Show version [boolean]")] if node is self else []), C)
        lines += ["", ui.paint("muted", f"For more information, visit {self.docs}")]
        ui.out("\n".join(lines))

    # --- run ---------------------------------------------------------------------------------------------------
    def run(self, argv=None):
        argv = list(sys.argv[1:] if argv is None else argv)
        try:
            return self._run(argv) or 0
        except ui.Fail as e:
            ui.error_box(e, e.hint)
            return e.code
        except (ui.Cancel, KeyboardInterrupt):
            return 130
        except BrokenPipeError:
            return 0
        except SystemExit as e:
            if isinstance(e.code, str):  # legacy `sys.exit("message")` becomes a boxed error
                ui.error_box(e.code)
                return 1
            return e.code or 0

    def _run(self, argv):
        if argv[:1] in (["-v"], ["--version"]):
            ui.out(self.version_text())
            return 0
        raw = self.find(argv[0]) if argv else None
        if raw is not None and raw.raw:  # passthrough commands see the rest of argv untouched
            ui.quiet = bool(os.environ.get(self.env_quiet))
            r = raw.fn(argparse.Namespace(args=argv[1:]))
            return asyncio.run(r) if inspect.iscoroutine(r) else r
        g = _Parser(add_help=False, allow_abbrev=False, prog=self.name)
        g.add_argument("-q", "--quiet", action="store_true")
        g.add_argument("-h", "--help", action="store_true")
        for a in self.global_args:
            a.add_to(g)
        gns, rest = g.parse_known_args(argv)
        ui.quiet = gns.quiet or bool(os.environ.get(self.env_quiet))
        node, names = self, [self.name]
        if self.default and not gns.help and (rest or not sys.stdin.isatty()) and (not rest or rest[0].startswith("-")):
            rest = [self.default, *rest]
        while rest and node.commands and not rest[0].startswith("-"):
            nxt = node.find(rest[0])
            if not nxt:
                raise ui.Fail(f"Unknown command: {rest[0]}", f"Run `{' '.join(names)} --help` to list commands.", 2)
            node, rest = nxt, rest[1:]
            names.append(node.name)
        if node.commands:  # root or group without a verb
            if rest:
                raise ui.Fail(f"Unknown option: {rest[0]}", f"Run `{' '.join(names)} --help` for usage.", 2)
            self.print_help(names[1:])
            return 0
        if gns.help:
            self.print_help(names[1:])
            return 0
        p = _Parser(add_help=False, allow_abbrev=False, prog=" ".join(names))
        for a in node.args:
            a.add_to(p)
        ns = p.parse_args(rest)
        for k, v in vars(gns).items():
            setattr(ns, k, v)
        for a in node.args:
            if a.required and getattr(ns, a.dest, None) in (None, [], ""):
                if node.banner:
                    ui.banner(self.name, self.version)
                flag = a.flags[0] if a.positional else max(a.flags, key=len)
                v = ui.need(None, flag, a.prompt or a.dest.replace("_", " ").capitalize(), positional=a.positional,
                            secret=a.secret, choices=a.kw.get("choices"), default=a.kw.get("default"))
                setattr(ns, a.dest, _convert(a, v, flag))
        if node.banner:
            ui.banner(self.name, self.version)
        r = node.fn(ns)
        return asyncio.run(r) if inspect.iscoroutine(r) else r

    def main(self, argv=None):
        sys.exit(self.run(argv))


def _convert(a, v, flag):
    t = a.kw.get("type")
    try:
        if a.kw.get("nargs") in ("+", "*"):  # prompted text becomes a list
            return [t(x) if t else x for x in v.replace(",", " ").split()]
        return t(v) if t and isinstance(v, str) else v
    except (ValueError, TypeError, argparse.ArgumentTypeError) as e:
        raise ui.Fail(f"Invalid value for {flag}: {v!r} ({e})", code=2) from None


def _usage(args):
    return "".join((f" <{a.flags[0]}>" if a.required else f" [{a.flags[0]}]") for a in args if a.positional)


def _cols(rows, style):
    width = min(max((len(left) for left, _ in rows), default=0), 36)
    cols = shutil.get_terminal_size((100, 24)).columns
    out = []
    for left, right in rows:
        wrapped = textwrap.wrap(right, max(cols - width - 4, 30)) or [""]
        out.append(f"  {style(left)}{' ' * (width - len(left) + 2)}{wrapped[0]}")
        out += [f"  {' ' * (width + 2)}{w}" for w in wrapped[1:]]
    return out


def _installed(pkg):
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def latest_version(pkg):
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=5) as r:
            return json.load(r)["info"]["version"]
    except Exception:  # noqa: BLE001
        return None


def upgrade_command(pkg):
    exe = sys.executable.replace("\\", "/")
    if "/uv/tools/" in exe and shutil.which("uv"):
        return ["uv", "tool", "upgrade", pkg]
    if "/pipx/" in exe and shutil.which("pipx"):
        return ["pipx", "upgrade", pkg]
    return [sys.executable, "-m", "pip", "install", "-U", pkg]
