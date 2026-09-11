"""Форма `disposition_unit_unnamed` пакета B-P2b-P3a.

Повод — 00-system/canon-corrections-register.md §A, 2026-08-31, класс К2: вилки
названы на один ход, прогон шёл по стенограмме двадцати, расхождение ×3–5
прочиталось дефектом детекторов, а было дефектом предсказания. Правка §11 была
там же вынесена «первым упражнением гейта этапа B»; здесь её механическая
половина.

Единица диспозиции — «на артефакт `--fast`» для фикстур и «на строку» для
пофразных случаев.

Отдельно здесь стоит **страж падения** (`test_both_forms_live_on_the_red_fixture`):
у чекера две формы, а `run.calibrate` ставит `[ok]` по одной находке своего
имени. Смерть любой из форм печатает ту же строку калибровки, и разложение по
префиксу — единственное, что делает её видимой (мутации M-U6 и M-U7).

Каждый случай оправдания — ПАРА: оправдывающий текст молчит, он же без
оправдывающего элемента краснеет. Без пары тест прошёл бы и при мёртвом
триггере: молчание формы неотличимо от молчания детектора. Ровно на этом в
пакете P2 три мутации из девяти вернулись зелёными с первого прогона.
"""

from __future__ import annotations

import os

import pytest
import yaml

import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "linter", "fixtures")

NAME = "detector_disposition"
UNIT_FORM = "disposition_unit_unnamed"

