"""Ветки `curl_follow_hides_redirect` и `reinstall_without_pins.*` чекера
`env_presupposition` (пакет B-P2b-P1).

Опора: ADR-054, аннотация 2026-09-09, раунд 8 — NB-45 (`curl -L`: POST→GET на
301/302/303, кросс-хостовый Authorization, петли; лечение — `%{url_effective}`)
и NB-44 (лестница строгости пиннинга: диапазон → `==` → хэш).

Обе ветки — данные манифеста; кода они не трогают. Трогают код три правки входа
`_line_pattern` (склейка продолжений, снятие комментария оболочки, `ignorecase`),
и у каждой здесь стоит свой тест: правка без теста — правка, которую нельзя
показать сломанной.

Единица диспозиции — «на артефакт `--fast`» для фикстур и «на блок» для строк.
"""

from __future__ import annotations

import os

import pytest
import yaml

import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "linter", "fixtures")
NAME = "env_presupposition"

CURL = "curl_follow_hides_redirect"
PIN = "reinstall_without_pins"


@pytest.fixture(scope="module")
def checker() -> dict:
    with open(os.path.join(ROOT, "linter", "manifest.yaml"), encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}
    active, _skipped, failed = run.load_checkers(manifest, "handoff")
    assert failed == []
    return {c["name"]: c for c in active}[NAME]


def check(checker: dict, text: str) -> list[str]:
    return [f.message for f in checker["module"].check(text, checker["config"])]


def marked(messages: list[str], form: str) -> list[str]:
    return [m for m in messages if f"[{form}" in m]


def block(*lines: str, lang: str = "bash") -> str:
    return "```%s\n%s\n```\n" % (lang, "\n".join(lines))


def fixture_findings(capsys, colour: str) -> tuple[int, list[str]]:
    path = os.path.join(FIXTURES, colour, f"{NAME}.md")
    code = run.main(["--fast", path, "--no-report"])
    out = capsys.readouterr().out
    listed = out.split("## Находки", 1)[1].split("## Сводка", 1)[0]
    return code, [ln for ln in listed.splitlines() if f" {NAME} " in ln]


# ─────────────────── фикстуры: на артефакт --fast ────────────────────────

@pytest.mark.parametrize("form,count", [
    (CURL, 5),
    (f"{PIN}.python", 1),
    (f"{PIN}.node", 1),
    (f"{PIN}.psmodule", 1),
    (f"{PIN}.winget", 1),
])
def test_red_fixture_carries_form(capsys, form, count):
    code, lines = fixture_findings(capsys, "red")
    assert code == 1
    assert len([ln for ln in lines if f"[{form}]" in ln]) == count


def test_green_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green")
    assert (code, lines) == (0, [])


# ───────────────── curl_follow_hides_redirect: на блок ───────────────────

@pytest.mark.parametrize("line", [
    "curl -sSL https://example.invalid/x -o /tmp/x",
    "curl --location https://example.invalid/x -o /tmp/x",
    "curl --location-trusted https://example.invalid/x -u u:t -o /tmp/x",
    "curl -fsSL https://example.invalid/install.sh | bash",
    "curl -LO https://example.invalid/dist.tgz",
    "curl -sSL -X POST https://example.invalid/hook -d @/tmp/p.json",
])
def test_following_without_the_final_address_is_red(checker, line):
    assert len(marked(check(checker, block(line)), CURL)) == 1


def test_no_L_is_the_bearing_silence(checker):
    """Умолчание curl — остановиться на 3xx — и есть fail-closed (NB-45).
    Молчание здесь доказывает, что форма про `-L`, а не про `curl`."""
    assert marked(check(checker, block("curl -sS https://example.invalid/x -o /tmp/x")),
                  CURL) == []


@pytest.mark.parametrize("line", [
    "curl -sSL -w '%{url_effective}\\n' https://example.invalid/x -o /tmp/x",
    "curl -sSL --max-redirs 0 https://example.invalid/x -o /tmp/x",
    "curl -sSL --max-redirs=0 https://example.invalid/x -o /tmp/x",
])
def test_absolutions(checker, line):
    assert marked(check(checker, block(line)), CURL) == []


def test_bounded_chain_is_not_an_absolution(checker):
    """`--max-redirs 3` отвечает только на третью из трёх gotcha NB-45 (петля).
    «Куда я пришёл» и «что туда ушло» называет только конечный адрес; инвариант
    ветки — «адрес назван», а не «цепь ограничена»."""
    line = "curl -sSL --max-redirs 3 https://example.invalid/x -o /tmp/x"
    assert len(marked(check(checker, block(line)), CURL)) == 1


def test_the_field_absolves_not_the_flag(checker):
    """`-w '%{http_code}'` не называет ничего: оправдывает ПОЛЕ, а не флаг."""
    line = "curl -sSL -w '%{http_code}\\n' https://example.invalid/x -o /tmp/x"
    assert len(marked(check(checker, block(line)), CURL)) == 1


@pytest.mark.parametrize("line", [
    "curl -sS https://example.invalid/x -o /tmp/x; grep -L foo /tmp/x",
    "gh run list --workflow CI -L 1 --json databaseId",
    "grep -L 'нет' public/policy.html",
])
def test_a_foreign_L_is_not_the_subject(checker, line):
    assert marked(check(checker, block(line)), CURL) == []


