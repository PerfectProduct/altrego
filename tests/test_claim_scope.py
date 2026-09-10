"""Формы пакета B-P2b-P2: `count_predicate_unmeasured` и `repo_state_claim`.

Повод — контракт §11, «Провенанс утверждений оркестратора» (реестр R-PROV-001).
Две формы, два дома, и дома разные по разбору:

  * `count_predicate_unmeasured` — четвёртая нога `claim_provenance`: тот же
    смысл («провенанса рядом нет») и тот же набор оправданий, другой триггер;
  * `repo_state_claim` — отдельный чекер: он краснеет ровно там, где
    `claim_provenance` замолкает (команда рядом есть), и его строка калибровки
    остаётся единственным живым сигналом при нулевой экспозиции на корпусе.

Единица диспозиции — «на артефакт `--fast`» для фикстур и «на строку» для
пофразных случаев.

Отдельно здесь стоит **страж падения** (`test_previous_legs_did_not_drop`):
общий счёт red-фикстуры `claim_provenance` равен 10, и он разложен по префиксам —
ноги 1–3 ровно 8, нога 4 ровно 2. Без разложения десятка спрятала бы ногу,
которая молча перестала краснеть: калибровка требует лишь одной находки своего
чекера, и три мёртвые ноги из четырёх её прошли бы.
"""

from __future__ import annotations

import os

import pytest
import yaml

import run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "linter", "fixtures")

CLAIM = "claim_provenance"
REPO = "repo_state_claim"
COUNT_FORM = "count_predicate_unmeasured"
DATE_FORM = "date_literal_unmeasured"
SCOPE_FORM = "command_scope_narrower_than_claim"

# Ноги 1–3 на red-фикстуре claim_provenance на момент заведения ноги 4.
LEGS_1_3_BASELINE = 8


