"""S-14 / К7: новый детектор введён без названной наблюдённой диспозиции.

Опора: контракт §11, «Новый детектор принимается по наблюдённой диспозиции»
(добавлено 2026-08-28, разбор milestone UIP; реестр: R-DISPOSITION-012). Пункт:
отчёт, вводящий новый гард, принимается только если по каждому новому детектору
названы **мутация**, её **предсказанная** и **наблюдённая** диспозиция;
расхождение фиксируется как исправление утверждения — правится текст плана и
комментарий ноги, а не нога под предсказание.

Повод — самый частый в §A реестра правок канона (2026-08-28, К7): за milestone
UIP четыре детектора покраснели на самих себе и три предсказания разошлись с
измерением; всё найдено вооружающими дугами, ни одно — чтением. Отсюда и место
этого чекера первым в очереди добора.

Что меряется — документ целиком, а не блок. Триггер у обеих форм общий: ход,
вводящий новый детектор (`intro_patterns`: «новый чекер», «новый гард», «завожу
детектор», «вводит новую ногу»). «Допустимые попадания» пункта — пакеты, не
вводящие новых детекторов, — здесь есть отсутствие триггера: ход без введения
детектора чекер не трогает ни одной формой.

Форма 1 (без префикса): ход обязан нести три слота (`slot_patterns`) — мутация,
предсказанная диспозиция, наблюдённая диспозиция. Нет хотя бы одного — красный
на строке введения, с перечнем недостающих: приёмка по одному предсказанию и
есть тот отказ, ради которого пункт заведён.

Форма 2, `disposition_unit_unnamed` (пакет B-P2b-P3a, 2026-09-10): слот
предсказания есть, но предсказание названо ЧИСЛОМ без единицы измерения.
Повод — реестр правок канона §A, 2026-08-31, К2: «вилки заданы на один ход,
прогон шёл по стенограмме двадцати; расхождение ×3–5 выглядело дефектом
детекторов, а было дефектом предсказания». Форма судит не наличие слота, а его
пригодность, и потому НЕ обусловлена полнотой остальных: плохое предсказание
есть отказ независимо от того, названа ли рядом мутация. Обусловленность
сломала бы и механику — слоты ищутся по всему документу, и красный случай,
называющий все три, стёр бы находку формы 1 на той же фикстуре.

Что форма 2 намеренно не ловит, и каждый пункт — признак, а не частота:
  * предсказание без цифр. Русское числительное словом обязательно управляет
    существительным и тем самым называет свою совокупность («красный на четырёх
    местах публичной политики»); цифра не управляет ничем. Цена: предсказание,
    написанное словами целиком, не судится;
  * число, которое есть адрес или идентификатор, — дата, §11, S-14, v0,
    B-P2b-P2, `файл.md:8`, ×3–5. Отсечено формой просмотров, а не стоп-списком;
  * номер пункта нумерованного списка: «2.» — номер шага, а не счёт находок;
  * слот, отсылающий к предсказанию («Записать предсказанные диспозиции ниже»),
    а не несущий его: указатель гасит совпадение линейно-локально, как irrealis
    у ног 4/5 `claim_provenance`; настоящая таблица судится сама;
  * всё, что лежит за ближайшим markdown-заголовком: область предсказания
    кончается на границе раздела, и «код выхода 1» смоук-строки соседнего
    раздела числом предсказания не является;
  * наблюдённая диспозиция. Пункт К2 и CLAUDE.md привязывают требование к
    предсказанию; наблюдение есть измерение и называет свой артефакт само.

Списки форм — данные манифеста: расширяются без правки модуля. У ключей формы 2
умолчаний в коде НЕТ намеренно — четыре списка полосы уже мертвы механизмом
«манифест побеждает умолчание» (`DEFAULT_INTRO` и `DEFAULT_SLOTS` ниже,
`DEFAULT_IGNORE` и `DEFAULT_COMMAND` в `claim_provenance`, `DEFAULT_GATES` в
`artifact_integrity`, до сих пор называющий переименованный `stop_provenance`).
Отсутствие ключа — исключение, из которого `run_checker` делает красный
`checker_error` и пометку «не измерено»: «ключ не задан» и «форма снята» обязаны
быть различимы, та же доктрина, что у `LIMIT_KEY` в `run.py`.

Чистая функция: ни сети, ни LLM, ни файловых эффектов.
"""

from __future__ import annotations

import re

from ..common import RED, Finding, in_block_lines, split_lines

NAME = "detector_disposition"
UNIT_FORM = "disposition_unit_unnamed"

DEFAULT_INTRO = [
    r"\bнов\w+\s+(?:чекер\w*|гард\w*|детектор\w*|ног[ауи]\b)",
    r"\b(?:завожу|завед\w+|вношу|ввожу|вводит\w*)\s+(?:\w+\s+){0,2}?"
    r"(?:чекер|гард|детектор)\w*",
    r"\b(?:чекер|гард|детектор)\w*\s+(?:завед\w+|введ\w+|добавл\w+)",
]
DEFAULT_SLOTS = [
    ("мутация", r"мутаци\w*"),
    ("предсказанная диспозиция", r"предсказанн\w*\s+диспозиц\w*|"
                                 r"диспозиц\w*\s*[:—–-]?\s*предсказ\w*|предсказ\w*\s+диспозиц\w*"),
    ("наблюдённая диспозиция", r"наблюд[её]нн\w*\s+диспозиц\w*|"
                               r"диспозиц\w*\s*[:—–-]?\s*наблюд\w*|наблюд\w*\s+диспозиц\w*"),
]