def test_powershell_fence_is_in_scope(checker):
    """Область расширена ключом `shell_langs_extra`: тот же двоичный curl
    приходит владельцу и в PowerShell-блоке."""
    text = block("curl -sSL https://example.invalid/x -o C:\\tmp\\x", lang="powershell")
    assert len(marked(check(checker, text), CURL)) == 1


# ── правки входа _line_pattern: у каждой свой тест (мутации M11, M12) ────

def test_a_continuation_line_carries_the_absolution(checker):
    """Домашний стиль полосы — перенос `\\`. Оправдание живёт на той же
    КОМАНДЕ, а не на той же строке файла (ложное срабатывание до правки)."""
    text = block("curl -sSL \\", "  -w '%{url_effective}\\n' https://example.invalid/x -o /tmp/x")
    assert marked(check(checker, text), CURL) == []


def test_a_continuation_line_carries_the_flag(checker):
    """Обратная сторона той же правки — ложное МОЛЧАНИЕ: якорь `curl` стоит на
    первой строке, а `-L` уехал на продолжение."""
    text = block("curl -sS -w '%{http_code}\\n' \\", "  -L https://example.invalid/x -o /tmp/x")
    assert len(marked(check(checker, text), CURL)) == 1


def test_a_token_inside_a_comment_is_not_a_command(checker):
    """Хвостовой комментарий: флага `-L` в команде нет вовсе."""
    text = block("curl -sS https://example.invalid/x -o /tmp/x  # -L намеренно не ставим")
    assert marked(check(checker, text), CURL) == []


def test_a_whole_comment_line_is_not_a_command(checker):
    text = block("# лечение: curl -L только вместе с показом конечного адреса",
                 "curl -sS https://example.invalid/x -o /tmp/x")
    assert marked(check(checker, text), CURL) == []


def test_markdown_heading_is_not_a_shell_comment(checker):
    """Область `document` комментарий НЕ снимает: там `#` есть заголовок
    markdown. Соседняя форма `pip_install_outside_venv` стоит `document`."""
    text = "## pip install --user pyyaml\n"
    assert len(marked(check(checker, text), "pip_install_outside_venv")) == 1


# ───────────────── reinstall_without_pins.*: на блок ─────────────────────

@pytest.mark.parametrize("line,form", [
    ("pip install pyyaml", "python"),
    ("pip install --upgrade pip", "python"),
    ("pip install 'mcp>=2,<3'", "python"),
    ("uv pip install --python .venv pyyaml", "python"),
    ("pipx install pre-commit", "python"),
    ("npm install express", "node"),
    ("npm install express@^4.18.2", "node"),
    ("pnpm add zod", "node"),
    ("yarn add lodash", "node"),
    ("Install-Module Pester", "psmodule"),
    ("winget install Git.Git", "winget"),
    ("choco install jq", "winget"),
])
def test_a_moving_reference_is_red(checker, line, form):
    assert len(marked(check(checker, block(line)), f"{PIN}.{form}")) == 1


@pytest.mark.parametrize("line", [
    "pip install pyyaml==6.0.3",
    "pip install -r requirements.txt",
    "pip install -r requirements.txt --require-hashes",
    "pip install --editable .",
    "npm install express@4.18.2",
    "npm ci",
    "npm install",
    "Install-Module Pester -RequiredVersion 5.6.1",
    "winget install Git.Git --version 2.45.1",
])
def test_a_named_redaction_or_a_manifest_absolves(checker, line):
    assert marked(check(checker, block(line)), PIN) == []


def test_the_manifest_reference_is_a_scope_exit_not_a_pin(checker):
    """`-r <файл>` оправдывает потому, что состав файла линтер НЕ ЧИТАЕТ:
    красный здесь был бы вердиктом о непрочитанном содержимом. Предел назван,
    а не опущен (верхняя ступень NB-44 чекеру недоступна)."""
    assert marked(check(checker, block("./.venv/bin/pip install -r requirements.txt")),
                  PIN) == []


def test_powershell_forms_are_case_insensitive(checker):
    """PowerShell регистронезависим по определению языка: без флага
    `install-module` молчал бы, а `-requiredversion` не оправдывал бы."""
    assert len(marked(check(checker, block("install-module Pester", lang="powershell")),
                      f"{PIN}.psmodule")) == 1
    assert marked(check(checker, block("Install-Module Pester -requiredversion 5.6.1",
                                       lang="powershell")), PIN) == []


def test_bash_forms_stay_case_sensitive(checker):
    """У curl `-L` и `-l` — разные флаги; регистр там значим."""
    assert marked(check(checker, block("curl -sSl https://example.invalid/x -o /tmp/x")),
                  CURL) == []


def test_prose_is_not_the_subject(checker):
    """Область `shell_block`, а не `document`: ход, который об установке
    ГОВОРИТ, предметом ветки не является. Выбор измерен на артефакте владельца:
    `document` давал +11 находок, из них ноль внутри блока."""
    text = "Ход разбирает инцидент: `npm install express` без пина ставит другое.\n"
    assert marked(check(checker, text), PIN) == []
