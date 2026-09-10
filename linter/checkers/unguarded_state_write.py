"""Запись по непроверенному чтению: между чтением состояния и записью по нему
нет проверки, что чтение состоялось.

Опора: реестр правок канона `00-system/canon-corrections-register.md`, §D,
наблюдения 2026-09-08 (3), пункт 3 — К6 **с материальным ущербом**. Блок правки
`claude_desktop_config.json` в PowerShell не имел проверки между чтением и
записью: `ConvertFrom-Json` упал на висячей запятой, оболочка продолжила
построчно, `$j` осталась объектом из прошлого сеанса консоли, и запись затёрла
правку владельца. Канон несёт «цепочки с побочным эффектом — через `&&`», но
это формулировка про bash; в PowerShell ту же роль играет `if (-not $x) {
throw }`, и переноса не произошло. Лечение названо самим пунктом и здесь
исполнено дословно: **«между чтением состояния и записью по нему стоит проверка,
что чтение состоялось; форма проверки зависит от оболочки»**.

Отсюда деление труда: **инвариант — в коде, диалект — в данных.** Код ищет
пару «строка, связавшая имя с прочитанным состоянием» → «строка, меняющая
состояние И ссылающаяся на это имя» и смотрит, стоит ли между ними проверка.
Оболочку код не называет ни разу: словари чтения, эффекта и проверки лежат в
`linter/manifest.yaml` по записи на диалект (`config.dialects`), диалект
выбирается языком ограды, а блок без языка судится `dialect_default`.

Почему отдельный чекер, а не форма `shell_mech`. Охват блоков у чекера один на
все его формы, а этой форме нужен PowerShell. Отдай его `shell_mech` — и
`windows_path` покраснеет на пути `D:\…`, который в PowerShell **верен**, а
green-фикстура `shell_mech`, обязанная нести корректный PowerShell-блок, дала бы
`green-fixture-red` и дисквалификацию чекера на каждом прогоне (измерено).
Расширять `shared.shell_langs` нельзя тем более: это девять чекеров из
шестнадцати, причём двое дома промптов молча **сужаются** (`linter/prompts.py`
снимает блок, чей язык лежит в `shell_langs`). Поэтому охват расширяется одним
ключом `shell_langs_extra` и только этому чекеру.

Четыре сужения оправданий — не вкус, а замер: наивные варианты зеленили ровно
тот инцидент, ради которого чекер заведён.
  * bash, сцепка `&&` — оправдывает, только если эффект стоит на той же команде
    справа от неё. Иначе `cd /repo && VER=$(…)` (сцепка **слева** от чтения)
    и `VER=$(…) && echo` (сцеплено с печатью) зеленили бы блок.
  * PowerShell, `-ErrorAction Stop` — оправдывает, только если стоит на
    последней ступени конвейера чтения. В инциденте упал `ConvertFrom-Json`
    **ниже по конвейеру**, а флаг висел бы на `Get-Content`.
  * bash, `set -e` — не оправдывает чтение-объявление (`export VER=$(…)`):
    объявление маскирует код возврата подстановки (ShellCheck SC2155,
    ADR-054 NB-43), и errexit его не видит.
  * правая часть, **порождающая** значение (`$(mktemp)`, `$(date …)`), чтением
    состояния не считается.

Чистая функция: ни сети, ни LLM, ни файловых эффектов.
"""

from __future__ import annotations

import re

from ..common import RED, Finding, mask_spans, shell_blocks
from .shell_mech import _rows as shell_rows

# Имя обязано совпасть с `name` записи манифеста дословно: run.py отбирает
# собственные находки чекера по `f.checker == name`, и расхождение дало бы
# вечный `red-fixture-silent` и дисквалификацию. Имя ветки пакета живёт в
# сообщении тегом, а не здесь.
NAME = "unguarded_state_write"
FORM = "effect_after_unchained_predicate"

# Кавычки маскируются до сверки со словарём эффекта: иначе `echo "$VER > 1.0"`
# и `awk '$1 > 0'` читаются как перенаправление в файл (измерено).
QUOTE_SPANS = [r'"[^"\n]*"', r"'[^'\n]*'"]

