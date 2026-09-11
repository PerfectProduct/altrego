"""Утверждение о состоянии репозитория, опирающееся на команду уже своей области.

Опора: контракт §11, «Провенанс утверждений оркестратора» (реестр: R-PROV-001),
*Момент:* «любое утверждение о состоянии репозитория, прогона, артефакта или
устройства».

Что меряется — не то же, что мерит `claim_provenance`. Тот спрашивает, есть ли
провенанс рядом, и при виде команды делает `continue`. Этот чекер начинается
ровно там, где тот замолчал: провенанс на месте, команда названа, — и **область
команды уже области утверждения**. Отказ не виден именно потому, что провенанс
соблюдён: счётчик отвечает на свой вопрос верно, а утверждение задаёт другой.

Повод, с материальным расхождением (ход полосы 2026-09-10): состав пакета мерен
`git diff --stat main` и отчитан как 9 путей и 356 строк; коммит показал 14 путей
и 1205 строк. `git diff` не видит неотслеживаемых файлов — счётчик структурно не
видел трети предмета, и утверждение о состоянии репозитория стояло на нём.

Инвариант — в коде, диалект — в данных. Код не называет ни одной команды: пары
«область утверждения ↔ область команды», список узких команд с полем «чего не
видит» и список покрывающих живут в `linter/manifest.yaml`.

Область утверждения (`claim_scopes`) — положительный список, а не изъятие:
чекер судит только те утверждения, чей предмет назван — состав правки, рабочее
дерево, незакоммиченное, состав коммита. Утверждение, чей предмет **и есть**
дифф («В diff 4 файла — выдача `git diff --stat`»), в список не входит и молчит
по построению: там область команды равна области утверждения. Эта строка стоит в
`linter/fixtures/green/claim_provenance.md` и обязана остаться зелёной.

Четыре сужения, каждое по признаку:

  * **Обрезка, а не труба.** Покрывающая команда перестаёт покрывать, если её
    вывод обрезан (`| head -N`, `| tail -N`), — но не от того, что он вообще идёт
    в трубу: `git status --porcelain | wc -l` считает всё. Мера — усечение, а не
    конвейер.
  * **Поручение — не утверждение.** Пункт списка, начинающийся с инфинитива
    («Сверить правку и прислать вывод целиком»), адресован владельцу и притязания
    о состоянии не делает.
  * **Адрес пункта канона — чужой предмет.** «Строку 113 файла контракта» судит
    нога 3 `claim_provenance`; такие строки исключены явно, чтобы один отказ не
    назывался дважды.
  * **Проза, а не ограда.** Утверждение ищется только вне огороженных блоков:
    команда и её выдача — не утверждение оркестратора. Команды при этом читаются
    и из прозы (inline-код), и из ближайшей ограды ниже: провенанс утверждения
    обычно стоит блоком под ним.

Соседи. `whitespace_diff` меряет ту же команду по другому вопросу — содержательна
ли правка; `-w` оправдывает его и **не** оправдывает этот чекер: фильтр пробелов
меняет, что считается правкой, а не то, какие файлы вообще попадают в счёт.

Сценарий чекера — S-24 (`scenarios/s24.yaml`, пакет B-P2b P3a, ярус 2,
2026-09-10): S-02 держит `claim_provenance` и перечисляет свои формы закрытым
списком, а этот класс в нём не описан — отсюда отдельный сценарий, а не нога.

Чистая функция: ни сети, ни LLM, ни файловых эффектов.
"""

from __future__ import annotations

import re

from ..common import RED, Finding, in_block_lines, parse_blocks, split_lines

# Имя обязано совпасть с `name` записи манифеста дословно: run.py отбирает
# собственные находки чекера по `f.checker == name`, и расхождение дало бы
# вечный `red-fixture-silent` и дисквалификацию.
NAME = "repo_state_claim"
FORM = "command_scope_narrower_than_claim"

DEFAULT_CLAIM_SCOPES = {
    "worktree": (r"(?:состав\w*\s+(?:правк\w+|пакет\w+|изменени\w+)|"
                 r"рабоч\w+\s+дерев\w+|working\s+tree|незакоммич\w+)"),
    "commit": r"(?:состав\w*\s+коммит\w*|коммит\s+нес[ёе]т)",
}
# Притязание на счёт либо на исчерпанность: без него «рабочее дерево» — тема, а
# не утверждение о величине.
DEFAULT_COUNTED = (r"(?:\d+\s*(?:файл\w*|пут(?:ь|и|ей|ям)|строк\w*)|"
                   r"(?:файл\w*|пут(?:ь|и|ей)|строк\w*)\s*[—:-]\s*\d+|"
                   r"\bвс[её]\b|\bцеликом\b|\bполностью\b|\bчист\w+|\bпуст\w+)")
