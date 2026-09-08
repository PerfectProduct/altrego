"""Три ветки turn_end v2, заведённые 2026-09-07.

Повод: контракт §11, подабзац «Слот трёх полей перед вопросом владельцу»
(правка канона по подписи владельца 2026-09-07); реестр правок канона §B, счёт
пары «Конец хода» × К4 — №4, №5, №7; семь рецидивов К4. Оракул назван самим
подабзацем в поле *Проверка*, и веток ровно три: развилка без слота, «есть» без
«потому что», конец хода на анонсе. Новых чекеров пакет не заводит — формы
стоят внутри turn_end.

Единица диспозиции — «на артефакт `--fast`» для фикстур и «на текст» для веток.

Три теста рецидивов ниже — не выдуманные формы, а тексты, на которых правило
ломалось: три вопроса владельцу с вариантами и без полей слота; «основной
вариант и близкая альтернатива» трижды; закрывающая строка «Записываю прогон в
вольт». Они держат ветки на предмете, а не на удобной форме.
"""

from __future__ import annotations

import os

import pytest
import yaml

import run
from linter.checkers.turn_end import ConfigDefect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "linter", "fixtures")

# Находок turn_end на собственной red-фикстуре до расширения (прогон 2026-09-08):
# фикстура дополняется, а не переписывается, и прежняя ветка обязана остаться.
BASELINE_RED = 1

# Опознание веток по несущему куску сообщения: своих меток `[форма]`, как у
# shell_mech, у turn_end нет — ветки различаются предметом, а не подвидом формы.
VARIANTS = "владельцу вынесено вариантов"
DIFFERENCE = "«Долгосрочная разница» отвечает «есть»"
ANNOUNCE = "конец хода на анонсе"
SHORT_TAIL = "не называет требуемое слово владельца"
ABSENT = "нет строки «Конец хода»"

# Закрывающая строка, не дающая сработать ветке длины: тексты ниже меряют другие
# ветки, и молчание ветки длины в них — условие, а не предмет.
CLOSING = ("**Конец хода:** нужно слово владельца — принять разбор выше "
           "либо назвать расхождение.")
FULL_SLOT = ("**Периметр владельца (риск / вкус / публичное / необратимое / "
             "конституция): нет · Обратимость: один пакет · Долгосрочная "
             "разница: нет**")


@pytest.fixture(scope="module")
def checker() -> dict:
    with open(os.path.join(ROOT, "linter", "manifest.yaml"), encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh) or {}
    active, _skipped, failed = run.load_checkers(manifest, "handoff")
    assert failed == []
    return {c["name"]: c for c in active}["turn_end"]


def check(checker: dict, text: str) -> list[str]:
    return [f.message for f in checker["module"].check(text, checker["config"])]


def hits(messages: list[str], branch: str) -> list[str]:
    return [m for m in messages if branch in m]


def fixture_findings(capsys, colour: str) -> tuple[int, list[str]]:
    path = os.path.join(FIXTURES, colour, "turn_end.md")
    code = run.main(["--fast", path, "--no-report"])
    out = capsys.readouterr().out
    listed = out.split("## Находки", 1)[1].split("## Сводка", 1)[0]
    return code, [ln for ln in listed.splitlines() if " turn_end " in ln]


# ───────────────────── (а) варианты без слота ────────────────────────────────

def test_variants_without_slot_red(checker):
    text = ("# Ход\n\n1= завожу ветку сам\n2= жду владельца\n\n" + CLOSING + "\n")
    messages = check(checker, text)
    assert len(hits(messages, VARIANTS)) == 1
    # Сообщение перечисляет именно отсутствующие поля, а не факт неполноты.
    assert "«Периметр владельца»" in messages[0]
    assert "«Обратимость»" in messages[0]
    assert "«Долгосрочная разница»" in messages[0]


def test_full_slot_green(checker):
    text = ("# Ход\n\n1= завожу ветку сам\n2= жду владельца\n\n" + FULL_SLOT
            + "\n\n" + CLOSING + "\n")
    assert check(checker, text) == []


def test_fenced_variants_green(checker):
    """Варианты внутри огороженного блока — «Допустимое попадание» подабзаца.

    Слота в тексте нет намеренно: без снятия оград ветка (а) обязана была бы
    покраснеть, и молчание здесь меряет именно снятие, а не полноту слота.
    """
    text = ("# Ход\n\nБлок владельцу для подписи:\n\n"
            "```\n1=да\n2=нет\nА) третий путь\n```\n\n" + CLOSING + "\n")
    assert check(checker, text) == []