@pytest.fixture(scope="module")
def manifest() -> dict:
    with open(os.path.join(ROOT, "linter", "manifest.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@pytest.fixture(scope="module")
def checkers(manifest) -> dict:
    active, _skipped, failed = run.load_checkers(manifest, "handoff")
    assert failed == []
    return {c["name"]: c for c in active}


def check(checkers, name: str, text: str) -> list[str]:
    c = checkers[name]
    return [f.message for f in c["module"].check(text, c["config"])]


def marked(messages: list[str], form: str) -> list[str]:
    return [m for m in messages if f"[{form}]" in m]


def block(*lines: str, lang: str = "bash") -> str:
    return "```%s\n%s\n```\n" % (lang, "\n".join(lines))


def fixture_findings(capsys, colour: str, name: str) -> tuple[int, list[str]]:
    path = os.path.join(FIXTURES, colour, f"{name}.md")
    code = run.main(["--fast", path, "--no-report"])
    out = capsys.readouterr().out
    listed = out.split("## Находки", 1)[1].split("## Сводка", 1)[0]
    return code, [ln for ln in listed.splitlines() if f" {name} " in ln]


# ── фикстуры: на артефакт --fast ─────────────────────────────────────────

def test_red_claim_fixture_carries_count_form(capsys):
    code, lines = fixture_findings(capsys, "red", CLAIM)
    assert code == 1
    assert len([ln for ln in lines if f"[{COUNT_FORM}]" in ln]) == 2


def test_previous_legs_did_not_drop(capsys):
    """Страж падения: счёт разложен по ногам, иначе он их прячет.

    Калибровка требует ≥1 находки своего чекера на своей red-фикстуре. У
    `claim_provenance` пять ног; замолчи четыре из них, калибровка всё равно
    напечатала бы `[ok]` — ни красного, ни строки «не измерено», ни кода
    выхода. Разложение по префиксу формы — то единственное, что делает смерть
    ноги видимой, и потому этот тест, а не калибровка, есть сторож ноги 5
    (мутация M-D6). Двоичного разложения мало: пока «старым» считалось «без
    префикса `count_predicate_unmeasured`», находка ноги 5 попадала бы в тот же
    мешок и арифметика оставалась бы верной при мёртвых ногах 1–3.
    """
    _code, lines = fixture_findings(capsys, "red", CLAIM)
    counted = [ln for ln in lines if f"[{COUNT_FORM}]" in ln]
    dated = [ln for ln in lines if f"[{DATE_FORM}]" in ln]
    untagged = [ln for ln in lines if "[" not in ln.split(CLAIM, 1)[1]]
    assert (len(untagged), len(counted), len(dated)) == (LEGS_1_3_BASELINE, 2, 2)
    assert len(lines) == LEGS_1_3_BASELINE + 4


def test_green_claim_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green", CLAIM)
    assert (code, lines) == (0, [])


def test_red_repo_fixture_carries_two(capsys):
    code, lines = fixture_findings(capsys, "red", REPO)
    assert code == 1
    assert len(lines) == 2
    assert len([ln for ln in lines if f"[{SCOPE_FORM}]" in ln]) == 2


def test_red_repo_fixture_names_both_blindnesses(capsys):
    """Два случая — две разные слепоты, а не одна дважды."""
    _code, lines = fixture_findings(capsys, "red", REPO)
    assert any("неотслеживаемых" in ln for ln in lines)
    assert any("обрезан" in ln for ln in lines)


def test_green_repo_fixture_stays_silent(capsys):
    code, lines = fixture_findings(capsys, "green", REPO)
    assert (code, lines) == (0, [])


# ── count_predicate_unmeasured: на строку ────────────────────────────────

@pytest.mark.parametrize("line", [
    "Все чекеры полосы зелёные.",
    "Ни одной находки на green-фикстурах нет.",
    "Ни один сценарий корпуса не остался без оракула.",
    "Единственный чекер без сценария — этот.",
])
def test_count_predicate_reddens(checkers, line):
    assert marked(check(checkers, CLAIM, line + "\n"), COUNT_FORM)


def test_an_adverb_is_not_a_count_predicate(checkers):
    """«Покрыт полностью» — наречие при глаголе, а не квантор при множестве.

    Триггер требует порядка «квантор → счётное существительное»: то же слово в
    наречной позиции притязания на величину набора не делает. Это следствие
    меры управления, а не отдельный список изъятий.
    """
    text = "Корпус покрыт полностью: правила без сценария не осталось.\n"
    assert marked(check(checkers, CLAIM, text), COUNT_FORM) == []


@pytest.mark.parametrize("line", [
    "Все чекеры полосы зелёные — выдача `run.py --no-report --fast`, строка вердикта.",
    "Ни одной находки нет — это прочитано в выдаче прогона.",
    "Все чекеры полосы зелёные, но не проверено на свежем клоне.",
])
def test_provenance_absolves_the_count(checkers, line):
    assert marked(check(checkers, CLAIM, line + "\n"), COUNT_FORM) == []


def test_prediction_is_not_a_claim(checkers):
    """«Ожидание: ни одной находки» — предсказание, а не притязание.

    Оправдание узкое: `prediction_pattern` не несёт слова «оценка» — по той же
    причине, по какой его нет в `claim_unverified_pattern` (рецидив 3 реестра).
    """
    assert marked(check(checkers, CLAIM,
                        "Ожидание: ни одной находки env_presupposition.\n"),
                  COUNT_FORM) == []


def test_irrealis_is_not_an_assertion(checkers):
    """Мутация M2: снятие `irrealis_pattern` красит этот тест."""
    text = "Снятие ключа не покрасило бы ни одного теста.\n"
    assert marked(check(checkers, CLAIM, text), COUNT_FORM) == []


def test_scenario_frame_is_not_a_claim(checkers):
    """Мутация M3: снятие `hypothetical_frame_pattern` красит этот тест.

    Рамка меряется на самой строке: в разборе корпуса «Дано / Действие /
    Ожидаемо» стоят подряд одной строкой, а не тремя.
    """
    text = ("**S-05 · К4.** Дано: ход завершается. Действие: ни один пункт "
            "блока действий не требует решения.\n")
    assert marked(check(checkers, CLAIM, text), COUNT_FORM) == []


def test_distributive_quantifier_is_not_a_count(checkers):
    """Мутация M1: замена управления на окно в символах красит этот тест.

    «Каждая предпосылка измеряется строкой выше» — квантор управляет соседним
    словом, а не счётным: это дистрибутив, а не утверждение о величине набора.
    Строка живёт в `linter/fixtures/green/env_presupposition.md`, и окно в
    символах покрасило бы на ней гейт.
    """
    text = "Тот же предмет: каждая предпосылка измеряется строкой выше той.\n"
    assert marked(check(checkers, CLAIM, text), COUNT_FORM) == []


def test_gap_measure_is_named_and_bounded(checkers):
    """Мутация M1: `count_gap_words` 1 → 8 красит этот тест.

    Мера управления — «квантор, не дальше `count_gap_words` слов, затем
    существительное». Предел назван, а не опущен: «все ТРИ НОВЫХ чекера» — два
    промежуточных слова, и на единице он не ловится. Это цена меры, а не порог
    под подгонку: расширение окна возвращает дистрибутивные пары, ради которых
    мера и заведена. Класс ложного отрицания назван здесь, чтобы он не
    выглядел молчанием без причины.
    """
    assert marked(check(checkers, CLAIM, "Все новые чекеры зелёные.\n"), COUNT_FORM)
    assert marked(check(checkers, CLAIM, "Все три новых чекера зелёные.\n"),
                  COUNT_FORM) == []


def test_numeral_is_not_the_subject(checkers):
    """Числительное — предмет ног 1 и 2, и ногой 4 не судится.

    Названная цена: голый счётчик сегодня не ловит ни одна нога. Закрытие
    пробела стоило бы правки двух чужих green-фикстур и идёт отдельным пакетом.
    """
    assert marked(check(checkers, CLAIM, "17 чекеров полосы зелёные.\n"),
                  COUNT_FORM) == []


def test_noun_list_is_data(checkers):
    """Список существительных — данные манифеста, и это меряется.

    «Откат» в `countable_nouns` не стоит, поэтому та же грамматика на нём не
    срабатывает. Мутация M8 (убрать `находк\\w*`) красит счёт red-фикстуры.
    """
    assert marked(check(checkers, CLAIM, "Ни одного отката в механике нет.\n"),
                  COUNT_FORM) == []
    assert marked(check(checkers, CLAIM, "Ни одной находки в механике нет.\n"),
                  COUNT_FORM)


def test_fenced_line_is_not_a_claim(checkers):
    text = block("echo 'все чекеры зелёные'")
    assert marked(check(checkers, CLAIM, text), COUNT_FORM) == []


def test_a_line_judged_by_legs_1_3_is_not_judged_twice(checkers):
    """Вторая находка того же класса на той же строке назвала бы отказ дважды."""
    text = "Все ходы §6 закрывались строкой, называющей требуемое слово.\n"
    messages = check(checkers, CLAIM, text)
    assert len(messages) == 1
    assert marked(messages, COUNT_FORM) == []


# ── repo_state_claim: на строку ──────────────────────────────────────────

def test_scope_narrower_than_claim_reddens(checkers):
    text = "Состав правки измерен: 9 путей, 356 строк.\n\n" + block("git diff --stat -w main")
    assert marked(check(checkers, REPO, text), SCOPE_FORM)


def test_truncated_output_reddens(checkers):
    text = "Рабочее дерево чисто целиком.\n\n" + block("git status --porcelain | head -20")
    assert marked(check(checkers, REPO, text), SCOPE_FORM)


def test_scope_covering_command_absolves(checkers):
    """Мутация M5: убрать `git status --porcelain` из покрывающих.

    Покрытие проверяется там, где оно и работает: узкая команда стоит рядом,
    и покрывающая обязана её перебить. Первая редакция этого теста ставила
    `git diff --cached` — и мерила не покрытие, а отрицательный просмотр в
    самом узком шаблоне; мутация M5 её не красила, и слот стоял мёртвым.
    """
    text = ("Состав правки — 14 путей, 1205 строк.\n\n"
            + block("git diff --stat -w main", "git status --porcelain"))
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_staged_diff_is_not_a_narrow_command(checkers):
    """`--cached` снимает узость самим шаблоном, не списком покрывающих."""
    text = "Состав правки — 14 путей: `git diff --cached --stat -w`.\n"
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_named_limit_absolves(checkers):
    text = ("Состав правки по отслеживаемым файлам — 9 путей, без учёта "
            "неотслеживаемых.\n\n" + block("git diff --stat -w main"))
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_the_diff_as_subject_is_not_the_class(checkers):
    """Мутация M4: снять различение областей — красит гейт на green/claim_provenance.md.

    «В diff 4 файла» — область команды равна области утверждения. Это не изъятие
    по слову, а следствие положительного списка `claim_scopes`: предмет «дифф» в
    него не входит вовсе.
    """
    text = "В diff 4 файла — выдача `git diff --stat -w`, строка «4 files changed».\n"
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_a_pipe_is_not_a_truncation(checkers):
    """Мера — усечение, а не конвейер.

    `git status --porcelain | wc -l` считает весь вывод. Наивное «в трубе —
    значит не покрывает» покрасило бы `linter/fixtures/green/shell_mech.md`,
    где ровно эта строка стоит внутри ограды.
    """
    text = "Незакоммиченных файлов нет.\n\n" + block("git status --porcelain | wc -l")
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_predicates_are_whole_words(checkers):
    """Правка входа со своим тестом: без `\\b` предикат ловит себя внутри слова.

    `пуст\\w+` без границы совпадает с «проПУСТили», и находка встаёт на строке,
    где счётного притязания нет вовсе. Наблюдено на калибровочном наборе
    (`session-2.md:740`): предсказан ноль находок, измерена одна — по этому
    токену. Предсказание разошлось с наблюдением, дефект был в мере, а не в
    пороге, и лечится он границей слова, а не сужением списка.
    """
    text = ("Дефект не в том, что вы что-то пропустили, а в самом чекере: "
            "авторитетный носитель канона — рабочая копия вольта, где правки "
            "лежат незакоммиченными.\n\n"
            + block("git status --porcelain | head -20"))
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []
    # тот же блок под настоящим притязанием — краснеет
    text = ("Рабочее дерево пусто.\n\n" + block("git status --porcelain | head -20"))
    assert marked(check(checkers, REPO, text), SCOPE_FORM)


def test_instruction_to_the_owner_is_not_a_claim(checkers):
    text = "1. Сверить состав правки целиком и прислать вывод:\n\n" + block("git diff --stat -w")
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_canon_address_is_a_foreign_subject(checkers):
    """Адрес пункта канона судит нога 3 `claim_provenance`, не этот чекер."""
    text = "Состав правки описан в §6 файла контракта, строка 113.\n\n" + block("git diff --stat -w")
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


def test_claim_inside_a_fence_is_not_a_claim(checkers):
    text = block("echo 'состав правки: 9 путей'", "git diff --stat -w")
    assert marked(check(checkers, REPO, text), SCOPE_FORM) == []


# ── разграничение с соседями: измерение, а не довод ──────────────────────

def test_claim_provenance_is_silent_where_the_scope_form_reddens(checkers):
    """Провенанс на месте — сосед молчит; область уже — этот чекер краснеет."""
    text = "Состав правки измерен: 9 путей, 356 строк.\n\n" + block("git diff --stat -w main")
    assert check(checkers, CLAIM, text) == []
    assert marked(check(checkers, REPO, text), SCOPE_FORM)


def test_the_scope_form_is_silent_on_a_bare_estimate(checkers):
    """Обратное направление: числовая оценка — предмет `claim_provenance`."""
    text = "Темп правок канона — примерно 5 в неделю.\n"
    assert check(checkers, REPO, text) == []
    assert check(checkers, CLAIM, text)


def test_whitespace_filter_does_not_absolve_the_scope_form(checkers):
    """`-w` оправдывает `whitespace_diff` и не оправдывает этот чекер.

    Фильтр пробелов меняет, что считается правкой, а не то, какие файлы вообще
    попадают в счёт: неотслеживаемых `git diff -w` не видит ровно так же.
    """
    text = "Состав правки измерен: 9 путей, 356 строк.\n\n" + block("git diff --stat -w main")
    assert check(checkers, "whitespace_diff", text) == []
    assert marked(check(checkers, REPO, text), SCOPE_FORM)


# ── статические утверждения о манифесте ──────────────────────────────────

def test_checker_is_gated_by_artifact_integrity(manifest):
    """Мутация M6: на артефакте без оград команд нет вовсе, и ноль находок
    читался бы как чистота (R-VACUUM-007)."""
    gates = {c["name"]: c for c in manifest["checkers"]}["artifact_integrity"]
    assert REPO in gates["config"]["gates"]


def test_checker_kinds_are_measured_not_inherited(manifest):
    """Вид измерен по spec-корпусу на диске (планы пакетов), а не выведен из
    правила: 7 находок на 1000 строк — потому spec, а не только handoff."""
    entry = {c["name"]: c for c in manifest["checkers"]}[REPO]
    assert entry["kinds"] == ["handoff", "spec"]


def test_checker_binds_the_provenance_rule(manifest):
    entry = {c["name"]: c for c in manifest["checkers"]}[REPO]
    assert entry["rule_id"] == "R-PROV-001"
    assert "scenario" not in entry


def test_count_form_lists_live_in_the_manifest(manifest):
    """Списки — данные: новая форма есть правка манифеста, не кода."""
    cfg = {c["name"]: c for c in manifest["checkers"]}[CLAIM]["config"]
    assert cfg["count_gap_words"] == 1
    assert "чекер\\w*" in cfg["countable_nouns"]
    assert not any(any(ch.isdigit() for ch in p) for p in cfg["count_quantifier_patterns"])


# ── date_literal_unmeasured: на строку ───────────────────────────────────

STOP_BLOCK = ("## Стоп-условия пакета\n\n"
              "- Сегодня — 2026-09-10\n"
              "- Ветка впереди main ровно на 7 коммитов\n")


@pytest.mark.parametrize("line", [
    "Сегодня — 2026-09-10.",
    "Сегодняшняя дата 2026-09-10 уходит в имя отчёта.",
    "Дата этого хода — 2026-09-10.",
    "Today is 2026-09-10.",
])
def test_date_literal_reddens(checkers, line):
    assert marked(check(checkers, CLAIM, line + "\n"), DATE_FORM)


@pytest.mark.parametrize("line,stripped", [
    ("Сегодня по среде — 2026-09-10.",
     "Сегодня — 2026-09-10."),
    ("Дата этого хода — 2026-09-10 — выдача `date -u +%F`.",
     "Дата этого хода — 2026-09-10 — выдача есть."),
    ("Сегодня — 2026-09-10: дата продиктована владельцем в этом ходе.",
     "Сегодня — 2026-09-10: дата взята в этом ходе."),
    ("Сегодня — 2026-09-10, снято `git log -1 --format=%ct` в этом ходе.",
     "Сегодня — 2026-09-10, снято в этом ходе."),
])
def test_a_named_source_absolves_the_date(checkers, line, stripped):
    """По одному оправданию на случай — и у каждого свой живой контроль.

    `stripped` — та же строка без одного оправдывающего оборота. Без этой
    половины пары тест прошёл бы и при мёртвом триггере: молчание ноги
    неотличимо от молчания детектора. Ровно на этом в пакете P2 три мутации из
    девяти вернулись зелёными с первого прогона.
    """
    assert marked(check(checkers, CLAIM, line + "\n"), DATE_FORM) == []
    assert marked(check(checkers, CLAIM, stripped + "\n"), DATE_FORM)


def test_environment_named_absolves(checkers):
    """Мутация M-D3: убрать канал среды из `date_source_patterns`.

    Пара: та же строка без двух оправдывающих слов обязана краснеть, иначе тест
    прошёл бы при мёртвом триггере, а не при живом оправдании. Этот слот несёт
    16 из 20 сырых попаданий калибровочного набора — соглашение полосы.
    """
    assert marked(check(checkers, CLAIM, "Сегодня по среде — 2026-09-10.\n"),
                  DATE_FORM) == []
    assert marked(check(checkers, CLAIM, "Сегодня — 2026-09-10.\n"), DATE_FORM)


def test_the_log_tail_is_not_a_source(checkers):
    """Список оправданий положительный: годится только то, что в нём стоит.

    «Взята из хвоста лога» источник называет — и расширение контракта от
    2026-08-25 исключает именно этот канал дословно.
    """
    assert marked(check(checkers, CLAIM,
                        "Дата этого хода — 2026-09-10, взята из хвоста лога.\n"),
                  DATE_FORM)


def test_deictic_coordinated_with_a_past_date_is_not_a_claim(checkers):
    """Мутация M-D1: заменить управление окном в символах.

    «пропущенный случай 2026-08-30 и сегодняшний» — литерал назван как ДРУГОЙ
    член пары, то есть заведомо не сегодняшний; сегодняшняя дата в строке не
    написана вовсе. Окно в символах свело бы их в пару. Наблюдено на
    калибровочном наборе дважды (`session-2.md:543`, `:564`).

    Пара: та же грамматика с литералом в позиции управления обязана краснеть —
    иначе тест молчал бы оттого, что триггер мёртв, а не оттого, что сужение
    работает.
    """
    text = "Занести обе строки в §B (пропущенный случай 2026-08-30 и сегодняшний).\n"
    assert marked(check(checkers, CLAIM, text), DATE_FORM) == []
    assert marked(check(checkers, CLAIM, "Занести обе строки: сегодня — 2026-08-30.\n"),
                  DATE_FORM)


def test_a_deictic_governing_a_command_is_not_a_date_claim(checkers):
    """Второй наблюдённый ложный класс (`session-2.md:539`).

    «Сегодняшний `pip install --user` — третий случай» — дейксис управляет
    командой; литералы в строке суть даты чужих записей реестра.
    """
    text = ("Правило стоит со счётом 1 (2026-08-28, имя по памяти). "
            "Сегодняшний `pip install --user` — третий случай.\n")
    assert marked(check(checkers, CLAIM, text), DATE_FORM) == []
    # Живой контроль: тот же дейксис, управляющий литералом, — краснеет.
    assert marked(check(checkers, CLAIM,
                        "Правило стоит со счётом 1. Сегодня — 2026-08-28.\n"),
                  DATE_FORM)


def test_date_gap_is_named_and_bounded(checkers):
    """Мутация M-D2: `date_gap_words` 3 → 8.

    Мера управления: дейксис, не дальше `date_gap_words` слов, затем литерал.
    Предел назван, а не опущен. Пара в обе стороны на одной мере: зачин полосы
    с тремя промежуточными словами обязан СРАБОТАТЬ (иначе оправдание стояло бы
    мёртвым слотом), а четыре слова — уже не управление.
    """
    assert marked(check(checkers, CLAIM, "Сегодня три записи лога дают 2026-08-30.\n"),
                  DATE_FORM) == []
    assert marked(check(checkers, CLAIM, "Сегодня уже стало поздно 2026-09-10.\n"),
                  DATE_FORM)


def test_a_date_in_a_stop_block_is_judged(checkers):
    """Мутация M-D4: заставить ногу 5 пропускать `stop_lines`.

    Нога 1 гасит литерал даты маской `ignore_patterns` (иначе `2026-09-10`
    читался бы как три голых числа), поэтому дата в блоке стоп-условия сегодня
    не судится ни одной ногой — это и есть пробел, названный §D реестра. Нога 5
    строит своё множество пропуска: `judged` засеян `stop_lines`, и
    переиспользование его дословно вернуло бы мутанта.

    Пара — положительный контроль того, что блок ВООБЩЕ распознан: без него
    прозаическая строка после маркера в блок не входит (`_blocks` вернёт
    `[(0, 0)]`), тест прошёл бы и с сужением, и без него, и мерил бы ничто.
    """
    messages = check(checkers, CLAIM, STOP_BLOCK)
    assert any(m.startswith("число 7") for m in messages)
    assert marked(messages, DATE_FORM)


def test_an_irrealis_date_is_not_a_claim(checkers):
    """Мутация M-D9: снять гард наклонения у ноги 5.

    Ход, вводящий эту ногу, сам несёт строки такой формы.
    """
    assert marked(check(checkers, CLAIM,
                        "Если бы сегодня было 2026-09-10, штамп ушёл бы вчерашним.\n"),
                  DATE_FORM) == []
    assert marked(check(checkers, CLAIM,
                        "Сегодня было 2026-09-10, штамп ушёл вчерашним.\n"), DATE_FORM)


def test_a_scenario_frame_date_is_not_a_claim(checkers):
    """Мутация M-D9, вторая форма гарда: рамка «Дано / Действие / Ожидаемо»."""
    assert marked(check(checkers, CLAIM,
                        "Дано: сегодня — 2026-09-10. Действие: запись в лог.\n"),
                  DATE_FORM) == []
    assert marked(check(checkers, CLAIM,
                        "Проверено: сегодня — 2026-09-10. Запись в лог.\n"), DATE_FORM)


def test_a_bare_date_literal_is_not_a_claim(checkers):
    """Умышленное несовпадение: голая дата без дейксиса.

    Имя файла отчёта и идентификатор чужой записи — ДОПУСТИМЫЕ попадания
    (контракт: имена, создаваемые самим ходом, и идентификаторы, продиктованные
    владельцем; CLAUDE.md п. 8а: цитирование чужих дат как дат акта). Варианты
    D2–D4 пакета P2 встали ровно на том, что держали их внутри триггера.
    """
    for line, control in (
        ("Отчёт лёг в `05-inbox/raw/otchet-2026-09-04.md`.",
         "Отчёт за сегодня — 2026-09-04."),
        ("Owner-акт 2026-08-30 (2) о аддитивной дозаписи.",
         "Сегодня — 2026-08-30, owner-акт (2) о аддитивной дозаписи."),
    ):
        assert marked(check(checkers, CLAIM, line + "\n"), DATE_FORM) == []
        # Живой контроль: тот же литерал под дейксисом — краснеет. Молчит
        # именно отсутствие дейксиса, а не неспособность ноги увидеть дату.
        assert marked(check(checkers, CLAIM, control + "\n"), DATE_FORM)


def test_date_inside_a_fence_is_not_a_claim(checkers):
    """Мутация M-D7: снять пропуск огороженных строк.

    Пара: то же предложение вне ограды обязано краснеть — иначе тест прошёл бы
    оттого, что триггер не совпадает с текстом вида `echo`, а не оттого, что
    ограда работает.
    """
    assert marked(check(checkers, CLAIM, block("echo 'Сегодня — 2026-09-10'")),
                  DATE_FORM) == []
    assert marked(check(checkers, CLAIM, "Сегодня — 2026-09-10\n"), DATE_FORM)


def test_source_named_on_the_next_line_absolves(checkers):
    """Мутация M-D8: `claim_window` → 0.

    Окно у ноги 5 не своё: она берёт существующий `claim_window`, и оправдание
    на соседней строке абзаца работает так же, как у ног 2 и 3. Пара: та же
    строка без соседа обязана краснеть.
    """
    text = ("Сегодня — 2026-09-10, и запись идёт этим же ходом,\n"
            "дата снята `date -u +%F` в этом же ходу.\n")
    assert marked(check(checkers, CLAIM, text), DATE_FORM) == []
    assert marked(check(checkers, CLAIM,
                        "Сегодня — 2026-09-10, и запись идёт этим же ходом,\n"),
                  DATE_FORM)


def test_a_line_judged_by_an_earlier_leg_is_not_dated_twice(checkers):
    """Ноги одного класса не называют один отказ дважды.

    Нога 5 строит своё множество пропуска из строк, на которых НАПЕЧАТАЛИ ноги
    2–4, но без `stop_lines`, которыми `judged` засеян.
    """
    text = "Все чекеры полосы зелёные, сегодня — 2026-09-10.\n"
    messages = check(checkers, CLAIM, text)
    assert len(messages) == 1
    assert marked(messages, COUNT_FORM)
    # Живой контроль: снять счётное притязание — и та же дата краснеет ногой 5.
    assert marked(check(checkers, CLAIM, "Чекеры полосы зелёные, сегодня — 2026-09-10.\n"),
                  DATE_FORM)


def test_the_date_leg_is_silent_on_a_count_predicate(checkers):
    """Обратное направление: счётное утверждение — предмет ноги 4."""
    text = "Все чекеры полосы зелёные.\n"
    assert marked(check(checkers, CLAIM, text), DATE_FORM) == []
    assert marked(check(checkers, CLAIM, text), COUNT_FORM)


def test_live_channel_slot_is_silent_on_the_date_form(checkers):
    """Разграничение с соседом измерением, а не доводом.

    У `live_channel_slot` триггер — носитель плюс предикативный глагол
    состояния в одной клаузе; «дата» в `carrier_nouns` не стоит, а дейксис
    глаголом состояния не является.
    """
    text = "Сегодня — 2026-09-10.\n"
    assert check(checkers, "live_channel_slot", text) == []
    assert marked(check(checkers, CLAIM, text), DATE_FORM)


def test_date_form_lists_live_in_the_manifest(manifest):
    """Мутация M-D5: списки — данные, а не код.

    Порог в дейксис не зашит, литерал вынесен ключом, окно у ноги не своё.
    """
    cfg = {c["name"]: c for c in manifest["checkers"]}[CLAIM]["config"]
    assert cfg["date_gap_words"] == 3
    assert cfg["date_literal_pattern"] == r"\b20\d{2}-\d{2}-\d{2}\b"
    assert any("сегодня" in p for p in cfg["date_deixis_patterns"])
    assert not any(any(ch.isdigit() for ch in p) for p in cfg["date_deixis_patterns"])
    assert not any("хвост" in p for p in cfg["date_source_patterns"])
    assert any("SOURCE_DATE_EPOCH" in p for p in cfg["date_source_patterns"])
    assert "date_window" not in cfg and cfg["claim_window"] == 1
