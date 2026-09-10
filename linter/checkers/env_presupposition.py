"""S-03 / К2–К3: предпосылочная форма без предшествующей измеряющей строки.

Опора: контракт §11, «Исполнимость shell-блока», вопрос (2) «Предпосылки»
и (2а) «Гейт — предпосылка блока».
Реестр правок канона §B: рецидив 2026-08-28 — имя сервиса Cloud Run по памяти.

Список форм — данные, а не код: он живёт в linter/manifest.yaml (`forms`) и
расширяется без правки этого модуля. Виды форм:
  kind: line_pattern     — строка совпала с `pattern`; оправдана, если на ней же
                           есть `absolved_by_line` либо выше по блоку есть
                           `absolved_by_above` (измеряющая строка).
  kind: heredoc_length   — heredoc длиннее `max_lines` строк.
Область (`scope`): shell_block (по умолчанию) либо document — форма ловится в
любой строке артефакта, включая прозу и inline-код.

Формы 2026-09-10 (пакет B-P2b-P1; ADR-054, аннотация 2026-09-09):
  curl_follow_hides_redirect      — `curl -L` без `%{url_effective}`: конечный
                                    адрес назначает ответ сервера и нигде не
                                    печатается (NB-45). Лечение curl-специфично:
                                    в Windows PowerShell 5.1 `curl` — алиас
                                    `Invoke-WebRequest`, у которого этого поля
                                    нет вовсе, а редиректы идут по умолчанию;
                                    форма для IWR/IRM имеет ОБРАТНУЮ полярность
                                    (голый вызов уже есть форма) и потому
                                    отдельной записью в этот пакет не входит.
  reinstall_without_pins.<эко>    — переустановка подвижным указателем вместо
                                    неизменяемой редакции (NB-44). Ветка держит
                                    вторую ступень лестницы: строка обязана
                                    назвать точную редакцию либо сослаться на
                                    закоммиченный манифест. Верхняя ступень (пин
                                    хэшем) чекеру НЕДОСТУПНА: он чистая функция
                                    и файлов не открывает, поэтому `-r <файл>`
                                    оправдывает не как пин, а как выход из
                                    предмета. Предел назван, а не опущен.
Обе стоят `scope: shell_block`, а не `document`: выбор измерен на артефакте
владельца — `document` давал +11 находок, из них НОЛЬ внутри блока (ход, который
об установке говорит, а не поручает её). Соседняя `pip_install_outside_venv`
остаётся `document`: её основание не отменяется, прозаический канал не исчезает,
он просто не умножается.

Ключ `requires_above` (добавлен 2026-09-04 вместе с формой
push_workflow_without_scope): форма срабатывает только тогда, когда выше по
охвату есть строка, совпавшая с этим шаблоном. Он не оправдывает, а наоборот —
включает: «`git push` при staged-файле под `.github/workflows/`» из одной
строки не выводится, предпосылка живёт строкой выше, и без неё та же команда
предпосылки о праве `workflow` не несёт.
"""

from __future__ import annotations

import re

from ..common import RED, Finding, shell_blocks, split_lines

NAME = "env_presupposition"

HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# Приведение входа для форм области `shell_block` (заведено 2026-09-10, пакет
# B-P2b-P1). Три замера показали, что форма судит не то, что исполняется:
#   `curl -sS … -o y  # -L намеренно не ставим`   — краснела: токен стоял в
#       комментарии, командой он не является;
#   `curl -sSL \` + `-w '%{url_effective}' …`     — краснела: оправдание уехало
#       на строку продолжения, а это та же команда;
#   `curl -sS -w '%{url_effective}' \` + `-L …`   — МОЛЧАЛА: якорь остался на
#       первой строке, и настоящий случай проходил мимо.
# Лечение — вход, а не порог: строка судится как команда, а не как строка файла.
# Область `document` не трогается намеренно: там `#` есть заголовок markdown, а
# не комментарий оболочки, и перенос строки — разметка, а не сцепка.
CONTINUED = re.compile(r"\\\s*$")
COMMENT_LINE = re.compile(r"^\s*#")
TRAILING_COMMENT = re.compile(r"\s+#.*$")

DEFAULT_FORMS = [
    {
        "name": "pip_install_outside_venv",
        "kind": "line_pattern",
        "scope": "document",
        "pattern": r"\bpip3?\s+install\b",
        "absolved_by_line": r"(\.venv/bin/pip|/venv/bin/pip|\bvenv/bin/pip|"
                            r"python3?\s+-m\s+venv|--python\s+\S*venv)",
        "absolved_by_above": r"(python3?\s+-m\s+venv|source\s+\S*venv/bin/activate|"
                             r"\.\s+\S*venv/bin/activate|VIRTUAL_ENV=)",
        "above_window": 3,
        "message": "`pip install` без venv-пути и без предшествующей строки, создающей "
                   "или активирующей venv: в среде PEP 668 системный pip отказывает "
                   "(externally-managed-environment) — блок падает на предпосылке, "
                   "а не на предмете",
    },
    {
        "name": "gcloud_run_named_service",
        "kind": "line_pattern",
        "scope": "shell_block",
        "pattern": r"\bgcloud\s+run\s+(deploy|revisions|services\s+"
                   r"(update|describe|delete|update-traffic))\b",
        "absolved_by_above": r"\bgcloud\s+run\s+services\s+list\b",
        "message": "`gcloud run …` с именем сервиса без предшествующего "
                   "`gcloud run services list`: имя взято по памяти, "
                   "провал блока неотличим от отсутствия предмета",
    },
    {
        "name": "adb_serial_without_devices",
        "kind": "line_pattern",
        "scope": "shell_block",
        "pattern": r"\badb\s+-s\s+\S+",
        "absolved_by_above": r"\badb\s+devices\b",
        "message": "`adb -s <серийник>` без предшествующего `adb devices`: "
                   "серийник назван по памяти, подключение не измерено",
    },
    {
        "name": "long_heredoc",
        "kind": "heredoc_length",
        "scope": "shell_block",
        "max_lines": 25,
        "message": "heredoc длиннее {max_lines} строк: предпосылка о том, что канал "
                   "доставки переживёт вставку такой длины, не измерена",
    },
]


