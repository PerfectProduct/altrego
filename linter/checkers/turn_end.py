"""S-05 / К4: конец хода не называет, какое слово владельца требуется.

Опора: контракт §11, «Конец хода — точка, где нужно слово владельца».
Структурная половина сценария: наличие строки и непустота требования после
двоеточия. Существо (нужно ли здесь вообще слово владельца) — manual.

Расширение 2026-09-07: контракт §11, «Слот трёх полей перед вопросом
владельцу»; реестр правок канона §B, счёт пары «Конец хода» × К4 — №4, №5, №7;
семь рецидивов К4. Подабзац добавлен по подписи владельца и сам называет
оракул: «*Проверка:* чекер `turn_end` — артефакт с 2+ вариантами без строки
слота, с «есть» без «потому что» или с анонсом в строке «Конец хода» краснеет;
истинность полей — ручная». Отсюда ровно три новые ветки, и ни одной больше:
четвёртый «ловимый отказ» подабзаца (вопрос владельцу при трёх «нет») в
*Проверку* не вошёл и остаётся за владельцем.

Огороженные блоки снимаются до всех проверок — это «Допустимое попадание»
подабзаца: «варианты внутри блока владельца, а не вопрос ему». Снимаются
**гашением строк на месте**, а не вырезанием: `Finding.line` — номер строки
сырого артефакта, и по этой же паре (строка, чекер) `linter/ignores.py`
сопоставляет изъятие `<!-- lint:ignore turn_end — причина -->`. Вырезание
сдвинуло бы оба молча (замерено: в red/shell_mech.md 53 строки, 40 из них
внутри оград, и находка ветки 1 уехала бы с 53-й строки на 13-ю). Признак
ограды берётся готовым домом
`common.in_block_lines` — шестая копия признака разошлась бы с пятью
имеющимися молча (тот же довод, что у дома признака промпта в prompts.py).

Наблюдения, названные при заведении веток и в этот пакет не взятые:

* Исключение шире канона. Канон исключает **блок владельца**, чекер — любую
  ограду. Развилка, вынесенная владельцу внутри промпта исполнителю или внутри
  цитаты чужого хода, станет невидимой. Класс пропуска назван; сужение до
  «блока владельца» (признак у `prompts.owner_addressed` уже есть) — кандидат,
  а не этот пакет.
* Незакрытая ограда заглатывает остаток артефакта до EOF (`parse_blocks`,
  `closed=False`), и тогда гасится хвост вместе со строкой «Конец хода».
  В корпусе таких оград 0 из 32; отдельного гарда нет.
* `slot_fields` ищутся в любом месте текста, тогда как канон требует строку
  слота **перед вопросом**. Артефакт, цитирующий сам канон, получает слот
  даром. Сиблинг `live_channel_slot` держит ту же задачу строже — парой
  `slot_pattern` + `slot_window`; здесь это сознательное послабление
  структурной половины, названное владельцем в задании пакета.
* `announce_markers` — перечислимая половина инварианта, а не сам инвариант.
  Инвариант: хвост называет **собственное следующее действие хода** вместо
  слова, требуемого от владельца («ход, заканчивающийся анонсом собственного
  следующего действия («следующим шагом сделаю X»), возвращается»). Список не
  видит «Пишу отчёт», «Прогоняю линтер» — тот же отказ. Держит список якорь
  начала хвоста, а не частота: слово «дальше» стоит **внутри** 3 из 24
  настоящих закрывающих строк владельца и ни одна из 24 с маркера не
  начинается. Второй проход по инварианту (адресация владельцу / ведущий
  глагол 1 л. ед. ч.) — кандидат §D, не этот пакет.

Ветка «есть» без основания меряет только первую половину уточнения §B №4:
канон требует у поля «есть» и «потому что», и двух названных разных целевых
состояний, но *Проверка* поручает чекеру лишь первую («истинность полей —
ручная»). Вторая половина здесь не меряется — молчание чекера о ней не значит
«измерено».

Чистая функция: без сети, без LLM, без файловых эффектов.
"""

from __future__ import annotations

import re

from ..common import (RED, Finding, in_block_lines, significant_chars,
                      split_lines)

NAME = "turn_end"

DEFAULT_MARKER = r"^\s*(?:[*_#>\-\s]*)\**\s*Конец хода\**\s*(?::|—|-)?\s*(.*)$"


class ConfigDefect(Exception):
    """Данная ветки не задана в манифесте.

    Своя дверь, а не умолчание в коде: список форм и порог живут в
    `linter/manifest.yaml` как данные, и «ключа нет» обязано быть отличимо от
    «форма не встретилась». Умолчание в коде дало бы ветку, которая молчит
    нулём находок при снятой данной, — пустая выдача при нулевом коде выхода,
    та самая, что полоса и ловит (§11, R-VACUUM-007). Отказ чекера есть отказ
    хода: run.py обращает его в красный `checker_error`.
    """


