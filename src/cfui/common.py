"""Options and helpers the tools all repeat: shared Args, value parsing, parallel runs, a ready-made `config` group."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from . import ui
from .app import Arg

# Shared options: put them in a command's `args=[...]` so every tool spells them the same way.
YES = Arg("-y", "--yes", action="store_true", help="Skip confirmation")
JSON = Arg("--json", action="store_true", help="Output machine-readable JSON")
FORCE = Arg("-f", "--force", action="store_true", help="Overwrite / proceed even if it exists")
DRY_RUN = Arg("--dry-run", action="store_true", help="Show what would change, change nothing")
JOBS = Arg("-j", "--jobs", type=int, help="Number of parallel jobs")
TIMEOUT = Arg("--timeout", type=int, default=10, help="Timeout in seconds")
BACKGROUND = Arg("-b", "--background", action="store_true", help="Run the command in the background")


def confirm(message, yes=False, default=False):
    """True when `yes` was passed or the user agrees. Non-interactive without --yes is a usage error."""
    if yes:
        return True
    if not ui.interactive():
        raise ui.Fail(message, "Not a terminal: pass --yes to confirm.", code=2)
    return ui.confirm(message, default=default)


def parse_value(text):
    """CLI string -> bool / None / int / float / list / str (for `config set`)."""
    low = text.lower()
    if low in ("true", "yes", "1", "on", "enable", "enabled"):
        return True
    if low in ("false", "no", "0", "off", "disable", "disabled"):
        return False
    if low in ("none", "null", "auto"):
        return None
    if text.lstrip("-").isdigit():
        return int(text)
    if "." in text and text.replace(".", "", 1).lstrip("-").isdigit():
        return float(text)
    if "," in text:
        return [x.strip() for x in text.split(",")]
    return text


def run_parallel(items, worker, jobs=1, label=str):
    """worker(item) on a thread pool; one status line per item; returns the failed items.
    An item fails when worker raises or returns an object with a non-zero `return_code`."""
    failures = []
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futures = {ex.submit(worker, i): i for i in items}
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                ok = getattr(fut.result(), "return_code", 0) == 0
            except Exception:
                ok = False
            (ui.success if ok else ui.error)(label(item))
            if not ok:
                failures.append(item)
    return failures


def _show(value):
    if value is None:
        return "None (auto)"
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return str(value)


def add_config(app, *, items, get, set, reset, path, validate=None, name="config", help="Manage configuration"):
    """Register `<tool> config show|get|set|reset|path|validate` from five callables:

    items() -> dict, get(key) -> value, set(key, value), reset(), path() -> Path, validate() -> bool (optional).
    `config set` with no value asks for it on a TTY; `config reset` needs --yes off a TTY.
    """
    grp = app.group(name, help)

    @grp.command("show", "Show every setting", args=[JSON])
    def _show_all(a):
        if a.json:
            ui.data(items())
        else:
            ui.table([(k, _show(v)) for k, v in items().items()], ["Setting", "Value"])
            ui.hint(f"Config file: {path()}")

    @grp.command("get", "Get one setting", args=[Arg("key", required=True, prompt="Setting name", help="Setting name")])
    def _get(a):
        ui.out(_show(get(a.key)))

    @grp.command(
        "set",
        "Set one setting",
        args=[
            Arg("key", required=True, prompt="Setting name", help="Setting name"),
            Arg("value", required=True, prompt="New value", help="New value (true/false/number/a,b,c/none)"),
        ],
    )
    def _set(a):
        value = parse_value(a.value)
        set(a.key, value)
        ui.success(f"Set {a.key} = {_show(value)}")

    @grp.command("reset", "Reset every setting to its default", args=[YES])
    def _reset(a):
        if not confirm("Reset all configuration to defaults?", a.yes):
            raise ui.Fail("Reset cancelled.")
        reset()
        ui.success("Configuration reset to defaults")

    @grp.command("path", "Print the config file path")
    def _path(a):
        ui.out(path())

    if validate:

        @grp.command("validate", "Check the configuration")
        def _validate(a):
            if not validate():
                raise ui.Fail("Configuration validation failed.")
            ui.success("Configuration is valid")

    return grp
