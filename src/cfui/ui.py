"""cf-style terminal UI: semantic palette, status lines, boxed errors, JSON output, prompts."""

import getpass
import json
import os
import re
import shutil
import sys
import textwrap

PALETTE = {
    "brand": "#BF6600",
    "success": "#3A8E52",
    "error": "#D45350",
    "warning": "#BF6600",
    "info": "#3D82BB",
    "muted": "#7F7F7F",
    "boolean": "#926CC1",
}
_BASIC = {"brand": 33, "success": 32, "error": 31, "warning": 33, "info": 34, "muted": 90, "boolean": 35}
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
quiet = False  # set by the -q flag or <TOOL>_QUIET


class Fail(Exception):
    """Raise to print a boxed error and exit non-zero."""

    def __init__(self, message, hint=None, code=1):
        super().__init__(message)
        self.hint, self.code = hint, code


class Cancel(Exception):
    """Ctrl-C / EOF in a prompt: exit 130."""


def color_on(stream=None):
    return (
        bool((stream or sys.stdout).isatty()) and "NO_COLOR" not in os.environ and os.environ.get("FORCE_COLOR") != "0"
    )


def paint(role, text, stream=None):
    if not color_on(stream):
        return str(text)
    h = PALETTE[role]
    r, g, b = (int(h[i : i + 2], 16) for i in (1, 3, 5))
    if os.environ.get("COLORTERM") in ("truecolor", "24bit"):
        code = f"38;2;{r};{g};{b}"
    elif "256" in os.environ.get("TERM", ""):
        code = f"38;5;{16 + 36 * round(r / 51) + 6 * round(g / 51) + round(b / 51)}"
    else:
        code = str(_BASIC[role])
    return f"\x1b[{code}m{text}\x1b[39m"


def bold(text, stream=None):
    return f"\x1b[1m{text}\x1b[22m" if color_on(stream) else str(text)


def strip(text):
    return _ANSI.sub("", text)


def _unicode():
    return "utf" in (getattr(sys.stderr, "encoding", None) or "").lower()


def sym(name):
    uni = {"ok": "✔", "err": "✖", "warn": "⚠", "info": "ℹ", "arrow": "→"}
    ascii_ = {"ok": "√", "err": "×", "warn": "‼", "info": "i", "arrow": ">"}
    return (uni if _unicode() else ascii_)[name]


def _err(role, symbol, msg):
    print(f"{paint(role, sym(symbol), sys.stderr)} {msg}", file=sys.stderr)


def success(msg):
    """Success marker: stderr, TTY only (it carries no payload)."""
    if not quiet and sys.stderr.isatty():
        _err("success", "ok", msg)


def warning(msg):
    if not quiet:
        _err("warning", "warn", msg)


def info(msg):
    if not quiet:
        _err("info", "info", msg)


def error(msg):
    """One-line error marker (stderr). Use Fail / error_box for fatal errors."""
    _err("error", "err", msg)


def heading(msg):
    """Section heading (stderr): brand + bold."""
    if not quiet:
        print(paint("brand", bold(msg, sys.stderr), sys.stderr), file=sys.stderr)


def hint(msg):
    if not quiet:
        print(paint("muted", f"{sym('arrow')} {msg}", sys.stderr), file=sys.stderr)


def banner(name, version=None, note=None):
    """Two-line banner on stderr; skipped for pipes and --quiet."""
    if quiet or not sys.stderr.isatty():
        return
    e = sys.stderr
    line = f"{paint('brand', bold(name, e), e)}"
    if version:
        line += f" {paint('muted', '·', e)} {paint('muted', 'v' + version, e)}"
    if note:
        line += f" {paint('muted', '·', e)} {paint('warning', note, e)}"
    print(f"{line}\n{paint('brand', '─' * len(strip(line)), e)}", file=e)


def error_box(message, hint_=None, title="Error", raw=False):
    e = sys.stderr
    width = max(shutil.get_terminal_size((80, 24)).columns - 2, 20)
    lines = str(message).splitlines() or [""]
    if not raw:
        lines = [w for ln in lines for w in (textwrap.wrap(ln, width) or [""])]
    out = ["", f"{paint('error', '┌', e)} {paint('error', bold(title, e), e)}"]
    out += [f"{paint('error', '│', e)} {paint('error', ln if raw else bold(ln, e), e)}" for ln in lines]
    if hint_:
        out.append(paint("error", "│", e))
        out += [f"{paint('error', '│', e)} {paint('muted', ln, e)}" for ln in str(hint_).splitlines()]
    out.append(paint("error", "└", e))
    print("\n".join(out), file=e)


def out(text=""):
    print(text)