DEFAULT_NARROW = [
    {"pattern": r"git\s+diff(?![^`\n]*--cached)(?![^`\n]*--staged)",
     "blind": "`git diff` не видит неотслеживаемых файлов"},
    {"pattern": r"\|\s*head\s+-\d+", "blind": "вывод обрезан `head`"},
    {"pattern": r"\|\s*tail\s+-\d+", "blind": "вывод обрезан `tail`"},
    {"pattern": r"git\s+log[^`\n]*\s-(?:n\s*)?\d+\b",
     "blind": "окно журнала ограничено числом строк"},
    {"pattern": r"\bls(?![^`\n]*-[A-Za-z]*R)\b", "blind": "`ls` не рекурсивен"},
    {"pattern": r"-maxdepth\s*1\b", "blind": "обход ограничен глубиной 1"},
]
DEFAULT_COVERING = {
    # `git add -A && git diff --cached` сюда не входит: он недостижим — узость
    # снимается отрицательным просмотром в самом шаблоне узких команд.
    "worktree": r"(?:git\s+status\s+--porcelain|git\s+ls-files[^`\n]*--others)",
    "commit": r"(?:git\s+show[^`\n]*--stat|git\s+diff[^`\n]*--cached)",
}
# Усечение снимает покрытие: «покрывающая, но обрезанная» — не покрывающая.
DEFAULT_TRUNCATION = r"\|\s*(?:head|tail)\s+-\d+"
# Предел, названный словами, — тоже ответ: область сужена сознательно.
DEFAULT_NAMED_LIMIT = (r"(?:без\s+уч[ёе]та\s+неотслеж\w*|только\s+отслеж\w*|"
                       r"untracked\s+не\s+вход\w*|предел\s+назван)")
# Поручение владельцу: пункт списка с инфинитивом.
DEFAULT_INSTRUCTION = r"^\s*(?:[-*+]|\d+[.)])\s*\*{0,2}[А-ЯЁA-Za-zа-яё]+(?:ть|ти|чь)\b"
# Чужой предмет: адрес пункта канона судит нога 3 claim_provenance.
DEFAULT_FOREIGN_REFS = [
    r"§\s*\d+(?:\.\d+)*",
    r"\b[\w.-]+\.md:\d+",
    r"\b(?:строк\w+|line)\s+\d+\b",
]
INLINE = re.compile(r"`([^`\n]+)`")


def _compile(patterns) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def check(text: str, config: dict) -> list[Finding]:
    config = config or {}
    scopes = config.get("claim_scopes") or DEFAULT_CLAIM_SCOPES
    counted = re.compile(config.get("counted_pattern", DEFAULT_COUNTED), re.I)
    narrow = config.get("narrow_commands") or DEFAULT_NARROW
    covering = config.get("covering_commands") or DEFAULT_COVERING
    truncation = re.compile(config.get("truncation_pattern", DEFAULT_TRUNCATION), re.I)
    named_limit = re.compile(config.get("named_limit_pattern", DEFAULT_NAMED_LIMIT), re.I)
    instruction = re.compile(config.get("instruction_pattern", DEFAULT_INSTRUCTION), re.I)
    foreign = _compile(config.get("foreign_ref_patterns") or DEFAULT_FOREIGN_REFS)
    window = int(config.get("command_window", 2))
    block_reach = int(config.get("block_reach", 8))

    lines = split_lines(text)
    blocked = in_block_lines(text, config)
    # Строки оград — источник команд, но не место утверждения.
    block_lines: dict[int, str] = {}
    for b in parse_blocks(text, config):
        for ln, body in b.numbered():
            block_lines[ln] = body

    scope_res = {k: re.compile(v, re.I) for k, v in scopes.items()}
    cover_res = {k: re.compile(v, re.I) for k, v in covering.items()}
    narrow_res = [(re.compile(n["pattern"], re.I), n["blind"]) for n in narrow]

    findings: list[Finding] = []
    for idx, line in enumerate(lines):
        if (idx + 1) in blocked:
            continue
        if instruction.match(line) or any(f.search(line) for f in foreign):
            continue
        if not counted.search(line):
            continue
        scope = next((k for k, r in scope_res.items() if r.search(line)), None)
        if scope is None:
            continue
        lo, hi = max(0, idx - window), min(len(lines) - 1, idx + window)
        near = [lines[k] for k in range(lo, hi + 1)]
        # Ближайшая ограда ниже: провенанс утверждения обычно стоит блоком под ним.
        near += [block_lines[k + 1] for k in range(idx + 1,
                                                   min(len(lines), idx + window + block_reach))
                 if (k + 1) in block_lines]
        near = "\n".join(near)
        cmds = " ".join(INLINE.findall(near)) + "\n" + near
        if named_limit.search(near):
            continue
        cover = cover_res.get(scope)
        if cover is not None and cover.search(cmds) and not truncation.search(cmds):
            continue
        hit = next(((r, blind) for r, blind in narrow_res if r.search(cmds)), None)
        if hit is None:
            continue
        findings.append(Finding(
            idx + 1, NAME, RED,
            f"[{FORM}] утверждение о состоянии репозитория ({scope}) опирается на "
            f"команду `{hit[0].search(cmds).group(0).strip()}`, область которой уже "
            f"области утверждения: {hit[1]}. Провенанс соблюдён, и потому отказ не "
            f"виден: счётчик отвечает на свой вопрос верно, а утверждение задаёт "
            f"другой — расхождение всплывёт не здесь, а на следующей команде"))
    return sorted(findings, key=lambda f: (f.line, f.message))
