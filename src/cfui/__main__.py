"""`cfui` / `python -m cfui`: helper commands for projects that use cfuicli."""

import shutil
from importlib import resources
from pathlib import Path

from . import ui
from .app import App, Arg

app = App(
    "cfui", repo="https://github.com/arian24b/cfui", pypi="cfuicli", description="Helpers for CLIs built on cfuicli."
)


@app.command(
    "skill",
    "Print the path of the bundled cf-cli-ui agent skill, or copy it with --install",
    args=[
        Arg(
            "--install",
            nargs="?",
            const="~/.agents/skills",
            metavar="DIR",
            help="copy it into DIR/cf-cli-ui (default ~/.agents/skills)",
        ),
    ],
)
def skill(a):
    src = Path(str(resources.files("cfui").joinpath("skills/cf-cli-ui")))
    if not a.install:
        ui.out(src)
        return
    dest = Path(a.install).expanduser() / "cf-cli-ui"
    shutil.copytree(src, dest, dirs_exist_ok=True)
    ui.success(f"installed skill to {dest}")


def main():
    app.main()


if __name__ == "__main__":
    main()