def test_line_numbers_survive_fence_stripping(checker):
    """Ограды гасятся на месте: номер строки остаётся номером сырого артефакта."""
    text = ("# Ход\n\n```bash\nls -1\nwc -l run.py\n```\n\n"
            "1= завожу ветку сам\n2= жду владельца\n\n" + CLOSING + "\n")
    found = checker["module"].check(text, checker["config"])
    assert [f.line for f in found] == [8]          # строка «1= …» в сыром тексте
    assert text.split("\n")[7].startswith("1=")


def test_one_variant_is_not_a_fork_green(checker):
    """Порог — два НАЗВАННЫХ варианта: одна помеченная строка развилкой не является."""
    text = "# Ход\n\n1= завожу ветку сам\n\n" + CLOSING + "\n"
    assert hits(check(checker, text), VARIANTS) == []


def test_same_variant_named_twice_green(checker):
    """Считаются различные тождества: повтор одного варианта — по-прежнему один."""
    text = ("# Ход\n\nвариант А закрывает узел; вариант А же закрывает и второй.\n\n"
            + CLOSING + "\n")
    assert hits(check(checker, text), VARIANTS) == []


@pytest.mark.parametrize("second", ["основной вариант", "Основной вариант"])
def test_same_variant_named_in_two_cases_green(checker, second):
    """Тождество берётся в нижнем регистре: «Основной» и «основной» — один вариант.

    Без приведения регистра один и тот же вариант, названный с прописной и со
    строчной, дал бы два тождества и ложный красный — ровно тот класс, ради
    которого счёт и ведётся по тождествам.
    """
    text = ("# Ход\n\nОсновной вариант — правка манифеста. " + second
            + " закрывает и второй узел.\n\n" + CLOSING + "\n")
    assert hits(check(checker, text), VARIANTS) == []


def test_alternative_alone_is_not_a_variant_green(checker):
    """«альтернатива» без названного первого варианта — отношение, а не вариант."""
    text = ("# Ход\n\nБолее лёгкая альтернатива обсуждалась и отброшена; вторая "
            "альтернатива не рассматривалась.\n\n" + CLOSING + "\n")
    assert hits(check(checker, text), VARIANTS) == []


def test_invariant_word_is_not_a_variant_green(checker):
    """`\\b` слева от «вариант» отсекает «инвариант» — 30 вхождений в репозитории."""
    text = ("# Ход\n\nИнвариант А держит правило, инвариант Б — его половину.\n\n"
            + CLOSING + "\n")
    assert hits(check(checker, text), VARIANTS) == []


def test_variant_in_redaction_is_not_a_label_green(checker):
    """Метка варианта — только прописная буква: «вариант в редакции» не метка.

    Буквы взяты РАЗНЫЕ намеренно. С одной и той же строчной буквой тест прошёл
    бы и без сужения `(?-i:…)`: два совпадения дали бы одно тождество, и его
    снял бы счёт различных тождеств, а не класс метки. Здесь ослабление класса
    даёт тождества «в» и «б», то есть красный, — и тест это ловит.
    """
    text = ("# Ход\n\nПринять вариант в редакции пакета либо вариант б редакции "
            "владельца.\n\n" + CLOSING + "\n")
    assert hits(check(checker, text), VARIANTS) == []


# ─────────────────── (б) «есть» без основания ────────────────────────────────

def test_est_without_because_red(checker):
    text = ("# Ход\n\nПериметр владельца: нет · Обратимость: один пакет · "
            "Долгосрочная разница: есть\n\n" + CLOSING + "\n")
    assert len(hits(check(checker, text), DIFFERENCE)) == 1


@pytest.mark.parametrize("field", [
    "Долгосрочная разница: есть, потому что имя проверки уходит в защиту ветки",
    "**Долгосрочная разница:** есть — потому что реестр связывает пакет",
])
def test_because_on_same_line_green(checker, field):
    text = "# Ход\n\n" + field + "\n\n" + CLOSING + "\n"
    assert hits(check(checker, text), DIFFERENCE) == []