DEFAULT_DIALECT = "bash"
DEFAULT_DIALECTS = [
    {
        "name": "bash",
        "langs": ["bash", "sh", "shell", "zsh", "console", "shell-session"],
        "read_patterns": [
            r"(?:^|&&\s*|\|\|\s*)\s*(?:(?:local|export|declare|readonly|typeset)\s+)?"
            r"(?P<var>[A-Za-z_]\w*)=[^\n;&|]*(?:\$\(|`)",
        ],
        "read_exclude_patterns": [r"\$\(\s*(?:mktemp|date|uuidgen|seq|printf|echo)\b"],
        "effect_patterns": [
            r"\bgit\s+(?:push|commit|tag|reset|checkout|restore|apply)\b",
            r"\bgh\s+(?:pr|issue|release|repo|secret|variable|workflow)\s+"
            r"(?:create|merge|close|edit|delete|upload|set|remove)\b",
            r"\bcurl\b[^|]*?-X\s*(?:POST|PUT|PATCH|DELETE)\b",
            r"\bsed\s+-i\b",
            r"\btee\b",
            r"(?<![0-9&\\])>>?\s*[\"']?[~./$\w]",
            r"^\s*(?:rm|mv|cp|ln)\s",
            r"\bgcloud\s+\w+\s+(?:deploy|update)\b",
            r"\bkubectl\s+(?:apply|delete|patch)\b",
            r"\bdocker\s+push\b",
        ],
        "guard_inline_patterns": [r"\|\|\s*\{?\s*(?:exit|return)\b"],
        "guard_inline_last_stage_patterns": [],
        "guard_between_patterns": [
            r"\[\[?[^\n]*<VAR>[^\n]*\]\]?\s*(?:\|\||&&)\s*\{?\s*(?:exit|return)\b",
            r"^\s*if\s[^\n]*<VAR>[^\n]*\b(?:exit|return)\b",
            r"^\s*(?:exit|return)\b",
        ],
        "guard_block_patterns": [r"^\s*set\s+-[A-Za-z]*e"],
        "guard_block_masked_patterns": [r"^\s*(?:local|export|declare|readonly|typeset)\s"],
        "var_reference": r"\$\{?<VAR>\b",
        "ignorecase": False,
    },
    {
        "name": "powershell",
        "langs": ["powershell", "pwsh", "ps1"],
        "read_patterns": [
            r"^\s*(?P<var>\$[A-Za-z_]\w*)\s*=\s*[^\n]*\b(?:Get-Content|Get-Item|"
            r"Get-ChildItem|Get-ItemProperty|Import-Csv|Import-Clixml|"
            r"ConvertFrom-Json|Select-String|Get-Process|Get-Service|Test-Path|"
            r"Invoke-RestMethod|Invoke-WebRequest)\b",
        ],
        "read_exclude_patterns": [],
        "effect_patterns": [
            r"\b(?:Set-Content|Add-Content|Out-File|Export-Csv|Export-Clixml|"
            r"Set-ItemProperty|Set-Service)\b",
            r"\b(?:Remove|Copy|Move|Rename|New)-Item\b",
            r"\bInvoke-RestMethod\b[^\n]*-Method\s+(?:Post|Put|Patch|Delete)\b",
            r"(?<![0-9&\\])>>?\s*[\"']?[~./$\w]",
        ],
        "guard_inline_patterns": [],
        "guard_inline_last_stage_patterns": [r"-ErrorAction\s+[\"']?Stop"],
        "guard_between_patterns": [
            r"if\s*\(\s*(?:-not|!)\s*<VAR>\s*\)",
            r"if\s*\(\s*\$null\s+-eq\s+<VAR>\s*\)",
            r"if\s*\(\s*<VAR>\s+-eq\s+\$null\s*\)",
            r"if\s*\(\s*-not\s+\$\?\s*\)",
            r"^\s*\}\s*catch\b",
        ],
        "guard_block_patterns": [
            r"\$ErrorActionPreference\s*=\s*[\"']?Stop",
            r"^\s*try\s*\{",
        ],
        "guard_block_masked_patterns": [],
        "var_reference": r"<VAR>\b",
        "ignorecase": True,
    },
]

# Голый `cd` — предмет формы `cd_without_chain` той же полосы. Вторая находка
# ТОГО ЖЕ класса на той же строке называла бы один отказ дважды.
DEFAULT_EXCLUDE = [r"^\s*cd\s"]

COMMENT = re.compile(r"^\s*#")


def _compile(patterns, flags=0):
    return [re.compile(p, flags) for p in (patterns or [])]


def _steps(block):
    """Шаги блока: (номер строки, текст шага, сырая строка).

    Строка режется на шаги по `;` — точка с запятой разделяет команды, и провал
    левой правую не останавливает. По `&&`/`||` не режем: они и есть сцепка,
    и разрыв там стёр бы ровно то, что меряется. Тело heredoc и комментарии
    снимаются приёмом `shell_mech._rows` — общий дом, а не шестая копия признака.
    """
    rows, _open = shell_rows(block)
    out = []
    for ln, raw, inside in rows:
        if inside or COMMENT.match(raw):
            continue
        for seg in raw.split(";"):
            if seg.strip():
                out.append((ln, seg, raw))
    return out