# Строка введения детектора: триггер общий у обеих форм, и без него молчат обе.
INTRO = "Пакет вводит новый чекер `policy_scope`.\n\n"


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(os.path.join(ROOT, "linter", "manifest.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@pytest.fixture(scope="module")
def entry(manifest) -> dict:
    return {c["name"]: c for c in manifest["checkers"]}[NAME]


@pytest.fixture(scope="module")
def checkers(manifest) -> dict:
    active, _skipped, failed = run.load_checkers(manifest, "handoff")
    assert failed == []
    return {c["name"]: c for c in active}


def check(checkers, text: str) -> list[str]:
    c = checkers[NAME]
    return [f.message for f in c["module"].check(text, c["config"])]


def units(messages: list[str]) -> list[str]:
    return [m for m in messages if f"[{UNIT_FORM}]" in m]


def turn(*body: str) -> str:
    return INTRO + "".join(body)


def fixture_findings(capsys, colour: str) -> tuple[int, list[str]]:
    path = os.path.join(FIXTURES, colour, f"{NAME}.md")
    code = run.main(["--fast", path, "--no-report"])
    out = capsys.readouterr().out
    listed = out.split("## Находки", 1)[1].split("## Сводка", 1)[0]
    return code, [ln for ln in listed.splitlines() if f" {NAME} " in ln]


# ── фикстуры: на артефакт --fast ─────────────────────────────────────────

def test_both_forms_live_on_the_red_fixture(capsys):
    """Страж падения: счёт разложен по формам, иначе он их прячет.

    Калибровка требует ≥1 находки своего чекера на своей red-фикстуре. Форм две;
    замолчи любая, калибровка всё равно напечатала бы
    `detector_disposition red=1 green=0 [ok]` — ни красного, ни строки «не
    измерено», ни кода выхода. Мутации M-U6 (снять форму) и M-U7 (обусловить её
    полнотой слотов) обе гасят ровно тегированную находку, и оба счёта
    утверждаются раздельно: смерть одной формы не маскируется другой.
    """
    code, lines = fixture_findings(capsys, "red")
    tagged = [ln for ln in lines if f"[{UNIT_FORM}]" in ln]
    untagged = [ln for ln in lines if "[" not in ln.split(NAME, 1)[1]]
    assert code == 1
    assert (len(untagged), len(tagged)) == (1, 1)
    assert len(lines) == 2


def test_the_red_fixture_names_the_number_and_the_units(capsys):
    """Сообщение несёт ремонт, а не только жалобу: число и три единицы канона."""
    _code, lines = fixture_findings(capsys, "red")
    tagged = [ln for ln in lines if f"[{UNIT_FORM}]" in ln][0]
    assert "«2–4»" in tagged
    assert "на артефакт / на ход / на прогон" in tagged


def test_green_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green")
    assert (code, lines) == (0, [])


# ── триггер и его отсутствие ─────────────────────────────────────────────

def test_no_intro_no_form(checkers):
    """Форма наследует триггер: «Допустимые попадания» пункта — ход, не вводящий
    детектора, — здесь есть отсутствие триггера. Пара доказывает, что молчание
    от отсутствия триггера, а не от мёртвой формы."""
    body = "Предсказанная диспозиция: 20.\n"
    assert units(check(checkers, body)) == []
    assert len(units(check(checkers, turn(body)))) == 1


def test_a_fenced_prediction_is_not_judged(checkers):
    """Строка внутри ограды — команда или пример, а не предсказание хода."""
    fenced = turn("```text\nПредсказанная диспозиция: 20.\n```\n")
    assert units(check(checkers, fenced)) == []
    assert len(units(check(checkers, turn("Предсказанная диспозиция: 20.\n")))) == 1


# ── M-U1: указатель на предсказание не есть предсказание ─────────────────

def test_a_pointer_to_the_prediction_is_not_the_prediction(checkers):
    """M-U1. Снять unit_pointer_patterns — и шаг «Записать предсказанные
    диспозиции (ниже)» соберёт числа следующих шагов."""
    pointing = turn(
        "1. Записать предсказанные диспозиции (ниже) — до правки.\n"
        "2. Починить green-фикстуру пином; прогон — 0 находок.\n")
    assert units(check(checkers, pointing)) == []
    named = turn(
        "1. Записать предсказанные диспозиции — до правки.\n"
        "2. Починить green-фикстуру пином; прогон — 0 находок.\n")
    assert len(units(check(checkers, named))) == 1


# ── M-U2: область кончается на заголовке ─────────────────────────────────

def test_the_region_ends_at_the_next_heading(checkers):
    """M-U2. Снять unit_section_end_pattern — и предсказание с названной
    единицей соберёт число соседнего раздела (смоук-строку)."""
    bounded = turn(
        "- **Предсказанная диспозиция:** красный на местах публичной политики.\n"
        "\n"
        "## Ваши действия\n"
        "\n"
        "Ожидаемо: код выхода 1.\n")
    assert units(check(checkers, bounded)) == []
    merged = turn(
        "- **Предсказанная диспозиция:** красный на местах публичной политики.\n"
        "\n"
        "Ожидаемо: код выхода 1.\n")
    assert len(units(check(checkers, merged))) == 1


# ── M-U3: адрес и идентификатор количеством не являются ──────────────────

@pytest.mark.parametrize("address", [
    "замер сделан 2026-08-31",
    "пункт §11 контракта",
    "сценарий S-14",
    "версия v0 полосы",
    "пакет B-P2b-P2",
    "строка linter/manifest.yaml:8",
    "расхождение ×3–5 прошлого прогона",
])
def test_an_address_is_not_a_quantity(checkers, address):
    """M-U3. Снять просмотры в unit_quantity_pattern — и дата, параграф,
    идентификатор сценария и адрес строки станут «предсказанным числом»."""
    silent = turn(f"- **Предсказанная диспозиция:** красный на местах, {address}.\n")
    assert units(check(checkers, silent)) == []
    loud = turn(f"- **Предсказанная диспозиция:** 2–4, {address}.\n")
    assert len(units(check(checkers, loud))) == 1


# ── M-U4: номер пункта не есть счёт находок ──────────────────────────────

def test_an_ordered_list_marker_is_not_a_quantity(checkers):
    """M-U4. Снять unit_list_marker_pattern — и номер шага станет числом."""
    steps = turn(
        "Предсказанные диспозиции разложены по веткам.\n"
        "\n"
        "1. Ветки данных первыми.\n"
        "2. Затем модуль.\n")
    assert units(check(checkers, steps)) == []
    counted = turn(
        "Предсказанные диспозиции разложены по веткам.\n"
        "\n"
        "1. Ветки данных первыми, ожидаем 2 находки.\n"
        "2. Затем модуль.\n")
    assert len(units(check(checkers, counted))) == 1


# ── M-U5: названная единица оправдывает ──────────────────────────────────

@pytest.mark.parametrize("unit", ["на артефакт", "на ход", "на прогон", "на блок",
                                  "на 1000 строк", "на корпус"])
def test_a_named_unit_absolves(checkers, unit):
    """M-U5. Убрать единицу из unit_patterns — и зелёный случай фикстуры
    покраснеет. Пара: та же фраза без единицы краснеет уже сейчас."""
    absolved = turn(f"- **Предсказанная диспозиция:** 1–2 находки {unit}.\n")
    assert units(check(checkers, absolved)) == []
    bare = turn("- **Предсказанная диспозиция:** 1–2 находки.\n")
    assert len(units(check(checkers, bare))) == 1


# ── M-U9: совокупность, названная прозой, единицей не является ───────────

def test_a_scope_phrase_is_not_a_unit(checkers):
    """M-U9. Заменить закрытый список на «на + любое существительное» — и
    собственная фраза инцидента К2 станет оправданием.

    Это дословный текст session-2.md:819: оркестратор НАЗВАЛ совокупность прозой,
    и расхождение ×3–5 всё равно произошло. Закрытый список — структурное
    лечение; пара показывает, что при названной единице форма молчит.
    """
    incident = turn(
        "Фиксирую предсказанную диспозицию сейчас, на моих собственных ходах\n"
        "этой сессии как на настоящих handoff-артефактах:\n"
        "\n"
        "- `smoke_line` — 2–4, и это будут верные красные.\n")
    assert len(units(check(checkers, incident))) == 1
    repaired = turn(
        "Фиксирую предсказанную диспозицию сейчас, единица — на ход:\n"
        "\n"
        "- `smoke_line` — 2–4, и это будут верные красные.\n")
    assert units(check(checkers, repaired)) == []


# ── признак: цифра против числительного словом ───────────────────────────

def test_a_word_numeral_prediction_is_not_judged(checkers):
    """Числительное словом обязательно управляет существительным и тем самым
    называет свою совокупность; цифра не управляет ничем. Это и есть признак,
    по которому строка 12 green-фикстуры оставлена без правки."""
    in_words = turn(
        "- **Предсказанная диспозиция:** красный на четырёх местах публичной\n"
        "  политики.\n")
    assert units(check(checkers, in_words)) == []
    in_digits = turn("- **Предсказанная диспозиция:** красный на 4 местах.\n")
    assert len(units(check(checkers, in_digits))) == 1


def test_the_observed_disposition_is_not_judged(checkers):
    """Форма привязана к предсказанию: наблюдение есть измерение и называет свой
    артефакт само. Уже — намеренно, и пара это показывает."""
    observed = turn("- **Наблюдённая диспозиция:** 3 находки.\n")
    assert units(check(checkers, observed)) == []
    predicted = turn("- **Предсказанная диспозиция:** 3 находки.\n")
    assert len(units(check(checkers, predicted))) == 1


# ── M-U7: форма не обусловлена полнотой слотов ───────────────────────────

def test_the_form_is_not_gated_on_missing_slots(checkers):
    """M-U7. Слоты ищутся по всему документу, поэтому обусловленность формы
    полнотой слотов сделала бы обе формы невозможными на одной red-фикстуре:
    случай, называющий все три слота, стёр бы находку формы 1."""
    incomplete = turn("- **Предсказанная диспозиция:** 2–4.\n")
    msgs = check(checkers, incomplete)
    assert len(units(msgs)) == 1
    assert any("не называет" in m for m in msgs)     # форма 1 жива на том же тексте
    complete = turn(
        "- **Мутация:** подстановка фразы.\n"
        "- **Предсказанная диспозиция:** 2–4.\n"
        "- **Наблюдённая диспозиция:** 3.\n")
    msgs = check(checkers, complete)
    assert len(units(msgs)) == 1
    assert not any("не называет" in m for m in msgs)


# ── M-U8: имя слота и отсутствующий ключ — отказ, а не молчание ──────────

def test_unit_slot_name_resolves_in_slot_patterns(entry):
    """M-U8, статическая половина: слот адресуется именем, и имя обязано
    существовать. Второй копии шаблона нет намеренно — она разошлась бы молча."""
    cfg = entry["config"]
    names = [s["name"] for s in cfg["slot_patterns"]]
    assert cfg["unit_slot_name"] in names


def test_an_unresolvable_slot_name_is_a_checker_error(checkers):
    """M-U8, половина рантайма: имя не найдено — красный `checker_error` и «не
    измерено», а не тихий ноль находок."""
    broken = dict(checkers[NAME])
    broken["config"] = dict(checkers[NAME]["config"], unit_slot_name="нет такого слота")
    text = turn("- **Предсказанная диспозиция:** 2–4.\n")
    found, _applied, not_measured, failures = run.run_text([broken], text, "t.md", None, 2.0)
    assert found == []
    assert [f.status for f in failures] == [run.CHECKER_ERROR]
    assert NAME in not_measured


@pytest.mark.parametrize("key", ["unit_slot_name", "unit_quantity_pattern",
                                 "unit_list_marker_pattern", "unit_section_end_pattern",
                                 "unit_max_lines", "unit_pointer_patterns",
                                 "unit_patterns"])
def test_a_missing_form_key_is_a_checker_error(checkers, key):
    """Умолчания в коде нет намеренно: «ключ не задан» обязано быть отличимо от
    «форма снята». Та же доктрина, что у LIMIT_KEY в run.py."""
    cfg = dict(checkers[NAME]["config"])
    cfg.pop(key)
    broken = dict(checkers[NAME], config=cfg)
    text = turn("- **Предсказанная диспозиция:** 2–4.\n")
    _found, _applied, not_measured, failures = run.run_text([broken], text, "t.md", None, 2.0)
    assert [f.status for f in failures] == [run.CHECKER_ERROR]
    assert NAME in not_measured


# ── статические утверждения о манифесте ──────────────────────────────────

def test_unit_form_lists_live_in_the_manifest(entry):
    """Списки — данные: новая единица и новый указатель есть правка манифеста,
    не кода. Порогов в списках нет — иначе «список» был бы кодом."""
    cfg = entry["config"]
    assert cfg["unit_max_lines"] == 12
    assert any("артефакт" in p for p in cfg["unit_patterns"])
    assert any("ниже" in p for p in cfg["unit_pointer_patterns"])
    assert not any(any(ch.isdigit() for ch in p) for p in cfg["unit_pointer_patterns"])
    assert "unit_window" not in cfg


def test_the_region_boundary_is_a_feature_not_a_threshold(checkers):
    """Признак, а не порог: с границей раздела диспозиция ОДИНАКОВА при
    unit_max_lines 4, 8, 12, 20 и 40 — число меняет не счёт, а то, проверяется
    ли оправдание. Меряется рантаймом на том же тексте, что и M-U2.

    Положительный контроль на КАЖДОМ значении обязателен, и найден он вакуумной
    проверкой этого же пакета: без него тест утверждал только молчание и
    оставался зелёным при мутациях M-U6 и M-U7, то есть при мёртвой форме
    (antecedent failure, ADR-054 (13), NB-47 — «зелёный без свидетеля не
    отличается от зелёного со свидетелем, пока свидетель не предъявлен»).
    """
    bounded = turn(
        "- **Предсказанная диспозиция:** красный на местах публичной политики.\n"
        "\n"
        "## Ваши действия\n"
        "\n"
        "Ожидаемо: код выхода 1.\n")
    merged = turn(
        "- **Предсказанная диспозиция:** красный на местах публичной политики.\n"
        "\n"
        "Ожидаемо: код выхода 1.\n")
    c = checkers[NAME]
    for value in (4, 8, 12, 20, 40):
        cfg = dict(c["config"], unit_max_lines=value)
        assert units([f.message for f in c["module"].check(bounded, cfg)]) == [], value
        assert len(units([f.message for f in c["module"].check(merged, cfg)])) == 1, value


def test_the_checker_still_binds_its_rule_and_scenario(entry):
    """Форма приземляется на тот же пункт канона: R-DISPOSITION-012, S-14."""
    assert entry["rule_id"] == "R-DISPOSITION-012"
    assert entry["scenario"] == "S-14"
    assert entry["kinds"] == ["handoff"]