def test_because_on_next_significant_line_green(checker):
    """Пустые строки пропускаются: считается следующая НЕПУСТАЯ строка."""
    text = ("# Ход\n\n**Долгосрочная разница:** есть\n\n\n"
            "потому что имя обязательной проверки уходит в защиту ветки.\n\n"
            + CLOSING + "\n")
    assert hits(check(checker, text), DIFFERENCE) == []


def test_difference_in_fenced_block_green(checker):
    """Гашение оград держит и ветку (б), а не только ветку (а) и скан hits.

    Форма — та же, что моделирует green-фикстура: блок владельцу, цитирующий
    образец ответа. Без гашения строка слота внутри ограды краснела бы.
    """
    text = ("# Ход\n\nОбразец ответа, который вернёт владелец:\n\n"
            "```\nПериметр владельца: нет · Обратимость: один пакет · "
            "Долгосрочная разница: есть\n```\n\n" + CLOSING + "\n")
    assert check(checker, text) == []


def test_difference_net_is_green(checker):
    text = "# Ход\n\n**Долгосрочная разница:** нет\n\n" + CLOSING + "\n"
    assert hits(check(checker, text), DIFFERENCE) == []


def test_because_of_neighbouring_field_does_not_cover_red(checker):
    """Основание соседнего поля не покрывает «есть»: оно ищется в значении поля.

    Канон предписывает однострочную форму слота, поэтому «потому что» при
    «Периметре владельца» стоит на той же строке, что и непокрытое «есть».
    Поиск по строке снимал здесь находку — поиск по значению поля не снимает.
    """
    text = ("# Ход\n\n1= путь А\n2= путь Б\n\n"
            "**Периметр владельца: затронут, потому что публичное · Обратимость: "
            "один пакет · Долгосрочная разница: есть**\n\n" + CLOSING + "\n")
    assert len(hits(check(checker, text), DIFFERENCE)) == 1


def test_negated_mention_of_because_does_not_cover_red(checker):
    """Форма из вольта: канон-реестр, строка 138.

    Единственное «потому что» строки — отрицающее упоминание оборота, и стоит
    оно ЛЕВЕЕ поля. Предсказание — красный: упоминание оборота основанием поля
    не является.
    """
    text = ("# Ход\n\n"
            "(д) **Слот из трёх полей, заполненный без «потому что», не "
            "работает** — рецидив 4 «Конца хода» в тот же день, что и его "
            "лечение (§B): поле «Долгосрочная разница: есть» без двух названных "
            "целевых состояний есть та же категория, только переименованная.\n\n"
            + CLOSING + "\n")
    assert len(hits(check(checker, text), DIFFERENCE)) == 1


def test_est_in_neighbouring_field_is_not_the_value_green(checker):
    """Значение берётся по имени поля: «есть» в соседнем поле полем не является."""
    text = ("# Ход\n\nОбратимость: есть один пакет · Долгосрочная разница: нет\n\n"
            + CLOSING + "\n")
    assert hits(check(checker, text), DIFFERENCE) == []


# ───────────────────── (в) конец хода на анонсе ──────────────────────────────

def test_announce_red(checker):
    text = "# Ход\n\nПрогон зелёный.\n\n**Конец хода:** Записываю прогон в вольт\n"
    messages = check(checker, text)
    assert len(hits(messages, ANNOUNCE)) == 1
    # Ветка длины на этом хвосте молчит: 21 значащий символ при пороге 10 —
    # значит ветка анонса здесь единственное, что ловит рецидив.
    assert hits(messages, SHORT_TAIL) == []


@pytest.mark.parametrize("tail", [
    "Следующим шагом соберу пакет",
    "далее прогоню линтер",
    "**Дальше** правлю реестр",
    "— Приступаю к перепривязке",
    "Сейчас сделаю прогон",
    "Продолжаю добор корпуса",
])
def test_announce_forms_are_red(checker, tail):
    text = f"# Ход\n\n**Конец хода:** {tail}\n"
    assert len(hits(check(checker, text), ANNOUNCE)) == 1


def test_announce_word_inside_tail_green(checker):
    """Маркер сверяется с началом хвоста: «дальше» в середине — законная речь.

    Замерено на настоящих закрывающих строках владельца: слово «дальше» стоит
    внутри 3 из 24 и ни одна из 24 с маркера не начинается.
    """
    text = ("# Ход\n\n**Конец хода:** нужно слово владельца — принять корпус, "
            "и дальше идём к добору сценариев.\n")
    assert hits(check(checker, text), ANNOUNCE) == []