def _required(config: dict, key: str):
    value = config.get(key)
    if not value:
        raise ConfigDefect(
            f"config.{key} не задан либо пуст: ветка молчала бы нулём находок, "
            f"и «данной нет» стало бы неотличимо от «форма не встретилась» "
            f"(§11, R-VACUUM-007). Список форм — данные манифеста, не кода")
    return value


def _compile(patterns) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _visible_lines(text: str, config: dict) -> list[str]:
    """Строки артефакта, где огороженные блоки погашены пустыми строками.

    Гашение, а не вырезание: номера строк остаются номерами сырого артефакта.
    """
    blocked = in_block_lines(text, config)
    return ["" if (i + 1) in blocked else raw
            for i, raw in enumerate(split_lines(text))]


def _next_significant(lines: list[str], idx: int) -> str:
    """Ближайшая непустая строка после `idx` (0-индексно); иначе пустая."""
    for raw in lines[idx + 1:]:
        if raw.strip():
            return raw
    return ""


# ─────────────────────────── (а) варианты без слота ──────────────────────────

def _variant_identities(lines: list[str], config: dict) -> list[tuple[int, str]]:
    """Пары (строка, тождество варианта) в порядке появления.

    Тождество — группа 1 регэкспа, если она есть, иначе всё совпадение;
    приводится к нижнему регистру. Считаются РАЗЛИЧНЫЕ тождества, а не
    совпадения, строки или сработавшие регэкспы: инвариант подабзаца говорит о
    двух **названных вариантах**. Счёт по совпадениям краснел бы на повторном
    упоминании одного варианта; счёт по строкам терял бы однострочную развилку
    («основной вариант и близкая альтернатива»); счёт по регэкспам терял бы
    собственную подпись владельца («1=» и «2=» — один и тот же регэксп).

    `variant_markers_paired` называет вариант лишь относительно уже названного
    первого и в одиночку не считается: «альтернатива» сама по себе называет
    отношение сравнения, а не вынесенный владельцу вариант (замерено на вольте:
    262 вхождения в 131 файле, самостоятельным маркером она красит 51 файл из
    56 — поверхность вдесятеро больше предмета).
    """
    markers = _compile(_required(config, "variant_markers"))
    paired = _compile(_required(config, "variant_markers_paired"))

    def scan(patterns) -> list[tuple[int, str]]:
        out = []
        for idx, raw in enumerate(lines):
            for pattern in patterns:
                for m in pattern.finditer(raw):
                    ident = (m.group(1) if m.groups() else m.group(0))
                    out.append((idx + 1, ident.strip().lower()))
        return out

    named = scan(markers)
    if named:
        named += scan(paired)

    seen: set[str] = set()
    unique: list[tuple[int, str]] = []
    for ln, ident in sorted(named):
        if ident not in seen:
            seen.add(ident)
            unique.append((ln, ident))
    return unique


def _missing_slot_fields(text: str, config: dict) -> list[str]:
    fields = _required(config, "slot_fields")
    return [f for f in fields
            if not re.search(re.escape(f), text, re.IGNORECASE)]


def _check_variants(lines: list[str], config: dict) -> list[Finding]:
    minimum = int(_required(config, "variant_min"))
    variants = _variant_identities(lines, config)
    if len(variants) < minimum:
        return []
    missing = _missing_slot_fields("\n".join(lines), config)
    if not missing:
        return []
    named = ", ".join(f"«{ident}»" for _ln, ident in variants)
    absent = ", ".join(f"«{f}»" for f in missing)
    return [Finding(
        variants[0][0], NAME, RED,
        f"владельцу вынесено вариантов: {len(variants)} ({named}) — при пороге "
        f"{minimum}, а слот трёх полей перед вопросом неполон: нет {absent}. "
        f"Развилка без слота не даёт владельцу увидеть, затронут ли его "
        f"периметр, обратим ли выбор и есть ли долгосрочная разница, — и "
        f"раунд уходит на «да» там, где решение было за оркестратором")]


# ────────────────────── (б) «есть» без основания ─────────────────────────────

