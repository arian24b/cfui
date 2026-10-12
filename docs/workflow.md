# Workflow

[فارسی](workflow.fa.md)

Distilled from the conventions already used across my repos (tgnews, linkcovery, ollamatools, ...).

## Tooling
- **uv** for everything: `uv sync`, `uv run pytest`, `uv add <pkg>`. Commit `uv.lock`.
- **ruff** for lint + format (config in `pyproject.toml`, line length 120).
- **hatchling** build backend, `src/` layout.

## Branching & commits
1. Branch from `develop`; PR into `develop`, then `develop` -> `main`.
2. Use Conventional Commits (`git config commit.template .gitmessage`).
   `feat` = minor, `fix`/`perf` = patch, `BREAKING CHANGE` = major.

## Pipeline (`.github/workflows`)
`CI` (ruff + pytest) -> `Release` (python-semantic-release: bumps version, writes CHANGELOG, tags)
-> `Build` (docker image to ghcr.io, tagged version + latest).
Dependabot bumps actions and uv deps weekly.

## Starting a project
1. "Use this template" on GitHub.
2. Rename `project-name` / `project_name` (pyproject, Dockerfile, tests, `src/`).
3. Fill LICENSE, README; `uv sync`; `git config commit.template .gitmessage`.
4. Create the PyPI project + Trusted Publisher (workflow `release.yml`, environment `pypi`) before the first release.

## Adding Telegram/web apps
Secrets in `.env` (never committed; keep `.env.example` current). Timezone via `TZ` env in Dockerfile when scheduling.