def check(text: str, config: dict) -> list[Finding]:
    config = config or {}
    dialects = config.get("dialects") or DEFAULT_DIALECTS
    default_name = config.get("dialect_default", DEFAULT_DIALECT)
    exclude = _compile(config.get("exclude_patterns") or DEFAULT_EXCLUDE)
    quotes = config.get("quote_spans") or QUOTE_SPANS

    by_lang = {}
    fallback = None
    for d in dialects:
        for lang in d.get("langs") or []:
            by_lang[lang] = d
        if d.get("name") == default_name:
            fallback = d
    fallback = fallback or dialects[0]

    findings: list[Finding] = []
    for b in shell_blocks(text, config):
        d = by_lang.get(b.lang, fallback)
        flags = re.IGNORECASE if d.get("ignorecase") else 0
        reads = _compile(d.get("read_patterns"), flags)
        read_skip = _compile(d.get("read_exclude_patterns"), flags)
        effects = _compile(d.get("effect_patterns"), flags)
        inline = _compile(d.get("guard_inline_patterns"), flags)
        last_stage = _compile(d.get("guard_inline_last_stage_patterns"), flags)
        block_guard = _compile(d.get("guard_block_patterns"), flags)
        masked = _compile(d.get("guard_block_masked_patterns"), flags)
        between_raw = d.get("guard_between_patterns") or []
        var_ref_raw = d.get("var_reference") or ""

        steps = _steps(b)
        # Чтения шага: имя → позиция конца совпадения (нужна для сцепки).
        read_at: dict[int, tuple[str, int]] = {}
        for pos, (_ln, seg, _raw) in enumerate(steps):
            if any(x.search(seg) for x in read_skip):
                continue
            for r in reads:
                m = r.search(seg)
                if m and m.groupdict().get("var"):
                    read_at[pos] = (m.group("var"), m.end())
                    break

        for pos, (ln, seg, raw) in enumerate(steps):
            if any(x.search(seg) for x in exclude):
                continue
            masked_seg = mask_spans(seg, quotes)
            hit = next((e.search(masked_seg) for e in effects if e.search(masked_seg)), None)
            if hit is None:
                continue
            # Ближайшее выше (или на этом же шаге) чтение, на имя которого
            # эффект ссылается. Связь по имени и есть сужение: запись «по
            # прочитанному», а не всякая запись после всякого чтения.
            src = None
            for j in range(pos, -1, -1):
                if j not in read_at:
                    continue
                var, end = read_at[j]
                ref = re.compile(var_ref_raw.replace("<VAR>", re.escape(var)), flags)
                if ref.search(seg if j != pos else seg[end:]):
                    src = (j, var, end)
                    break
            if src is None:
                continue
            j, var, end = src
            read_ln, read_seg, read_raw = steps[j]

            # Сцепка `&&` оправдывает только ТУ ЖЕ команду: она держит то, что
            # стоит справа от неё, и ничего ниже. Наивное «`&&` где-нибудь на
            # строке чтения» зеленило бы `cd /repo && VER=$(…)` (сцепка слева от
            # чтения) и `VER=$(…) && echo` (сцеплено с печатью, а запись ниже).
            if j == pos and hit.start() >= end and "&&" in seg[end:hit.start()]:
                continue
            # `|| exit|return` на строке чтения обрывает блок целиком, поэтому
            # оправдывает и запись ниже. Ищется в хвосте ПОСЛЕ совпадения
            # чтения. У диалекта powershell слот пуст и недостижим: там шаблон
            # чтения жаден до конца строки, и хвоста не остаётся — измерено
            # мутацией M9 2026-09-10. Названо здесь, чтобы шаблон, положенный
            # туда позже, не читался как действующий (болезнь `prompt_min_lines`).
            if any(g.search(read_seg[end:]) for g in inline):
                continue
            # Проверка на ПОСЛЕДНЕЙ ступени конвейера строки чтения: в инциденте
            # 2026-09-08 упал `ConvertFrom-Json` ниже по конвейеру, а флаг висел
            # бы на `Get-Content`. Поиск по всей строке зеленил бы сам повод.
            if any(g.search(read_seg.rsplit("|", 1)[-1]) for g in last_stage):
                continue
            # Проверка между чтением и записью. Ищется по СЫРЫМ строкам
            # охвата, а не по шагам: `;` режет шаги, но `if …; then exit 1; fi`
            # есть одна проверка, а не три команды, и по шагам она невидима.
            span, seen = [], set()
            for k in range(j, pos + 1):
                if steps[k][0] not in seen:
                    seen.add(steps[k][0])
                    span.append(steps[k][2])
            between = [re.compile(p.replace("<VAR>", re.escape(var)), flags)
                       for p in between_raw]
            if any(g.search(s) for s in span for g in between):
                continue
            # Режим обрыва выше по блоку — но не при чтении-объявлении:
            # объявление маскирует код возврата подстановки (SC2155).
            if not any(mk.search(read_seg) for mk in masked) and \
               any(g.search(steps[k][2]) for k in range(0, j + 1) for g in block_guard):
                continue

            findings.append(Finding(
                ln, NAME, RED,
                f"[{FORM}] запись `{hit.group(0).strip()}` идёт по значению "
                f"`{var}`, прочитанному строкой {read_ln} "
                f"(`{read_seg.strip()[:60]}`), а проверки, что чтение "
                f"состоялось, между ними нет: при провале чтения оболочка "
                f"({d.get('name')}) продолжает следующей командой, и запись "
                f"ложится по пустому либо оставшемуся от прошлого сеанса "
                f"значению — провал неотличим от успеха"))

    return sorted(findings, key=lambda f: (f.line, f.message))