def _check_difference(lines: list[str], config: dict) -> list[Finding]:
    """«Долгосрочная разница: есть» без «потому что» рядом.

    Значение поля берётся по имени поля, а не поиском слова «есть» по строке:
    три поля слота стоят одной строкой через «·», и «есть» внутри соседнего
    поля или свободной прозы полем не является. Утвердительность — значение
    **начинается** с «есть».

    Основание сужено тем же образом (правка по слову владельца 2026-09-08):
    «потому что» ищется в значении самого поля — от «есть» до ближайшего
    разделителя «·» либо конца строки — и в следующей непустой строке, но не по
    всей строке. Инвариант подабзаца говорит об основании ПОЛЯ, а не строки:
    основание соседнего поля покрывало бы непокрытое «есть» на канонной
    однострочной форме слота. Замерено на настоящем документе: канон-реестр
    вольта, строка 138, где единственное «потому что» строки — отрицающее
    упоминание оборота («заполненный без «потому что», не работает»), — при
    поиске по строке оно снимало находку с «Долгосрочная разница: есть»,
    стоящего там же.
    """
    field = re.compile(_required(config, "difference_field_pattern"), re.IGNORECASE)
    yes = re.compile(_required(config, "difference_yes_pattern"), re.IGNORECASE)
    because = re.compile(_required(config, "because_pattern"), re.IGNORECASE)

    findings: list[Finding] = []
    for idx, raw in enumerate(lines):
        for m in field.finditer(raw):
            value = m.group(1) or ""
            if not yes.match(value):
                continue
            if because.search(value) or because.search(_next_significant(lines, idx)):
                continue
            findings.append(Finding(
                idx + 1, NAME, RED,
                "поле «Долгосрочная разница» отвечает «есть», но основания нет: "
                "ни в значении самого поля, ни в следующей непустой строке нет "
                "«потому что». Без основания поле читается как «нет» (§11, слот "
                "трёх полей), то есть развилка не была развилкой владельца"))
    return findings


# ─────────────────── (в) конец хода на анонсе ────────────────────────────────

def _check_announce(hits: list[tuple[int, str]], config: dict) -> list[Finding]:
    """Хвост «Конца хода» начинается с анонса собственного действия хода.

    Предмет — сама закрывающая реплика, поэтому берётся сырой хвост строки, а
    не продлённый: продление в ветке длины есть прибор порога
    `min_significant_chars`, и якорь «начинается с» на нём стал бы зависеть от
    чужого порога.

    Ведущая разметка срезается до сравнения, и это несущее, а не косметика:
    `marker_pattern` отдаёт в хвост закрывающие `**` жирного, а в жирной форме
    стоят все 29 строк «Конец хода» корпуса — без срезки ветка промахнулась бы
    по всем.
    """
    strip = re.compile(_required(config, "announce_lead_strip"))
    markers = _compile(_required(config, "announce_markers"))

    findings: list[Finding] = []
    for ln, tail in hits:
        head = strip.sub("", tail)
        for pattern in markers:
            m = pattern.match(head)
            if not m:
                continue
            findings.append(Finding(
                ln, NAME, RED,
                f"конец хода на анонсе собственного действия: хвост начинается "
                f"с «{m.group(0)}» — ход заканчивается там, где следующий шаг "
                f"доступен самому оркестратору. Назвать, какое слово владельца "
                f"требуется, либо продолжить ход до этой точки"))
            break
    return findings


# ──────────────────────────────── чекер ──────────────────────────────────────

def check(text: str, config: dict) -> list[Finding]:
    config = config or {}
    marker = re.compile(config.get("marker_pattern", DEFAULT_MARKER),
                        re.IGNORECASE | re.MULTILINE)
    min_sig = int(config.get("min_significant_chars", 10))
    require_presence = bool(config.get("require_presence", True))

    lines = _visible_lines(text, config)
    hits = []
    for idx, raw in enumerate(lines):
        m = marker.match(raw)
        if m:
            hits.append((idx + 1, m.group(1).strip()))

    findings: list[Finding] = []
    findings.extend(_check_variants(lines, config))
    findings.extend(_check_difference(lines, config))
    findings.extend(_check_announce(hits, config))

    if not hits:
        if not require_presence:
            return findings
        last = max(1, len([l for l in lines if l.strip()]) and len(lines))
        findings.append(Finding(
            last, NAME, RED,
            "в handoff-артефакте нет строки «Конец хода»: точка, где нужно слово "
            "владельца, не названа — граница хода не проверяема"))
        return sorted(findings, key=lambda f: f.line)

    for ln, tail in hits:
        # продолжение на следующей строке засчитывается, если строка не пуста
        if significant_chars(tail) < min_sig and ln < len(lines):
            tail = (tail + " " + lines[ln].strip()).strip()
        if significant_chars(tail) < min_sig:
            findings.append(Finding(
                ln, NAME, RED,
                f"«Конец хода» не называет требуемое слово владельца: после "
                f"двоеточия {significant_chars(tail)} значащих символов "
                f"(порог {min_sig})"))
    return sorted(findings, key=lambda f: f.line)
