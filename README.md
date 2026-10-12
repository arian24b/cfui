# cfui

[فارسی](README.fa.md)

A small, dependency-free toolkit for Python command-line tools. It gives every tool the same look (modelled on Cloudflare's `cf` CLI), the same common commands, and the same behavior when an option is missing.

- PyPI package: `cfuicli`. Import name: `cfui`.
- Python 3.12 to 3.15, standard library only.

## Features

- cf-style help, version, update and error output for every command.
- Missing required options are prompted on a terminal and rejected with exit code 2 in pipes and CI.
- Colors follow `NO_COLOR` and `FORCE_COLOR`, and fall back to 256 or 16 colors when needed.
- No runtime dependencies. Built on `argparse`.
- A bundled agent skill (`cf-cli-ui`) for building CLIs in this style.

## Install

Requires Python 3.12, 3.13, 3.14 or 3.15.


```bash
uv add cfuicli          # in a project
pip install cfuicli     # anywhere else
```

## A complete tool in a few lines

```python
from cfui import App, Arg, ui

app = App("tool", repo="https://github.com/me/tool", pypi="tool", description="Does things.")


@app.command("greet", "Say hi", args=[Arg("--name", required=True, prompt="Your name")])
def greet(a):
    ui.success(f"hi {a.name}")


def main():
    app.main()
```

```console
$ tool greet --name Sara          # runs
$ tool greet                      # on a terminal: asks "Your name"
$ tool greet </dev/null           # in a pipe or CI: --name is required. Pass --name <value> or run interactively.
$ tool help greet
$ tool version
```

## How it works

`App` is a thin layer over `argparse`. Each command gets its own parser, and `Arg` wraps `add_argument` with a few extra keywords. After parsing, any `required=True` option that has no value is asked for through `ui.ask` when stdin and stderr are terminals and `CI` is unset; otherwise it is reported as an error. Help and error text are drawn by `cfui.ui` and written to stderr, so stdout stays free for results. `update` reads the latest version from `https://pypi.org/pypi/<package>/json` and upgrades with `uv tool upgrade`, `pipx upgrade` or `pip install -U`, depending on where the interpreter lives.

## What every tool gets

| Command or flag | What it does |
|---|---|
| `help [command]`, `-h` | cf-style help: usage, description, options by section, global flags, docs link |
| `version`, `-v` | tool name and version, git repository, Python version |
| `update [--check]` | self update through uv, pipx or pip (override with `App(upgrade=...)`) |
| `-q`, `--quiet` | no banner, notes or success markers (also `<TOOL>_QUIET=1`) |

Behavior you do not have to write:

- A required option or argument is asked for on a terminal and reported as an error when the input is piped or the `CI` variable is set. The error exits with code 2.
- Errors are drawn as a red box on stderr and exit non-zero. `raise Fail(message, hint)` or `sys.exit("message")` both work. Ctrl-C exits 130.
- Color follows the rules: only on a TTY, `NO_COLOR` turns it off, `FORCE_COLOR=0` turns it off, and the palette drops to 256 or 16 colors when the terminal needs it.
- Structured results go to stdout as JSON (`ui.data`), decoration goes to stderr.

## Building commands

```python
app = App("tool", repo=..., pypi=..., description=..., default="count", global_args=[Arg("-c", "--config")])

grp = app.group("config", "Manage settings")  # tool config show


@grp.command("show", "Show settings")
def show(a): ...


@app.command("wp", "Pass everything through", raw=True)  # a.args is the untouched argv tail
def wp(a): ...
```

`Arg` takes the usual `argparse.add_argument` keywords plus `required=True` (prompt when missing), `prompt="Question"`, `secret=True` (hidden input) and `group="Section"` (help section). Positional arguments work the same way.

## Output helpers (`cfui.ui`)

`success`, `info`, `warning`, `error`, `hint`, `heading`, `banner`, `error_box`, `data` (JSON), `table`, `out`, and the prompts `ask`, `confirm`, `need`, plus `progress` for a one-line counter.

## Shared pieces (`cfui.common`)

| Name | Use |
|---|---|
| `YES`, `JSON`, `FORCE`, `DRY_RUN`, `JOBS`, `TIMEOUT`, `BACKGROUND` | the same flags with the same help text in every tool |
| `confirm(message, yes)` | ask, or require `--yes` when not on a terminal |
| `parse_value(text)` | turn `true`, `5`, `a,b`, `none` into Python values |
| `run_parallel(items, worker, jobs)` | thread pool with one status line per item |
| `add_config(app, items=, get=, set=, reset=, path=, validate=)` | registers `config show/get/set/reset/path/validate` |

## The agent skill

The package carries the `cf-cli-ui` skill, which tells coding agents how to build and restyle CLIs this way.

```bash
cfui skill                 # print where it is
cfui skill --install       # copy it to ~/.agents/skills/cf-cli-ui
```

## Tools built on cfui

[aitc](https://github.com/arian24b/aitc), [thronetools](https://github.com/arian24b/thronetools), [ollama-tool-cli](https://github.com/arian24b/ollamatools), [pem](https://github.com/arian24b/pem), [linkcovery](https://github.com/arian24b/linkcovery), [pulsecheck](https://github.com/arian24b/pulsecheck), [wpguard](https://github.com/arian24b/wpguard). [dokploytools](https://github.com/arian24b/dokploytools) is written in Go and follows the same conventions with its own code.

## Troubleshooting

- `--name is required. Pass --name <value> or run interactively.` in a script: the prompt only appears on a terminal. Pass the option explicitly.
- `tool version` prints `tool unknown`: the package named by `pypi=` is not installed, so its version cannot be read. Pass `version=` to `App` or install the package.
- No colors: output is not a TTY, `NO_COLOR` is set, or `FORCE_COLOR=0`.
- `update --check` prints `latest: unknown (offline or not published)`: PyPI did not answer within 5 seconds, or the package is not published.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

The conventions behind this repo are in [docs/workflow.md](docs/workflow.md) ([فارسی](docs/workflow.fa.md)).

Commits follow Conventional Commits. A `feat:` or `fix:` merged into `main` runs the Release workflow, which bumps the version, tags it, and publishes to PyPI through a trusted publisher.

## License

MIT