def _json_color(o, ind=0):
    pad = "  " * ind
    if isinstance(o, dict):
        if not o:
            return "{}"
        items = [f"{pad}  {paint('info', json.dumps(str(k)))}: {_json_color(v, ind + 1)}" for k, v in o.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(o, list):
        if not o:
            return "[]"
        return "[\n" + ",\n".join(f"{pad}  {_json_color(v, ind + 1)}" for v in o) + f"\n{pad}]"
    if isinstance(o, bool):
        return paint("boolean", json.dumps(o))
    if o is None:
        return paint("muted", "null")
    if isinstance(o, (int, float)):
        return paint("warning", json.dumps(o))
    return paint("success", json.dumps(o, ensure_ascii=False))


def data(obj):
    """Structured result: pretty JSON on stdout, colored only on a TTY and under 50k chars."""
    plain = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    if color_on() and len(plain) <= 50_000:
        try:
            plain = _json_color(json.loads(plain))
        except ValueError:
            pass
    print(plain)


def table(rows, headers=None):
    """Aligned plain-text table on stdout."""
    rows = [[str(c) for c in r] for r in rows]
    allr = ([list(map(str, headers))] if headers else []) + rows
    if not allr:
        return
    w = [max(len(strip(r[i])) if i < len(r) else 0 for r in allr) for i in range(max(map(len, allr)))]

    def fmt(r, paint_=lambda s: s):
        return "  ".join(paint_(c) + " " * (w[i] - len(strip(c))) for i, c in enumerate(r)).rstrip()

    if headers:
        print(fmt(allr[0], lambda s: paint("muted", s)))
    for r in rows:
        print(fmt(r))


# --- prompts (stdlib only; they write to stderr so stdout stays clean) ---------------------------------------------


def interactive():
    return sys.stdin.isatty() and sys.stderr.isatty() and not os.environ.get("CI")


def _label(s):
    return re.sub(r"[\x00-\x1f\x7f]", "", str(s))


def _read(prompt, secret=False):
    try:
        if secret:
            return getpass.getpass(prompt, stream=sys.stderr)
        sys.stderr.write(prompt)
        sys.stderr.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        return line.rstrip("\r\n")
    except (KeyboardInterrupt, EOFError):
        print(file=sys.stderr)
        raise Cancel from None


def ask(label, default=None, secret=False, choices=None):
    """Prompt for a value. `choices` makes it a numbered select. Raises Cancel on Ctrl-C."""
    e = sys.stderr
    q = paint("info", "?", e)
    if choices:
        print(f"{q} {_label(label)}", file=e)
        for i, ch in enumerate(choices, 1):
            print(f"  {paint('muted', f'{i})', e)} {_label(ch)}", file=e)
        while True:
            raw = _read(f"{paint('muted', '>', e)} ").strip() or (str(default) if default is not None else "")
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                return choices[int(raw) - 1]
            if raw in choices:
                return raw
            warning(f"choose 1-{len(choices)}")
    suffix = f" {paint('muted', f'({default})', e)}" if default not in (None, "") else ""
    while True:
        raw = _read(f"{q} {_label(label)}{suffix}: ", secret)
        if raw.strip() or default is not None:
            return raw.strip() or default
        warning("a value is required")


def confirm(label, default=True):
    e = sys.stderr
    while True:
        raw = (
            _read(f"{paint('info', '?', e)} {_label(label)} {paint('muted', '(Y/n)' if default else '(y/N)', e)} ")
            .strip()
            .lower()
        )
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False


def need(value, flag, label=None, positional=False, **kw):
    """Return `value` if set. Otherwise warn and prompt (TTY), or fail with the standard non-interactive error."""
    if value not in (None, ""):
        return value
    if not interactive():
        how = f"Pass <{flag}> as an argument" if positional else f"Pass {flag} <value>"
        raise Fail(f"{'<' + flag + '>' if positional else flag} is required. {how} or run interactively.", code=2)
    warning(f"{'<' + flag + '>' if positional else flag} is required")
    return ask(label or flag.lstrip("-").replace("-", " ").capitalize(), **kw)


class progress:
    """`with ui.progress("Importing", total) as p: p.advance()`: a one-line counter on color-capable TTYs only."""

    def __init__(self, label, total, enabled=True):
        self.label, self.total, self.n = label, total, 0
        self.on = enabled and not quiet and color_on(sys.stderr)

    def __enter__(self):
        return self

    def advance(self, n=1):
        self.n += n
        if self.on:
            sys.stderr.write(f"\r{paint('muted', f'{self.label} {self.n}/{self.total}', sys.stderr)}")
            sys.stderr.flush()

    def __exit__(self, *exc):
        if self.on:
            sys.stderr.write("\r\x1b[2K")