def test_announce_in_fenced_block_green(checker):
    """Анонс внутри блока владельцу — цитата формы, а не закрывающая реплика."""
    text = ("# Ход\n\nОбразец возвращаемой формы:\n\n"
            "```\n**Конец хода:** Записываю прогон в вольт\n```\n\n" + CLOSING + "\n")
    assert check(checker, text) == []


# ─────────────────── прежние ветки: сохранены ────────────────────────────────

def test_empty_tail_still_red(checker):
    """Прежняя ветка длины: хвост короче порога значащих символов."""
    text = "# Ход\n\n**Конец хода:** ok\n"
    assert len(hits(check(checker, text), SHORT_TAIL)) == 1


def test_missing_turn_end_line_still_red(checker):
    """Прежняя ветка присутствия: строки «Конец хода» в артефакте нет вовсе."""
    text = "# Ход\n\nПакет собран, отчёт принят.\n"
    assert len(hits(check(checker, text), ABSENT)) == 1


# ───────────────────────── рецидивы, все красные ─────────────────────────────

def test_recidive_three_questions_with_variants_red(checker):
    """Рецидив 1: три вопроса владельцу с вариантами и без единого поля слота."""
    text = ("# Ход\n\nВопрос 1. Как заводить ветку?\n\n"
            "1= завожу сам от origin/main\n2= ждём владельца\n\n"
            "Вопрос 2. Куда класть тесты?\n\n"
            "А) рядом с тестами чекеров\nБ) отдельным файлом\n\n"
            "Вопрос 3. Порог?\n\nвариант А — оставить два\nвариант Б — поднять\n\n"
            + CLOSING + "\n")
    assert len(hits(check(checker, text), VARIANTS)) == 1


def test_recidive_main_option_and_alternative_red(checker):
    """Рецидив 2: «основной вариант и близкая альтернатива» трижды, без полей."""
    text = ("# Ход\n\nПо первому узлу: основной вариант — правка манифеста, "
            "близкая альтернатива — правка кода.\n\n"
            "По второму узлу: основной вариант — дополнить фикстуру, близкая "
            "альтернатива — завести вторую.\n\n"
            "По третьему узлу: основной вариант — перепривязать хэш, близкая "
            "альтернатива — отложить.\n\n" + CLOSING + "\n")
    assert len(hits(check(checker, text), VARIANTS)) == 1


def test_recidive_writing_report_announce_red(checker):
    """Рецидив 3: ход закрыт строкой «Записываю прогон в вольт»."""
    text = "# Ход\n\nПрогон собран.\n\n**Конец хода:** Записываю прогон в вольт\n"
    assert len(hits(check(checker, text), ANNOUNCE)) == 1


# ───────────────────────── фикстуры: на артефакт --fast ──────────────────────

def test_red_fixture_carries_all_four_branches(capsys):
    code, lines = fixture_findings(capsys, "red")
    assert code == 1
    assert len(lines) == BASELINE_RED + 3
    for branch in (SHORT_TAIL, VARIANTS, DIFFERENCE, ANNOUNCE):
        assert len([ln for ln in lines if branch in ln]) == 1


def test_green_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green")
    assert (code, lines) == (0, [])


# ───────────────────────── данная снята — отказ, не молчание ─────────────────

@pytest.mark.parametrize("key", ["variant_markers", "variant_markers_paired",
                                 "variant_min", "slot_fields",
                                 "difference_field_pattern",
                                 "difference_yes_pattern", "because_pattern",
                                 "announce_lead_strip", "announce_markers"])
def test_missing_data_key_fails_closed(checker, key):
    """Снятая данная — отказ чекера, а не ветка, молчащая нулём находок.

    Умолчания в коде нет намеренно: «ключа нет» обязано быть отличимо от
    «форма не встретилась», иначе снятый список дал бы пустую выдачу при
    нулевом коде выхода (§11, R-VACUUM-007). run.py обращает отказ в красный
    `checker_error`.
    """
    config = dict(checker["config"])
    config.pop(key)
    with pytest.raises(ConfigDefect):
        checker["module"].check("# Ход\n\n1= раз\n2= два\n", config)
