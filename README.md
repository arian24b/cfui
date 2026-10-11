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
