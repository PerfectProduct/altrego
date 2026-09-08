#!/usr/bin/env python3
"""Мост MCP: ход-линтер полосы как инструмент оркестратора (stdio-сервер).

Повод — единая очередь контура, позиция 2 (вольт,
`02-synthesis/target-state-and-roadmap-r2.md`, §6): сегодня каждый детектор
срабатывает ПОСЛЕ того, как ход выдан, и красный доходит до оркестратора ходом
позже, через терминал владельца. Сервер переводит те же детекторы в режим «до»:
черновик хода меряется перед отправкой. Связь мягкая — жёстким гейтом остаётся
CI (`.github/workflows/ci.yml`, job `gate`).

**Второго линтера здесь нет.** Модуль — тонкий переходник: он зовёт готовый
конвейер `run.py` (`load_config` → `load_checkers` → `calibrate` → `run_text`) и
ничего о предмете не решает сам. Своей логики чекеров, своих порогов и своих
списков форм у него нет: они живут в `linter/manifest.yaml` и `config.yaml`, как
и прежде. Копия конвейера означала бы, что «зелёный до выдачи» и «зелёный в
прогоне» — разные утверждения.

Три инструмента:

* `check_turn(text, kind="handoff")` — прогон всех чекеров вида по черновику,
  который на диске не лежит. Калибровка идёт перед целью, как в `--fast`;
  дисквалифицированный чекер не голосует, а стоит в «не измерено».
* `list_rules()` — пункты канона из `rules/registry.yaml` (без пересчёта хэшей:
  хэши считаются по вольту, а он отсюда только читается прогоном `--full`).
* `queue()` — голова единой очереди контура из рабочей копии вольта.

Fail-closed, как весь прогон (несущий документ, слой 0, п. 5): отказ чекера,
отказ импорта, снятый лимит и провал калибровки делают `passed` ложным и
называются поимённо. Ноль находок при отказавшем контролёре — «не измерено», а
не «зелёно» (§11, R-VACUUM-007).

Запуск (измерено 2026-09-08): Claude Desktop на Windows поднимает сервер как
`wsl.exe -e <python> -u <абсолютный путь>`; процесс получает cwd
`/mnt/c/Windows/system32` и НЕ наследует окружение входа WSL. Отсюда три
свойства модуля:

1. Все пути абсолютные — от `__file__` либо из окружения; на cwd не опирается
   ничто.
2. Незаданная `ALTREGO_VAULT_MASTER` — читаемый отказ инструмента, а не
   молчаливое умолчание: путь вольта приходит только из окружения (CLAUDE.md,
   «Пути вольта — переменные окружения»), и запись сервера в конфиге клиента
   обязана нести его в блоке `env`.
3. Собственных стартовых эффектов нет: ни файлов блокировки, ни записи, ни
   общего состояния на диске (`__pycache__` кладёт сам CPython — однажды на
   версию исходника, общим состоянием процессов он не является). Клиент
   поднимает сервер по нескольку раз в секунду (наблюдено: pid
   283414/283417/283420 на одну запись), и каждый процесс обязан быть
   самостоятельным.

Основной интерпретатор — `.venv/bin/python` репозитория, он и стоит в записи
клиента (CLAUDE.md, «Мост MCP»). Гард ниже — запасной путь для ЧУЖОГО
интерпретатора (`/usr/bin/python3` у него зависимостей нет): он один раз
перезапускает файл под `.venv`, а если и там нечем — печатает в stderr, чем
именно, и выходит кодом 2. Молчаливый старт без `mcp` дал бы клиенту сервер,
который не отвечает, — отказ, неотличимый от отсутствия.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from typing import TypedDict

# ─────────────────────────── адреса и гард опоры ─────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF = os.path.abspath(__file__)
VENV = os.path.join(ROOT, ".venv")
VENV_PYTHON = os.path.join(VENV, "bin", "python")

# Зависимости, без которых сервер не сервер. `yaml` читает конфиг и манифест,
# `mcp` несёт транспорт: их отсутствие — отказ опоры, а не режим работы.
REQUIRED = ("mcp", "yaml")

# Лечение печатается в stderr клиенту и обязано быть исполнимым В ТОМ ЖЕ
# состоянии, в котором печатается: `uv pip install --python …` требует уже
# существующего интерпретатора, а печатается сообщение в том числе тогда, когда
# `.venv` нет вовсе. Поэтому создание venv стоит первым шагом той же строки:
# на существующем каталоге `python3 -m venv` идемпотентен.
INSTALL_HINT = (f"лечение: python3 -m venv {VENV} && "
                f"{os.path.join(VENV, 'bin', 'pip')} install -r "
                f"{os.path.join(ROOT, 'requirements.txt')}")

# Метка уже перезапущенного процесса. Гард обязан быть ограничен ЧИСЛОМ
# перезапусков, а не самоотчётом ребёнка: `sys.prefix` ребёнка равен `.venv`
# только при исправном `pyvenv.cfg`, и на venv без него (скопирован, шим,
# задан PYTHONHOME) условие «перезапускать» осталось бы истинным вечно —
# клиент получил бы молча крутящийся процесс вместо ответа и вместо отказа.
REEXEC_MARK = "ALTREGO_MCP_REEXEC"


def _inside_venv() -> bool:
    """Стоит ли текущий процесс на `.venv` репозитория.

    Сравнивается `sys.prefix`, а не путь к бинарнику: `.venv/bin/python` —
    симлинк на `/usr/bin/python3`, и сравнение по `realpath` считало бы venv
    системным интерпретатором. Перезапуск после этого зациклился бы.
    """
    return os.path.realpath(sys.prefix) == os.path.realpath(VENV)


def _missing_requirements() -> list[str]:
    out = []
    for name in REQUIRED:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):       # noqa: PERF203 — отказ опоры
            found = False
        if not found:
            out.append(name)
    return out


def _reexec_or_refuse(missing: list[str]) -> None:
    """Запасной путь чужого интерпретатора: ОДИН перезапуск под `.venv` либо отказ.

    Перезапуск делается только когда файл — точка входа: импорт из тестов не
    вправе подменять интерпретатор своего процесса. `-u` возвращается явно:
    stdio-сервер обязан быть небуферизованным, а флаги интерпретатора в
    `sys.argv` не приходят.

    Число перезапусков ограничено меткой в окружении ребёнка, а не сравнением
    `sys.prefix`: сравнение — самоотчёт, и на `.venv` без исправного
    `pyvenv.cfg` оно вечно говорит «ещё не перезапускались». Вечный цикл
    `execv` есть отсутствие ответа, а не отличимый отказ (§11, «Исполнимость
    shell-блока», (3)): клиент ждал бы сервер, который занят собственным
    перезапуском. Метка делает второй заход невозможным по построению.
    """
    entry = __name__ == "__main__"
    restarted = bool(os.environ.get(REEXEC_MARK))
    if entry and not restarted and os.path.isfile(VENV_PYTHON) and not _inside_venv():
        os.execve(VENV_PYTHON, [VENV_PYTHON, "-u", SELF, *sys.argv[1:]],
                  {**os.environ, REEXEC_MARK: "1"})
    where = (f"после перезапуска под {VENV_PYTHON}" if restarted
             else f"под {sys.executable} (sys.prefix {sys.prefix})")
    message = (f"altrego mcp-мост: {where} нет "
               f"модул{'ей' if len(missing) > 1 else 'я'}: {', '.join(missing)}. "
               f"Записи сервера в клиенте назвать интерпретатором {VENV_PYTHON}; "
               f"{INSTALL_HINT}\n")
    sys.stderr.write(message)
    if entry:
        raise SystemExit(2)
    raise ImportError(message)


_missing = _missing_requirements()
if _missing:
    _reexec_or_refuse(_missing)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import run                                                       # noqa: E402
from mcp.server import MCPServer                                 # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError            # noqa: E402

SERVER_NAME = "altrego-linter"
# Метка черновика в отказах чекеров: файла у него нет, а `run.run_checker`
# зовёт `repo_rel` на любом пути. Относительная метка стала бы там путём
# ОТ CWD КЛИЕНТА (`/mnt/c/Windows/system32/<черновик>` — измерено), то есть
# свидетельство отказа называло бы каталог клиентской машины вместо предмета.
# Метка держится внутри корня репозитория, и `repo_rel` сворачивает её обратно
# в голое имя из любого каталога запуска.
DRAFT = os.path.join(ROOT, "<черновик>")

mcp = MCPServer(SERVER_NAME)


# ─────────────────────── формы выдачи = схемы инструментов ───────────────────
#
# Аннотация возврата и есть контракт: по ней SDK строит output_schema, которую
# клиент видит в tools/list, и заполняет structured_content рядом с текстом.
# Голый `dict` схемы не даёт — инструмент отдавал бы текст, о форме которого
# ничего не объявлено, и «поле passed» существовало бы только на словах.
# TypedDict выбран вместо модели: в рантайме это обычный словарь, и переходник
# остаётся переходником — собирать объекты ради формы не приходится.

class FindingRow(TypedDict):
    """Находка чекера: адрес внутри черновика и текст вердикта."""
    checker: str
    line: int
    severity: str
    message: str


class NotMeasuredRow(TypedDict):
    """Чекер, по которому предмет не измерен: гейт, калибровка либо отказ."""
    checker: str
    reason: str


class InfraRow(TypedDict):
    """Отказ опоры прогона: отказала механика, а не предмет под чекером."""
    check: str
    status: str
    message: str


class TurnVerdict(TypedDict):
    """Вердикт по черновику хода: и находки, и всё, что осталось неизмеренным."""
    passed: bool
    verdict: str
    kind: str
    findings: list[FindingRow]
    not_measured: list[NotMeasuredRow]
    infra: list[InfraRow]
    calibration_reds: list[str]
    checkers: list[str]
    checkers_skipped: list[str]
    ignores_applied: int


class RuleRow(TypedDict):
    """Пункт канона по реестру полосы."""
    rule_id: str
    file: str
    section: str | None
    heading: str
    content_hash: str
    classes: list[str]


class RuleList(TypedDict):
    """Реестр правил как данные: значения реестра, без пересчёта по вольту."""
    registry: str
    computed_at: str | None
    computed_from: str | None
    count: int
    rules: list[RuleRow]
    note: str


class QueueItem(TypedDict):
    """Пункт очереди: номер владельца, признак закрытия, текст пункта."""
    position: int
    closed: bool
    text: str


class QueueHead(TypedDict):
    """Очередь контура: заголовок раздела, голова и весь список."""
    source: str
    heading: str
    as_of: str | None
    head: QueueItem | None
    items: list[QueueItem]

# ─────────────────────────────── общие двери ─────────────────────────────────

def _config() -> dict:
    """Конфиг прогона. Читается на каждый вызов: состояния между вызовами нет."""
    return run.load_config()


def _paths(config: dict) -> dict:
    return config.get("paths") or {}


def _required(config: dict, section: str, key: str) -> str:
    """Данная конфига, без умолчания в коде.

    Тот же довод, что у `linter/checkers/turn_end.py::_required`: «ключа нет»
    обязано быть отличимо от «форма не встретилась». Умолчание в коде дало бы
    инструмент, который молча читает не тот файл (§11, R-VACUUM-007).
    """
    block = config.get(section)
    value = (block or {}).get(key) if isinstance(block, dict) else None
    if not value:
        raise ToolError(
            f"config_missing_key: в config.yaml нет `{section}.{key}` — "
            f"инструмент не адресован, и умолчания в коде нет намеренно: "
            f"«ключа нет» обязано быть отличимо от «значение не встретилось»")
    return value


# ───────────────────────────── check_turn ────────────────────────────────────

def _failure_row(failure) -> dict:
    """Строка отказа контролёра для раздела infra: класс, статус, свидетельство.

    Текст берётся у самого `CheckerFailure`, чтобы формулировка отказа была та
    же, что в отчёте прогона: владелец читает одно и то же в терминале и здесь.
    """
    return {"check": failure.checker, "status": failure.status,
            "message": failure.line().split(": ", 1)[1]}


def check_turn(text: str, kind: str = "handoff") -> TurnVerdict:
    """Прогнать все чекеры вида по черновику хода ДО его выдачи владельцу.

    text — сам черновик (markdown-текст хода целиком).
    kind — вид артефакта: handoff (умолчание) либо spec; чекеры отбираются полем
    kinds манифеста, ровно как в `run.py --kind`.

    Возвращает вердикт прогона по этому тексту: passed, findings, а также всё,
    что НЕ измерено, — погашенные гейтом чекеры, дисквалифицированные
    калибровкой и отказавшие. Ноль находок при непустом not_measured/infra
    зелёным не считается.
    """
    if kind not in run.KINDS:
        raise ToolError(f"kind {kind!r} вне {', '.join(run.KINDS)}: "
                        f"вид артефакта отбирает чекеры, и неизвестный вид "
                        f"дал бы ноль чекеров при нулевом коде выхода")
    if not isinstance(text, str):
        raise ToolError("text: ожидается строка — текст черновика хода целиком")

    config = _config()
    paths = _paths(config)
    manifest = run.load_yaml(run.rel(paths.get("manifest", "linter/manifest.yaml"))) or {}
    checkers, skipped, import_failed = run.load_checkers(manifest, kind)

    infra: list[dict] = []
    for failed in import_failed:
        infra.append({"check": failed["name"], "status": run.CHECKER_IMPORT_ERROR,
                      "message": f"{failed['name']} ({failed['module']}): "
                                 f"{failed['exc_type']}: {failed['message']} — "
                                 f"модуль чекера не импортирован"})

    limit, limit_problem = run.checker_limit(config)
    if limit_problem is not None:
        infra.append({"check": "limits", "status": run.CONFIG_INVALID_LIMIT,
                      "message": limit_problem})
        limit = float("inf")

    if not checkers:
        infra.append({"check": kind, "status": run.NO_CHECKERS_FOR_KIND,
                      "message": f"вид «{kind}»: ни один чекер манифеста этот вид "
                                 f"не объявляет — ноль находок был бы зелёным "
                                 f"на неизмеренном"})

    # Калибровка идёт до цели и на каждом вызове — как в `--fast`: чекер, не
    # показавший, что умеет краснеть и не кричит зря, на этом вызове не голосует.
    calibration = run.calibrate(checkers, run.rel(paths.get("fixtures", "linter/fixtures")),
                                limit)
    infra.extend(_failure_row(f) for f in calibration["failures"])

    found, applied, gated, failures = run.run_text(
        checkers, text, DRAFT, calibration["disqualified"], limit)
    infra.extend(_failure_row(f) for f in failures)

    findings = [{"checker": f.checker, "line": f.line, "severity": f.severity,
                 "message": f.message}
                for _path, f in sorted(found, key=lambda x: (x[1].line, x[1].checker))]
    not_measured = [{"checker": name, "reason": reason}
                    for name, reason in sorted(gated.items())]

    failing = [f for f in findings if f["severity"] in run.FAILING]
    passed = not (failing or infra or calibration["reds"] or not_measured)
    return {
        "passed": passed,
        "verdict": "ЗЕЛЁНЫЙ" if passed else "КРАСНЫЙ",
        "kind": kind,
        "findings": findings,
        "not_measured": not_measured,
        "infra": infra,
        "calibration_reds": list(calibration["reds"]),
        "checkers": [c["name"] for c in checkers],
        "checkers_skipped": [c["name"] for c in skipped],
        "ignores_applied": applied,
    }


# ───────────────────────────── list_rules ────────────────────────────────────

def list_rules() -> RuleList:
    """Пункты канона, на которые опираются сценарии полосы (rules/registry.yaml).

    Хэши отдаются те, что лежат в реестре, и не пересчитываются: пересчёт идёт
    по вольту, а вольт отсюда только читается прогоном `--full` владельца
    (CLAUDE.md, «в вольт не писать»). Инструмент вольта не касается вовсе.
    """
    config = _config()
    path = run.rel(_paths(config).get("registry", "rules/registry.yaml"))
    registry = run.load_yaml(path) or {}
    rules = []
    for rule in registry.get("rules") or []:
        source = rule.get("source") or {}
        rules.append({"rule_id": rule.get("rule_id"),
                      "file": source.get("file"),
                      "section": source.get("section"),
                      "heading": source.get("heading"),
                      "content_hash": rule.get("content_hash"),
                      "classes": list(rule.get("classes") or [])})
    return {"registry": path,
            "computed_at": registry.get("computed_at"),
            "computed_from": registry.get("computed_from"),
            "count": len(rules),
            "rules": rules,
            "note": "content_hash — значение реестра; пересчёт по вольту делает "
                    "`run.py --full` у владельца, инструмент вольт не читает"}


# ─────────────────────────────── queue ───────────────────────────────────────

ITEM = re.compile(r"^(\d+)\.\s+(.*)$")
MD_HEADING = re.compile(r"^#{1,6}\s")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _compile(pattern: str, key: str) -> re.Pattern:
    """Регэксп данной конфига — с типизированным отказом на битой форме.

    Битый шаблон иначе выходит наружу как `re.error` и доезжает до клиента
    строкой «Error executing tool queue»: отказ есть, а чем именно он вызван и
    где лечить — не сказано. Данная живёт в config.yaml, и отказ обязан назвать
    ключ.
    """
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ToolError(
            f"config_invalid_pattern: `queue.{key}` = {pattern!r} — не регэксп "
            f"({exc}); лечение в config.yaml") from exc


def parse_queue(text: str, heading_pattern: str, closed_pattern: str) -> dict:
    """Разбор раздела очереди: абзац-зачин плюс нумерованный список под ним.

    Форма, на которой разбор держится (вольт, `02-synthesis/
    target-state-and-roadmap-r2.md`): строка-зачин, пустая строка, список
    `N. …` по пункту на строку.

    Три границы, и каждая — по инварианту, а не по удаче:

    * **Зачин** может занимать несколько строк: абзац идёт до первой пустой.
    * **Список обязан начинаться сразу** за абзацем-зачином. Проза между ними —
      типизированный отказ, а не повод искать список дальше по файлу: пропустив
      её, разбор дошёл бы до ЧУЖОГО нумерованного списка и выдал бы его за
      очередь — молча и с `isError=false`.
    * **Пустая строка списка не обрывает**, если следующая непустая — пункт
      либо строка с отступом (подпункт разрежённого списка). Обрыв на
      подпункте срезал бы хвост очереди молча, и голова могла бы стать `None`
      при живых пунктах ниже.

    Позиция берётся из самого номера, а не из порядка: владелец нумерует
    очередь сам, и перенумерация не должна молча сдвигать голову.
    """
    head_re = _compile(heading_pattern, "heading_pattern")
    closed_re = _compile(closed_pattern, "closed_pattern")
    lines = text.split("\n")

    start = next((i for i, line in enumerate(lines) if head_re.search(line)), None)
    if start is None:
        raise ToolError(
            f"queue_heading_not_found: в файле нет строки по признаку "
            f"{heading_pattern!r} — раздел очереди не найден, и пустой список "
            f"был бы неотличим от пустой очереди")

    # Абзац-зачин целиком: он вправе быть перенесённым на несколько строк.
    head_lines = [lines[start].strip()]
    i = start + 1
    while i < len(lines) and lines[i].strip() and not ITEM.match(lines[i]) \
            and not MD_HEADING.match(lines[i]):
        head_lines.append(lines[i].strip())
        i += 1

    while i < len(lines) and not lines[i].strip():
        i += 1

    if i >= len(lines) or not ITEM.match(lines[i]):
        seen = lines[i].strip()[:80] if i < len(lines) else "конец файла"
        raise ToolError(
            f"queue_items_not_after_heading: сразу за абзацем очереди нет "
            f"пункта `N. …` (следующее непустое: {seen!r}) — разбор не ищет "
            f"список дальше по файлу намеренно: он нашёл бы чужой "
            f"нумерованный список и выдал его за очередь")

    items: list[dict] = []
    while i < len(lines):
        raw = lines[i]
        match = ITEM.match(raw)
        if match:
            items.append({"position": int(match.group(1)), "lines": [match.group(2)]})
            i += 1
            continue
        if MD_HEADING.match(raw):
            break
        if not raw.strip():
            following = i + 1
            while following < len(lines) and not lines[following].strip():
                following += 1
            if following >= len(lines):
                break
            nxt = lines[following]
            # Пункт — новый элемент; строка с отступом — подпункт разрежённого
            # списка, то есть тот же список. Всё прочее — текст за списком.
            if ITEM.match(nxt) or nxt[:1].isspace():
                i = following
                continue
            break
        items[-1]["lines"].append(raw.strip())
        i += 1

    out = []
    for item in items:
        body = " ".join(item["lines"]).strip()
        out.append({"position": item["position"],
                    "closed": bool(closed_re.search(body)),
                    "text": body})
    heading = " ".join(head_lines)
    as_of = DATE.search(heading)
    head = next((x for x in out if not x["closed"]), None)
    return {"heading": heading,
            "as_of": as_of.group(0) if as_of else None,
            "head": head,
            "items": out}


def queue() -> QueueHead:
    """Голова единой очереди контура — из рабочей копии вольта, только чтением.

    Файл и признаки разбора — данные `config.yaml` (блок `queue`), не код:
    форма раздела живёт в вольте и правится владельцем, а порог, зашитый в
    модуль, разошёлся бы с ней молча.

    Путь вольта приходит только из окружения. Клиент Claude Desktop окружения
    входа WSL не наследует, поэтому незаданная переменная — названный отказ с
    лечением, а не умолчание на каталог владельца.
    """
    config = _config()
    master = run.env_path(run.ENV_MASTER)
    if not master:
        raise ToolError(
            f"vault_env_unset: переменная окружения {run.ENV_MASTER} не задана — "
            f"рабочая копия вольта не адресована, а умолчания на каталог "
            f"владельца в репозитории нет. Клиент не наследует окружение WSL: "
            f"задать {run.ENV_MASTER} в блоке `env` записи сервера в "
            f"конфигурации клиента и перезапустить его")

    rel_path = _required(config, "queue", "file")
    heading_pattern = _required(config, "queue", "heading_pattern")
    closed_pattern = _required(config, "queue", "closed_pattern")

    path = os.path.join(os.path.expanduser(master), rel_path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(
            f"queue_unreadable: {path} не прочитан ({type(exc).__name__}: {exc}) — "
            f"очередь не измерена, а не пуста") from exc

    parsed = parse_queue(text, heading_pattern, closed_pattern)
    parsed["source"] = path
    return parsed


# ─────────────────────────── регистрация и запуск ────────────────────────────

# Функции регистрируются после определения, а не декоратором сверху: так они
# остаются обычными функциями модуля, и харнесс зовёт ровно то, что зовёт
# клиент, без транспорта посередине.
mcp.tool()(check_turn)
mcp.tool()(list_rules)
mcp.tool()(queue)


if __name__ == "__main__":
    # Без аргументов — stdio: сервер блокируется и говорит протоколом в stdout.
    # В stdout не пишет больше ничего и никто: посторонняя строка там — сломанный
    # кадр протокола, а не сообщение.
    mcp.run()
