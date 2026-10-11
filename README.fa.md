# cfui

[English](README.md)

یک کتابخانهٔ کوچک و بدون وابستگی برای ابزارهای خط فرمان پایتون. همهٔ ابزارها با آن ظاهر یکسان (الهام‌گرفته از CLI شرکت Cloudflare به نام `cf`)، دستورهای مشترک و رفتار یکسان در برابر گزینهٔ جاافتاده پیدا می‌کنند.

- نام بسته در PyPI: `cfuicli`. نام برای import: `cfui`.
- پایتون ۳٫۱۲ تا ۳٫۱۵، فقط کتابخانهٔ استاندارد.

## نصب

```bash
uv add cfuicli          # داخل یک پروژه
pip install cfuicli     # جای دیگر
```

## یک ابزار کامل در چند خط

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
$ tool greet --name Sara          # اجرا می‌شود
$ tool greet                      # در ترمینال: "Your name" را می‌پرسد
$ tool greet </dev/null           # در pipe یا CI: --name is required. Pass --name <value> or run interactively.
$ tool help greet
$ tool version
```

## چیزهایی که هر ابزار خودکار دریافت می‌کند

| دستور یا گزینه | کار |
|---|---|
| `help [command]`، `-h` | راهنما به سبک cf: طرز استفاده، توضیح، گزینه‌ها به تفکیک بخش، گزینه‌های سراسری و پیوند مستندات |
| `version`، `-v` | نام و نسخهٔ ابزار، مخزن گیت، نسخهٔ پایتون |
| `update [--check]` | به‌روزرسانی خود ابزار با uv، pipx یا pip (با `App(upgrade=...)` قابل تغییر است) |
| `-q`، `--quiet` | بدون بنر، یادداشت و علامت موفقیت (متغیر `<TOOL>_QUIET=1` هم همین کار را می‌کند) |

رفتارهایی که لازم نیست خودتان بنویسید:

- گزینه یا آرگومان اجباریِ جاافتاده در ترمینال پرسیده می‌شود. اگر ورودی pipe باشد یا متغیر `CI` تنظیم شده باشد، خطا می‌دهد و با کد ۲ خارج می‌شود.
- خطاها به صورت کادر قرمز روی stderr چاپ می‌شوند و کد خروج غیرصفر دارند. هم `raise Fail(message, hint)` کار می‌کند و هم `sys.exit("message")`. با Ctrl-C کد خروج ۱۳۰ است.
- رنگ فقط روی TTY فعال است. `NO_COLOR` یا `FORCE_COLOR=0` آن را خاموش می‌کند و در صورت نیاز پالت به ۲۵۶ یا ۱۶ رنگ کاهش می‌یابد.
- نتیجهٔ ساخت‌یافته با `ui.data` به صورت JSON روی stdout می‌رود و هر چیز تزئینی روی stderr.

## ساختن دستورها

```python
app = App("tool", repo=..., pypi=..., description=..., default="count", global_args=[Arg("-c", "--config")])

grp = app.group("config", "Manage settings")          # tool config show
@grp.command("show", "Show settings")
def show(a): ...

@app.command("wp", "Pass everything through", raw=True)   # a.args بقیهٔ argv است، بدون تغییر
def wp(a): ...
```

`Arg` همان پارامترهای `argparse.add_argument` را می‌گیرد و چند پارامتر اضافه دارد: `required=True` (در صورت نبودن مقدار می‌پرسد)، `prompt="Question"`، `secret=True` (ورودی پنهان) و `group="Section"` (بخش راهنما). آرگومان‌های موضعی هم به همین شکل کار می‌کنند.

## توابع خروجی (`cfui.ui`)

`success`، `info`، `warning`، `error`، `hint`، `heading`، `banner`، `error_box`، `data` (JSON)، `table`، `out`، و پرسش‌ها: `ask`، `confirm`، `need`. برای شمارندهٔ تک‌خطی هم `progress` هست.

## بخش‌های مشترک (`cfui.common`)

| نام | کاربرد |
|---|---|
| `YES`، `JSON`، `FORCE`، `DRY_RUN`، `JOBS`، `TIMEOUT`، `BACKGROUND` | همین گزینه‌ها با همین نام و توضیح در همهٔ ابزارها |
| `confirm(message, yes)` | می‌پرسد، یا خارج از ترمینال `--yes` را لازم می‌داند |
| `parse_value(text)` | `true`، `5`، `a,b`، `none` را به مقدار پایتونی تبدیل می‌کند |
| `run_parallel(items, worker, jobs)` | اجرای موازی با یک خط وضعیت برای هر مورد |
| `add_config(app, items=, get=, set=, reset=, path=, validate=)` | دستورهای `config show/get/set/reset/path/validate` را ثبت می‌کند |

## مهارت (skill) عامل‌ها

این بسته مهارت `cf-cli-ui` را همراه دارد. مهارت به عامل‌های برنامه‌نویسی می‌گوید چطور CLI را به این شیوه بسازند یا بازطراحی کنند.

```bash
cfui skill                 # مسیر آن را چاپ می‌کند
cfui skill --install       # در ~/.agents/skills/cf-cli-ui کپی می‌کند
```

## ابزارهای ساخته‌شده با cfui

[aitc](https://github.com/arian24b/aitc)، [thronetools](https://github.com/arian24b/thronetools)، [ollama-tool-cli](https://github.com/arian24b/ollamatools)، [pem](https://github.com/arian24b/pem)، [linkcovery](https://github.com/arian24b/linkcovery)، [pulsecheck](https://github.com/arian24b/pulsecheck)، [wpguard](https://github.com/arian24b/wpguard). [dokploytools](https://github.com/arian24b/dokploytools) با Go نوشته شده و همین قراردادها را با کد خودش رعایت می‌کند.

## توسعه

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

پیام کامیت‌ها از Conventional Commits پیروی می‌کنند. وقتی `feat:` یا `fix:` در `main` ادغام شود، workflow مربوط به Release نسخه را بالا می‌برد، تگ می‌زند و از طریق trusted publisher در PyPI منتشر می‌کند.

## مجوز

MIT
