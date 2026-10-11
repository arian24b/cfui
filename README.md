# cfui

Stdlib-only terminal UI and tiny argparse framework in the style of Cloudflare's `cf` CLI.

```python
from cfui import App, Arg, ui

app = App("tool", repo="https://github.com/me/tool", pypi="tool", description="Does things.")


@app.command("greet", "Say hi", args=[Arg("--name", required=True, prompt="Your name")])
def greet(a):
    ui.success(f"hi {a.name}")


def main():
    app.main()
```

Gives you `help`, `version` (and `-v`), `update [--check]`, `-q/--quiet`, boxed errors, JSON output,
and prompts for missing required options on a TTY (a clear error when piped or in CI).

## Shared pieces (`cfui.common`)

`YES`, `JSON`, `FORCE`, `DRY_RUN`, `JOBS`, `TIMEOUT`, `BACKGROUND` (ready-made `Arg`s), `confirm(msg, yes)`,
`parse_value`, `run_parallel(items, worker, jobs)`, and `add_config(app, items=, get=, set=, reset=, path=, validate=)`
which registers `config show|get|set|reset|path|validate`.

## Releasing

Conventional Commits on `main` -> CI -> `Release` workflow (python-semantic-release) bumps the version, tags and
publishes to PyPI with a Trusted Publisher (environment `pypi`, workflow `release.yml`). See `docs/workflow.md`.