def commands(numbered: list[tuple[int, str]]) -> list[tuple[int, str]]:
    r"""Строки охвата, приведённые к командам: без комментариев, со склейкой `\`.

    Номер результата — первая строка склейки: находка указывает на начало
    команды, а не на её хвост. Комментарий снимается целиком (`^\s*#`) и хвостом
    (` #…`) — по правилу оболочки `#` начинает комментарий только с начала слова.
    """
    out: list[tuple[int, str]] = []
    pending_ln: int | None = None
    pending = ""
    for ln, raw in numbered:
        text = "" if COMMENT_LINE.match(raw) else TRAILING_COMMENT.sub("", raw)
        if pending_ln is None:
            pending_ln, pending = ln, text
        else:
            pending = pending + " " + text.lstrip()
        if CONTINUED.search(pending):
            pending = CONTINUED.sub("", pending)
            continue
        out.append((pending_ln, pending))
        pending_ln, pending = None, ""
    if pending_ln is not None:
        out.append((pending_ln, pending))
    return out


def _line_pattern(form: dict, spans: list[tuple[str, list[tuple[int, str]]]]) -> list[Finding]:
    # Регистр — данная формы, а не умолчание модуля: PowerShell регистронезависим
    # по определению языка, и без флага `install-module Pester` молчал бы, а
    # корректно запиненная `-requiredversion 5.6.1` краснела бы. Правило,
    # кодирующее соглашение об именовании оболочки вместо класса отказа, — тот же
    # рецидив, что реестр §D, 2026-09-08 (3), п. 3. У bash-форм регистр значим.
    flags = re.IGNORECASE if form.get("ignorecase") else 0
    pat = re.compile(form["pattern"], flags)
    by_line = form.get("absolved_by_line")
    by_line_re = re.compile(by_line, flags) if by_line else None
    by_above = form.get("absolved_by_above")
    by_above_re = re.compile(by_above, flags) if by_above else None
    # Условие срабатывания: форма без него не считается сработавшей вовсе.
    needs = form.get("requires_above")
    needs_re = re.compile(needs, flags) if needs else None
    # Сколько строк выше считаются «измеряющими». None — весь охват (блок/документ).
    above_window = form.get("above_window")
    as_commands = form.get("scope", "shell_block") != "document"

    out: list[Finding] = []
    for _scope_id, numbered in spans:
        if as_commands:
            numbered = commands(numbered)
        for pos, (ln, raw) in enumerate(numbered):
            if not pat.search(raw):
                continue
            if by_line_re and by_line_re.search(raw):
                continue
            lo = 0 if above_window is None else max(0, pos - int(above_window))
            if needs_re and not any(needs_re.search(prev)
                                    for _, prev in numbered[:pos]):
                continue
            if by_above_re and any(by_above_re.search(prev)
                                   for _, prev in numbered[lo:pos]):
                continue
            out.append(Finding(ln, NAME, RED,
                               f"[{form['name']}] " + form["message"]))
    return out


def _heredoc_length(form: dict, spans) -> list[Finding]:
    limit = int(form.get("max_lines", 25))
    out: list[Finding] = []
    for _scope_id, numbered in spans:
        open_at = None
        tag = None
        count = 0
        for ln, raw in numbered:
            if open_at is None:
                m = HEREDOC_OPEN.search(raw)
                if m:
                    open_at, tag, count = ln, m.group(2), 0
                continue
            if raw.strip() == tag:
                if count > limit:
                    out.append(Finding(
                        open_at, NAME, RED,
                        f"[{form['name']}] " +
                        form["message"].format(max_lines=limit) +
                        f" (тело: {count} строк)"))
                open_at, tag, count = None, None, 0
                continue
            count += 1
        if open_at is not None and count > limit:
            out.append(Finding(
                open_at, NAME, RED,
                f"[{form['name']}] " + form["message"].format(max_lines=limit) +
                f" (тело: {count} строк, терминатор не найден)"))
    return out


def check(text: str, config: dict) -> list[Finding]:
    config = config or {}
    forms = config.get("forms") or DEFAULT_FORMS

    doc_lines = split_lines(text)
    doc_span = [("document", list(enumerate(doc_lines, start=1)))]
    blk_span = [(f"block@{b.fence_line}", list(b.numbered()))
                for b in shell_blocks(text, config)]

    findings: list[Finding] = []
    for form in forms:
        spans = doc_span if form.get("scope", "shell_block") == "document" else blk_span
        kind = form.get("kind", "line_pattern")
        if kind == "line_pattern":
            findings.extend(_line_pattern(form, spans))
        elif kind == "heredoc_length":
            findings.extend(_heredoc_length(form, spans))
    return sorted(findings, key=lambda f: (f.line, f.message))
