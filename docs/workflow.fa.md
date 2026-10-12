# روند کار

[English](workflow.md)

خلاصهٔ قراردادهایی که در مخزن‌های دیگرم (tgnews، linkcovery، ollamatools و ...) هم استفاده می‌کنم.

## ابزارها
- **uv** برای همه‌چیز: `uv sync`، `uv run pytest`، `uv add <pkg>`. فایل `uv.lock` کامیت می‌شود.
- **ruff** برای lint و format (تنظیمات در `pyproject.toml`، طول خط ۱۲۰).
- **hatchling** به عنوان build backend و ساختار `src/`.

## شاخه‌ها و کامیت‌ها
1. از `develop` شاخه بگیرید؛ PR به `develop` و سپس `develop` به `main`.
2. از Conventional Commits استفاده کنید (`git config commit.template .gitmessage`).
   `feat` نسخهٔ minor، `fix` و `perf` نسخهٔ patch و `BREAKING CHANGE` نسخهٔ major را بالا می‌برد.

## Pipeline (`.github/workflows`)
`CI` (ruff و pytest) ← `Release` (python-semantic-release: نسخه را بالا می‌برد، CHANGELOG را می‌نویسد و تگ می‌زند)
← `Build` (ایمیج docker روی ghcr.io با تگ نسخه و latest).
Dependabot هر هفته نسخهٔ actions و وابستگی‌های uv را به‌روز می‌کند.

## شروع یک پروژهٔ جدید
1. در GitHub روی «Use this template» بزنید.
2. `project-name` و `project_name` را تغییر دهید (pyproject، Dockerfile، تست‌ها، `src/`).
3. LICENSE و README را پر کنید، `uv sync` را اجرا کنید و `git config commit.template .gitmessage` را بزنید.
4. پیش از اولین انتشار، پروژه را در PyPI بسازید و Trusted Publisher را تنظیم کنید (workflow با نام `release.yml`، environment با نام `pypi`).

## افزودن برنامهٔ تلگرام یا وب
رمزها در `.env` می‌مانند (کامیت نمی‌شود؛ `.env.example` را به‌روز نگه دارید). برای زمان‌بندی، منطقهٔ زمانی را با متغیر `TZ` در Dockerfile تنظیم کنید.