def _required(config: dict, key: str):
    """Ключ формы 2 обязателен: умолчания в коде нет намеренно.

    Отсутствие ключа — не «форма молчит», а отказ опоры: исключение уходит в
    `run_checker`, тот делает из него красный `checker_error`, и чекер стоит в
    «Не измерено». Молчаливое умолчание дало бы ноль находок при нулевом коде
    выхода — то самое, что полоса и ловит.
    """
    value = config.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(
            f"{NAME}: ключ config.{key} формы {UNIT_FORM} не задан в манифесте — "
            f"умолчания в коде нет намеренно: «ключ не задан» неотличимо от "
            f"«форма снята»")
    return value


def _unit_form(lines: list[str], blocked: set, slots, config: dict) -> list[Finding]:
    """Предсказанная диспозиция, названная числом без единицы измерения.

    Слот адресуется ИМЕНЕМ из `slot_patterns`, а не второй копией шаблона: копия
    разошлась бы с оригиналом молча. Имя, которого в списке нет, — отказ чекера,
    а не тихий ноль: форма мерила бы пустоту, и её молчание было бы неотличимо
    от зелёного.
    """
    slot_name = _required(config, "unit_slot_name")
    pattern = next((p for name, p in slots if name == slot_name), None)
    if pattern is None:
        raise ValueError(
            f"{NAME}: unit_slot_name {slot_name!r} не найден среди slot_patterns "
            f"({', '.join(name for name, _ in slots)}) — форма {UNIT_FORM} мерила "
            f"бы пустоту, и её молчание было бы неотличимо от зелёного")

    slot = re.compile(pattern, re.IGNORECASE)
    quantity = re.compile(_required(config, "unit_quantity_pattern"))
    marker = re.compile(_required(config, "unit_list_marker_pattern"))
    section_end = re.compile(_required(config, "unit_section_end_pattern"))
    max_lines = int(_required(config, "unit_max_lines"))
    pointers = [re.compile(p, re.IGNORECASE)
                for p in _required(config, "unit_pointer_patterns")]
    units = [re.compile(p, re.IGNORECASE)
             for p in _required(config, "unit_patterns")]

    for ln, raw in enumerate(lines, start=1):
        if ln in blocked or not slot.search(raw):
            continue
        if any(p.search(raw) for p in pointers):
            continue                   # слот отсылает к предсказанию, а не несёт его
        region: list[tuple[int, str]] = []
        for j in range(ln, min(len(lines), ln + max_lines) + 1):
            if j > ln and section_end.match(lines[j - 1]):
                break                  # раздел кончился: дальше уже не предсказание
            if j in blocked:
                continue
            region.append((j, marker.sub("", lines[j - 1])))
        body = "\n".join(text for _, text in region)
        hit = next(((j, quantity.search(text)) for j, text in region
                    if quantity.search(text)), None)
        if hit is None:
            continue                   # предсказание без числа вилкой не является
        if any(u.search(body) for u in units):
            continue                   # единица названа
        qline, qty = hit
        return [Finding(
            qline, NAME, RED,
            f"[{UNIT_FORM}] предсказанная диспозиция названа числом "
            f"«{qty.group(0).strip()}» без единицы измерения (строка предсказания "
            f"{ln}): вилка без единицы с наблюдением не сверяется — вилка, "
            f"названная на один ход, против прогона по стенограмме двадцати "
            f"даёт расхождение ×3–5, и оно читается дефектом детекторов, а есть "
            f"дефект предсказания. Назвать единицу до прогона: на артефакт / "
            f"на ход / на прогон")]
    return []


def check(text: str, config: dict) -> list[Finding]:
    config = config or {}
    intros = [re.compile(p, re.IGNORECASE)
              for p in (config.get("intro_patterns") or DEFAULT_INTRO)]
    raw_slots = config.get("slot_patterns")
    slots = ([(s["name"], s["pattern"]) for s in raw_slots] if raw_slots
             else DEFAULT_SLOTS)
    compiled = [(name, re.compile(p, re.IGNORECASE)) for name, p in slots]

    lines = split_lines(text)
    blocked = in_block_lines(text, config)

    intro_hit = None
    for ln, raw in enumerate(lines, start=1):
        if ln in blocked:
            continue
        hit = next((p.search(raw) for p in intros if p.search(raw)), None)
        if hit is not None:
            intro_hit = (ln, hit)
            break                      # предмет — ход, а не каждое упоминание
    if intro_hit is None:
        return []                      # нет триггера — обе формы молчат

    # Слоты ищутся по всему ходу: диспозиции стоят в прозе отчёта, не обязательно
    # рядом со строкой введения.
    prose = "\n".join(raw for i, raw in enumerate(lines, start=1) if i not in blocked)
    findings: list[Finding] = []

    missing = [name for name, pat in compiled if not pat.search(prose)]
    if missing:
        ln, hit = intro_hit
        findings.append(Finding(
            ln, NAME, RED,
            f"ход вводит новый детектор («{hit.group(0).strip()}»), но не называет: "
            f"{', '.join(missing)} — приёмка по одному предсказанию и есть отказ, "
            f"ради которого пункт заведён: детектор, не покрасневший на своей "
            f"мутации, неотличим от детектора, у которого нет предмета"))

    findings.extend(_unit_form(lines, blocked, slots, config))
    return findings
