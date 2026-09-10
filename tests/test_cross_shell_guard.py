"""Ветка `effect_after_unchained_predicate` чекера `unguarded_state_write`.

Повод: реестр правок канона §D, наблюдения 2026-09-08 (3), пункт 3 — К6 с
материальным ущербом. Лечение названо там же и меряется здесь: «между чтением
состояния и записью по нему стоит проверка, что чтение состоялось; форма
проверки зависит от оболочки».

Единица диспозиции — «на артефакт `--fast`» для фикстур и «на блок» для строк.
Каждое утверждение о рантайме исполняется вызовом, а не чтением кода.
"""

from __future__ import annotations

import os

import pytest
import yaml

import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "linter", "fixtures")
NAME = "unguarded_state_write"


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(os.path.join(ROOT, "linter", "manifest.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@pytest.fixture(scope="module")
def checker(manifest) -> dict:
    active, _skipped, failed = run.load_checkers(manifest, "handoff")
    assert failed == []
    return {c["name"]: c for c in active}[NAME]


def check(checker: dict, text: str) -> list[str]:
    return [f.message for f in checker["module"].check(text, checker["config"])]


def block(lang: str, *lines: str) -> str:
    return "```%s\n%s\n```\n" % (lang, "\n".join(lines))


def fixture_findings(capsys, colour: str) -> tuple[int, list[str]]:
    path = os.path.join(FIXTURES, colour, f"{NAME}.md")
    code = run.main(["--fast", path, "--no-report"])
    out = capsys.readouterr().out
    listed = out.split("## Находки", 1)[1].split("## Сводка", 1)[0]
    return code, [ln for ln in listed.splitlines() if f" {NAME} " in ln]


# ─────────────────── фикстуры: на артефакт --fast ────────────────────────

@pytest.mark.parametrize("dialect", ["powershell", "bash"])
def test_red_fixture_carries_each_dialect(capsys, dialect):
    """Красная фикстура краснеет В ОБЕИХ оболочках — это и есть доказательство
    переноса класса; рассуждение о переносе доказательством не является."""
    _code, lines = fixture_findings(capsys, "red")
    assert len([ln for ln in lines if f"({dialect})" in ln]) == 1


def test_red_fixture_total_is_two(capsys):
    code, lines = fixture_findings(capsys, "red")
    assert code == 1
    assert len(lines) == 2


def test_green_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green")
    assert (code, lines) == (0, [])


# ────────────────────── PowerShell: на блок ──────────────────────────────

INCIDENT = ('$p = "D:\\Obsidian\\TheyGrow\\claude_desktop_config.json"',
            "$j = Get-Content $p -Raw | ConvertFrom-Json",
            "$j | ConvertTo-Json -Depth 12 | Set-Content $p -Encoding UTF8")


def test_incident_block_is_red(checker):
    """Дословный блок инцидента 2026-09-08 (3) п. 3."""
    assert len(check(checker, block("powershell", *INCIDENT))) == 1


def test_check_after_the_write_is_not_a_check(checker):
    text = block("powershell", INCIDENT[0], INCIDENT[1], INCIDENT[2],
                 'if (-not $j) { throw "не прочитано" }')
    assert len(check(checker, text)) == 1


@pytest.mark.parametrize("guard", [
    'if (-not $j) { throw "не прочитано" }',
    "if ($null -eq $j) { exit 1 }",
    "if (-not $?) { throw }",
])
def test_check_between_absolves(checker, guard):
    assert check(checker, block("powershell", INCIDENT[0], INCIDENT[1], guard,
                                INCIDENT[2])) == []


def test_erroraction_on_a_non_final_stage_does_not_absolve(checker):
    """Инцидент упал в `ConvertFrom-Json` — НИЖЕ по конвейеру, чем флаг.

    Оправдание, зеленящее собственный повод, — тот же рецидив «правило про
    оболочку вместо класса», ради которого чекер и заведён.
    """
    text = block("powershell", INCIDENT[0],
                 "$j = Get-Content $p -Raw -ErrorAction Stop | ConvertFrom-Json",
                 INCIDENT[2])
    assert len(check(checker, text)) == 1


def test_erroraction_on_the_last_stage_absolves(checker):
    text = block("powershell", INCIDENT[0],
                 "$j = Get-Content $p -Raw | ConvertFrom-Json -ErrorAction Stop",
                 INCIDENT[2])
    assert check(checker, text) == []


@pytest.mark.parametrize("guard", ["$ErrorActionPreference = 'Stop'", "try {"])
def test_block_mode_absolves(checker, guard):
    assert check(checker, block("powershell", guard, *INCIDENT)) == []


def test_powershell_dialect_is_case_insensitive(checker):
    """PowerShell регистронезависим по определению языка; правило, кодирующее
    регистр имён, — правило про оболочку, а не про класс отказа."""
    lowered = block("powershell", INCIDENT[0],
                    "$j = get-content $p -Raw | convertfrom-json",
                    "$j | convertto-json | set-content $p")
    assert len(check(checker, lowered)) == 1
    guarded = block("powershell", INCIDENT[0],
                    "$j = get-content $p -Raw | convertfrom-json",
                    'if (-Not $j) { THROW "нет" }',
                    "$j | convertto-json | set-content $p")
    assert check(checker, guarded) == []


def test_literal_assignment_is_not_a_read(checker):
    text = block("powershell", '$p = "D:\\Obsidian\\TheyGrow\\config.json"',
                 '$p | Set-Content "C:\\tmp\\copy.json"')
    assert check(checker, text) == []


# ───────────────────────── bash: на блок ─────────────────────────────────

READ = "VER=$(jq -r .version package.json)"
WRITE = 'gh release create "v$VER" --notes "сборка"'


def test_read_then_write_is_red(checker):
    assert len(check(checker, block("bash", READ, WRITE))) == 1


def test_errexit_does_not_absolve_masked_declare(checker):
    """SC2155 (ADR-054 NB-43): объявление маскирует код возврата подстановки."""
    text = block("bash", "set -euo pipefail", "export " + READ, WRITE)
    assert len(check(checker, text)) == 1


def test_errexit_absolves_a_plain_read(checker):
    assert check(checker, block("bash", "set -euo pipefail", READ, WRITE)) == []


def test_chain_on_the_same_command_absolves(checker):
    assert check(checker, block("bash", f"{READ} && {WRITE}")) == []


def test_chain_left_of_the_read_does_not_absolve(checker):
    """`cd /repo && VER=$(…)`: сцепка держит то, что справа от неё, и ничего
    ниже. Это доминирующая форма green/shell_mech.md — наивное правило
    глушилось бы стилем, которому учит собственная зелёная фикстура."""
    assert len(check(checker, block("bash", f"cd /repo && {READ}", WRITE))) == 1


def test_chain_with_a_print_does_not_absolve(checker):
    text = block("bash", f'{READ} && echo "прочитано"', WRITE)
    assert len(check(checker, text)) == 1


@pytest.mark.parametrize("guard", [
    '[ -n "$VER" ] || exit 1',
    'if [ -z "$VER" ]; then exit 1; fi',
])
def test_check_between_absolves_bash(checker, guard):
    assert check(checker, block("bash", READ, guard, WRITE)) == []


def test_semicolon_is_not_a_chain(checker):
    """`;` разделяет команды: провал левой правую не останавливает."""
    assert len(check(checker, block("bash", f"{READ}; {WRITE}"))) == 1


@pytest.mark.parametrize("line", [
    'SHA="$(git rev-parse HEAD)"',      # чтение → чтение ниже
    "LOG=$(mktemp)",                    # порождение значения, не чтение состояния
])
def test_reads_without_a_write_by_the_value_are_silent(checker, line):
    text = block("bash", line, 'gh run list --commit "$SHA" --json databaseId',
                 'git status | tee "$LOG"')
    assert check(checker, text) == []


def test_quoted_comparison_is_not_a_redirect(checker):
    """Маскировка кавычек: `echo "$VER > 1.0"` записью в файл не является."""
    assert check(checker, block("bash", READ, 'echo "$VER > 1.0"')) == []


def test_write_without_reference_to_the_read_is_silent(checker):
    assert check(checker, block("bash", READ, "git push origin HEAD")) == []


def test_cd_is_the_subject_of_another_form(checker):
    """Голый `cd` держит `cd_without_chain`; вторая находка того же класса на
    той же строке называла бы один отказ дважды."""
    text = block("bash", "cd /mnt/d/Obsidian/TheyGrow", "git add -A",
                 'git commit -m "правки"')
    assert check(checker, text) == []


def test_heredoc_body_is_inserted_text(checker):
    text = block("bash", 'cat > /tmp/x.ps1 <<"PS1"',
                 "$j = Get-Content $p -Raw | ConvertFrom-Json",
                 "$j | ConvertTo-Json | Set-Content $p", "PS1")
    assert check(checker, text) == []


# ─────────────────── охват: язык ограды, не маркер ───────────────────────

def test_powershell_fence_is_in_scope_by_language(checker):
    assert len(check(checker, block("powershell", *INCIDENT))) == 1


def test_shared_shell_langs_is_not_widened(manifest):
    """Общий список не расширен: его расширение молча СУЖАЕТ два чекера дома
    промптов (linter/prompts.py снимает блок, чей язык лежит в shell_langs) и
    даёт shell_mech.windows_path ложный красный на пути `D:\\…`."""
    assert "powershell" not in manifest["shared"]["shell_langs"]


def test_scope_is_widened_only_for_this_checker(manifest):
    extra = {c["name"]: (c.get("config") or {}).get("shell_langs_extra")
             for c in manifest["checkers"]}
    assert "powershell" in extra[NAME]
    assert extra["shell_mech"] is None


def test_red_fixture_powershell_fence_carries_no_handoff_marker():
    """Статическое свойство: с маркером блок стал бы исполняемым для всех
    чекеров, и мутация «снять shell_langs_extra» не покрасила бы ни одного
    теста — кросс-оболочность осталась бы недоказанной."""
    with open(os.path.join(FIXTURES, "red", f"{NAME}.md"), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    fence = next(i for i, ln in enumerate(lines) if ln.startswith("```powershell"))
    assert not any("Handoff for" in ln for ln in lines[max(0, fence - 3):fence])


def test_abort_on_the_read_line_absolves_below(checker):
    """`|| exit` на строке чтения обрывает блок целиком — значит оправдывает и
    запись ниже. Слот `guard_inline_patterns` диалекта bash живой; у powershell
    он пуст и недостижим (шаблон чтения жаден до конца строки, измерено)."""
    assert check(checker, block("bash", f"{READ} || exit 1", WRITE)) == []
