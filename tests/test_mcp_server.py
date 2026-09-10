"""Мост MCP: контракт трёх инструментов и запуск под клиентом.

Опора: единая очередь контура, позиция 2 (вольт, `02-synthesis/
target-state-and-roadmap-r2.md`, §6) — линтер как stdio-MCP-инструмент
оркестратора; CLAUDE.md, «Пути вольта — переменные окружения» и «Калибровка и
отказ чекера — на каждом прогоне»; несущий документ, слой 0, п. 5 (отказ
контролёра есть отказ хода).

Утверждения о рантайме исполняются рантаймом: «сервер поднимается», «инструмент
отвечает», «красный доходит до клиента» меряются настоящим stdio-транспортом —
процесс, JSON-RPC на stdin, ответы на stdout, — а не чтением исходника.
Статически меряется только статическое свойство файла (отсутствие пишущих
вызовов), тем же приёмом, что контракт имени job'а в tests/test_ci_contract.py.

Единица диспозиции — «на вызов инструмента» для прямых тестов и «на процесс
сервера» для транспортных.

`mcp` не пропускается через importorskip намеренно: пакет стоит в
requirements.txt, и его отсутствие есть сломанная среда, а не режим работы.
Молчаливый пропуск дал бы «не измерено» под видом зелёного (§11, R-VACUUM-007).
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import threading

import pytest
import yaml

import run
from linter import mcp_server
from linter.checkers import whitespace_diff
from mcp.server.mcpserver.exceptions import ToolError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "linter", "mcp_server.py")
GREEN_TURN_END = os.path.join(ROOT, "linter", "fixtures", "green", "turn_end.md")

# Черновик развилки без слота: та самая форма, ради которой мост и заводится —
# два названных владельцу варианта и ни одного поля слота трёх полей.
RED_DRAFT = ("# Ход\n\n1= завожу ветку сам\n2= жду владельца\n\n"
             "**Конец хода:** нужно слово владельца — принять разбор выше "
             "либо назвать расхождение.\n")
VARIANTS = "владельцу вынесено вариантов"
CLOSING = ("**Конец хода:** нужно слово владельца — принять разбор выше "
           "либо назвать расхождение.\n")

# Маркер отказа подменённого чекера: без него чекер упал бы и на собственной
# фикстуре, был бы дисквалифицирован калибровкой и до черновика не дошёл бы —
# путь checker_error на цели остался бы не измерен (приём tests/test_fail_closed.py).
TARGET = "МАРКЕР-ОТКАЗА"
REAL_WHITESPACE = whitespace_diff.check

PROTOCOL = "2026-07-28"


# ──────────────────────────── stdio-транспорт ────────────────────────────────

def rpc(id_: int, method: str, params: dict | None = None) -> dict:
    msg = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


HANDSHAKE = [
    rpc(1, "initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                          "clientInfo": {"name": "харнесс", "version": "0"}}),
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
]


def drive(messages, python=None, cwd=None, env=None, timeout=90, args=()):
    """Поднять сервер, отдать сообщения, собрать ответы по id.

    `args` — аргументы запуска сервера, ровно как в `args` записи клиента: пути
    вольта приходят ими (CLAUDE.md, «Мост MCP»), и меряться они обязаны на
    настоящей командной строке, а не подменой модульной переменной.

    stdin держится открытым, пока не пришли все ответы: EOF на stdin гасит
    незавершённые запросы, и ответ на tools/call просто не приходит (mcp 2.x:
    «Cancelled requests are no longer answered»). Ровно поэтому наивный
    `printf … | server` видит только два кадра из трёх.

    Висящий процесс убивается сторожевым таймером: тест обязан провалиться, а
    не висеть — прогон, висящий вместо ответа, есть отсутствие ответа, а не
    отличимый провал (§11, «Исполнимость shell-блока», (3)).
    """
    proc = subprocess.Popen(
        [python or sys.executable, "-u", SERVER, *args],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=cwd, env=env)
    watchdog = threading.Timer(timeout, proc.kill)
    watchdog.start()
    answers: dict[int, dict] = {}
    try:
        for message in messages:
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
        awaited = {m["id"] for m in messages if "id" in m}
        while awaited:
            line = proc.stdout.readline()
            if not line:
                break
            frame = json.loads(line)
            if frame.get("id") in awaited:
                answers[frame["id"]] = frame
                awaited.discard(frame["id"])
    finally:
        watchdog.cancel()
        try:
            proc.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        stderr = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
    return answers, proc.returncode, stderr


def call(id_: int, tool: str, arguments: dict | None = None) -> dict:
    return rpc(id_, "tools/call", {"name": tool, "arguments": arguments or {}})


def structured(answer: dict):
    result = answer["result"]
    return result.get("structuredContent") or result.get("structured_content")


def client_env() -> dict:
    """Окружение, измеренное у клиента 2026-09-08.

    Claude Desktop поднимает сервер через `wsl.exe -e …`: профиль не читается,
    а блок `env` записи достаётся процессу Windows и внутрь дистрибутива не
    переносится (замер владельца 2026-09-08, PowerShell: `wsl.exe -e printenv
    ALTREGO_VAULT_MASTER` — пусто, код 1; путь и код 0 только под
    `WSLENV=ALTREGO_VAULT_MASTER/u`). Переменных вольта здесь нет намеренно:
    так выглядит процесс сервера у клиента, и путь ему приходит аргументом.
    """
    return {"HOME": os.path.expanduser("~"),
            "USER": os.environ.get("USER", "dev"),
            "PATH": "/usr/bin:/bin"}


def test_stdio_handshake_lists_three_tools():
    answers, code, stderr = drive(HANDSHAKE + [rpc(2, "tools/list")])
    assert sorted(answers) == [1, 2], stderr
    names = [t["name"] for t in answers[2]["result"]["tools"]]
    assert sorted(names) == ["check_turn", "list_rules", "queue"]
    assert code == 0
    assert stderr.strip() == ""


def test_tools_publish_output_schema():
    """Форма ответа объявлена, а не только описана: клиент видит output_schema."""
    answers, _code, _err = drive(HANDSHAKE + [rpc(2, "tools/list")])
    tools = {t["name"]: t for t in answers[2]["result"]["tools"]}
    schema = tools["check_turn"].get("outputSchema") or tools["check_turn"]["output_schema"]
    assert {"passed", "findings", "not_measured", "infra"} <= set(schema["properties"])


def test_stdio_red_draft_is_red_through_the_transport():
    """Красный доходит до клиента целиком: находка, чекер, строка, passed=false."""
    answers, _code, stderr = drive(
        HANDSHAKE + [call(2, "check_turn", {"text": RED_DRAFT})])
    assert 2 in answers, stderr
    assert answers[2]["result"].get("isError") in (False, None)
    verdict = structured(answers[2])
    assert verdict["passed"] is False
    assert [(f["checker"], f["line"]) for f in verdict["findings"]] == [("turn_end", 3)]
    assert VARIANTS in verdict["findings"][0]["message"]


def test_stdio_from_foreign_cwd_without_env(tmp_path):
    """Измеренная среда клиента: чужой cwd, профиль не прочитан, вольта нет.

    Здесь меряется независимость от cwd: зелёный черновик проходит, потому что
    все пути сервера абсолютные, а `queue` при неадресованном вольте отказывает,
    а не молчит. Текст самого отказа — предмет
    `test_neither_channel_is_the_typed_refusal_naming_both` ниже.
    """
    green = open(GREEN_TURN_END, encoding="utf-8").read()
    env = client_env()
    assert run.ENV_MASTER not in env and run.ENV_CLONE not in env
    answers, code, stderr = drive(
        HANDSHAKE + [call(2, "check_turn", {"text": green}), call(3, "queue")],
        cwd=str(tmp_path), env=env)
    assert sorted(answers) == [1, 2, 3], stderr
    assert structured(answers[2])["passed"] is True
    assert answers[3]["result"]["isError"] is True
    assert "vault_env_unset" in answers[3]["result"]["content"][0]["text"]
    assert code == 0


def test_three_concurrent_starts_all_answer():
    """Клиент поднимает сервер по нескольку раз в секунду — все процессы живы.

    Стартовых эффектов нет: ни файла блокировки, ни общего состояния, поэтому
    три одновременных процесса отвечают все три, а не один.
    """
    results: list[tuple[int, dict]] = []
    lock = threading.Lock()

    def one(n: int) -> None:
        answers, _code, _err = drive(HANDSHAKE + [rpc(2, "tools/list")])
        with lock:
            results.append((n, answers))

    threads = [threading.Thread(target=one, args=(n,)) for n in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert len(results) == 3
    for _n, answers in results:
        assert sorted(answers) == [1, 2]
        assert len(answers[2]["result"]["tools"]) == 3


def test_reexec_under_a_foreign_interpreter():
    """Запасной путь: чужой интерпретатор без зависимостей перезапускается под .venv.

    Основной путь записи клиента — `.venv/bin/python` (CLAUDE.md, «Мост MCP»);
    гард держит случай, когда в записи стоит системный python, у которого
    зависимостей нет.
    """
    foreign = "/usr/bin/python3"
    if not os.path.isfile(foreign):
        pytest.skip("системного /usr/bin/python3 нет")
    probe = subprocess.run([foreign, "-c", "import importlib.util as u;"
                            "print(u.find_spec('mcp') is not None)"],
                           capture_output=True, text=True)
    if probe.stdout.strip() != "False":
        pytest.skip("у системного интерпретатора зависимости есть — "
                    "запасной путь этим прогоном не измеряется")
    answers, code, stderr = drive(HANDSHAKE + [rpc(2, "tools/list")],
                                  python=foreign, cwd="/", env=client_env())
    assert sorted(answers) == [1, 2], stderr
    assert len(answers[2]["result"]["tools"]) == 3
    assert code == 0


def fake_root(tmp_path, venv_python: str | None) -> str:
    """Копия сервера в чужом корне: `.venv` там либо нет, либо она негодная.

    Настоящую `.venv` репозитория трогать нельзя — она и есть рабочий
    интерпретатор полосы; оба состояния гарда моделируются копией.
    """
    root = tmp_path / "корень"
    (root / "linter").mkdir(parents=True)
    (root / "linter" / "mcp_server.py").write_bytes(open(SERVER, "rb").read())
    if venv_python is not None:
        (root / ".venv" / "bin").mkdir(parents=True)
        os.symlink(venv_python, root / ".venv" / "bin" / "python")
    return str(root / "linter" / "mcp_server.py")


def foreign_python() -> str:
    foreign = "/usr/bin/python3"
    if not os.path.isfile(foreign):
        pytest.skip("системного /usr/bin/python3 нет")
    probe = subprocess.run([foreign, "-c", "import importlib.util as u;"
                            "print(u.find_spec('mcp') is not None)"],
                           capture_output=True, text=True)
    if probe.stdout.strip() != "False":
        pytest.skip("у системного интерпретатора зависимости есть — "
                    "запасной путь этим прогоном не измеряется")
    return foreign


def test_refusal_without_a_venv_is_exit_two_and_says_what_is_missing(tmp_path):
    """Другая половина запасного пути: перезапускаться не подо что — назвать это.

    Молчаливый старт без зависимостей дал бы клиенту сервер, который не
    отвечает: отказ, неотличимый от отсутствия. Меряется процессом, а не
    чтением исходника.
    """
    server = fake_root(tmp_path, venv_python=None)
    done = subprocess.run([foreign_python(), "-u", server], input="",
                          capture_output=True, text=True, timeout=60,
                          cwd="/", env=client_env())
    assert done.returncode == 2
    assert "mcp" in done.stderr and "python3 -m venv" in done.stderr
    assert done.stdout == ""


def test_guard_restarts_at_most_once(tmp_path):
    """Негодная `.venv` даёт ОТКАЗ, а не вечный цикл перезапусков.

    `.venv` без `pyvenv.cfg` — обычная поломка (скопировали каталог, потеряли
    файл): её `sys.prefix` равен системному, и гард, ограниченный сравнением
    префиксов, перезапускал бы себя вечно. Клиент получил бы молча крутящийся
    процесс — отсутствие ответа, а не отличимый провал. Ограничение — метка
    в окружении; тест меряет именно его, на живом процессе и с таймаутом.
    """
    foreign = foreign_python()
    server = fake_root(tmp_path, venv_python=foreign)   # симлинк без pyvenv.cfg
    done = subprocess.run([foreign, "-u", server], input="",
                          capture_output=True, text=True, timeout=60,
                          cwd="/", env=client_env())
    assert done.returncode == 2
    assert mcp_server.REEXEC_MARK not in os.environ
    assert "после перезапуска" in done.stderr
    assert done.stdout == ""


# ─────────────────── пути вольта: аргумент и окружение ───────────────────────
#
# Замер владельца 2026-09-08 (PowerShell, оба направления, коды выхода
# записаны): блок `env` записи сервера достаётся ПРОЦЕССУ WINDOWS `wsl.exe` и
# внутрь дистрибутива не переносится — `wsl.exe -e printenv
# ALTREGO_VAULT_MASTER` печатал пусто кодом 1 и печатал путь кодом 0 только
# после `WSLENV=ALTREGO_VAULT_MASTER/u`. Отсюда канал путей — аргумент запуска,
# окружение остаётся вторым. Меряются оба канала и их ПОРЯДОК, и меряются
# настоящей командной строкой процесса: подмена модульной переменной измерила бы
# разрешение, но не разбор argv, то есть не ту дверь, в которую входит клиент.
#
# Единица диспозиции — «на процесс сервера».

def fake_master(tmp_path, name: str, marker: str) -> str:
    """Каталог, изображающий рабочую копию вольта: файл очереди по конфигу репо.

    Путь файла и признаки разбора берутся из настоящего `config.yaml` — тест
    меряет ту же дверь, что клиент, а не свою копию её формы. Вольт владельца
    здесь не читается ни в каком виде (CLAUDE.md, «в вольт не писать»).

    `marker` печатается в текст пункта: два каталога обязаны быть различимы в
    выдаче, иначе «сработал аргумент» неотличимо от «сработало окружение».
    """
    config = run.load_config()
    root = os.path.join(str(tmp_path), name)
    path = os.path.join(root, config["queue"]["file"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("**Единая очередь контура на 2026-09-08.** Порядок:\n\n"
                 f"1. **{marker}** — голова.\n")
    return root


def test_vault_argument_wins_over_a_different_env_value(tmp_path):
    """Порядок каналов измерен, а не предположен: аргумент бьёт переменную.

    Каналы адресуют РАЗНЫЕ каталоги, и по тексту головы видно, какой сработал.
    Совпадающие пути порядка не измерили бы вовсе.
    """
    chosen = fake_master(tmp_path, "по-аргументу", "ГОЛОВА ПО АРГУМЕНТУ")
    other = fake_master(tmp_path, "по-окружению", "ГОЛОВА ПО ОКРУЖЕНИЮ")
    answers, code, stderr = drive(
        HANDSHAKE + [call(2, "queue")], cwd="/",
        env={**client_env(), run.ENV_MASTER: other},
        args=["--vault-master", chosen])
    assert 2 in answers, stderr
    assert answers[2]["result"].get("isError") in (False, None)
    got = structured(answers[2])
    assert got["head"]["text"].startswith("**ГОЛОВА ПО АРГУМЕНТУ**")
    assert got["source"].startswith(chosen) and not got["source"].startswith(other)
    assert code == 0


def test_vault_argument_alone_without_any_env(tmp_path):
    """Аргумент один, переменных вольта нет вовсе — очередь читается.

    Это и есть измеренная связка клиента: через `wsl.exe` до процесса доходит
    командная строка, а блок `env` — нет. `--vault-clone` подаётся здесь же:
    его не читает пока ни один инструмент, но запись клиента несёт оба флага, и
    «принимается» обязано быть измерено, а не подразумеваться.
    """
    master = fake_master(tmp_path, "только-аргумент", "ГОЛОВА БЕЗ ОКРУЖЕНИЯ")
    env = client_env()
    assert run.ENV_MASTER not in env and run.ENV_CLONE not in env
    answers, code, stderr = drive(
        HANDSHAKE + [call(2, "queue")], cwd="/", env=env,
        args=["--vault-master", master,
              "--vault-clone", os.path.join(str(tmp_path), "клон")])
    assert 2 in answers, stderr
    assert answers[2]["result"].get("isError") in (False, None)
    assert structured(answers[2])["head"]["text"].startswith("**ГОЛОВА БЕЗ ОКРУЖЕНИЯ**")
    assert code == 0


def test_env_alone_still_works_without_the_argument(tmp_path):
    """Второй канал жив: там, где переменная доходит, её одной достаточно.

    Речь не о прежней записи клиента — она пути и не доносила, потому и
    меняется. Речь о запуске из WSL руками, харнессе и CI: там переменная до
    процесса доходит, и аргумент, отменивший бы её, сломал бы эти три связки.
    """
    master = fake_master(tmp_path, "только-окружение", "ГОЛОВА ПО ОКРУЖЕНИЮ")
    answers, code, stderr = drive(
        HANDSHAKE + [call(2, "queue")], cwd="/",
        env={**client_env(), run.ENV_MASTER: master})
    assert 2 in answers, stderr
    assert answers[2]["result"].get("isError") in (False, None)
    assert structured(answers[2])["head"]["text"].startswith("**ГОЛОВА ПО ОКРУЖЕНИЮ**")
    assert code == 0


def test_neither_channel_is_the_typed_refusal_naming_both(tmp_path):
    """Ни аргумента, ни переменной — названный отказ, называющий ОБА канала.

    Отказ, называющий один канал, отправил бы владельца чинить не ту дверь:
    прежний текст велел задать переменную в блоке `env`, а именно он до сервера
    и не доходит. Лечение обязано быть исполнимым в том состоянии, в котором
    печатается.
    """
    answers, code, stderr = drive(HANDSHAKE + [call(2, "queue")],
                                  cwd="/", env=client_env())
    assert 2 in answers, stderr
    assert answers[2]["result"]["isError"] is True
    text = answers[2]["result"]["content"][0]["text"]
    assert "vault_env_unset" in text
    assert "--vault-master" in text and run.ENV_MASTER in text
    assert code == 0


def test_reexec_preserves_the_vault_arguments(tmp_path):
    """Перезапуск под `.venv` несёт аргументы дальше: путь на гарде не теряется.

    Гард — запасной путь чужого интерпретатора, и он `execv`-ит файл заново.
    Аргумент, потерянный там, дал бы `vault_env_unset` при верно заданном
    пути — отказ на месте рабочей связки, причём только на этой ветке запуска.
    """
    foreign = foreign_python()
    master = fake_master(tmp_path, "через-перезапуск", "ГОЛОВА ЧЕРЕЗ ПЕРЕЗАПУСК")
    answers, code, stderr = drive(HANDSHAKE + [call(2, "queue")],
                                  python=foreign, cwd="/", env=client_env(),
                                  args=["--vault-master", master])
    assert 2 in answers, stderr
    assert answers[2]["result"].get("isError") in (False, None)
    got = structured(answers[2])
    assert got["head"]["text"].startswith("**ГОЛОВА ЧЕРЕЗ ПЕРЕЗАПУСК**")
    assert got["source"].startswith(master)
    assert code == 0


def test_unknown_argument_exits_readably_and_keeps_stdout_clean():
    """Неизвестный аргумент — читаемый отказ в stderr, а не трассировка в stdout.

    stdout здесь канал JSON-RPC: любая строка там — сломанный кадр, а не
    сообщение. Клиент, получивший трассировку кадром, увидел бы поломку
    протокола вместо названной причины.
    """
    done = subprocess.run([sys.executable, "-u", SERVER, "--нет-такого-флага"],
                          input="", capture_output=True, text=True, timeout=60,
                          cwd="/", env=client_env())
    assert done.returncode == 2
    assert done.stdout == ""
    assert "--нет-такого-флага" in done.stderr
    assert "Traceback" not in done.stderr


def test_help_goes_to_stderr_and_not_into_the_protocol_channel():
    """Вторая дверь argparse: справка. Она обязана уйти в stderr, как и отказ.

    Отказ argparse печатает в stderr и без правки, а справку — в stdout: снятый
    `ArgParser` тест на неизвестном аргументе не заметил бы вовсе (измерено
    мутацией 2026-09-08: удаление гарда не покраснило ни одного теста). Гард,
    который не умеет краснеть, — не гард, поэтому его предмет меряется здесь.
    """
    done = subprocess.run([sys.executable, "-u", SERVER, "--help"],
                          input="", capture_output=True, text=True, timeout=60,
                          cwd="/", env=client_env())
    assert done.stdout == ""
    assert "--vault-master" in done.stderr and "--vault-clone" in done.stderr


def test_clone_argument_resolves_by_the_same_order(monkeypatch):
    """Обе двери разрешаются одинаково, и пустое значение равно незаданному.

    Клон не читает пока ни один инструмент — тем важнее измерить разрешение
    прямо: незамеренный флаг «принимается» ровно до первого раза, когда он
    кому-то понадобится. Пустая строка отбрасывается как пустая переменная в
    `run.env_path`: иначе `--vault-master ""` дал бы относительный путь от cwd
    клиента.
    """
    parsed = mcp_server.parse_args(["--vault-clone", "  /клон  ",
                                    "--vault-master", "   "])
    assert parsed == {run.ENV_CLONE: "/клон"}
    monkeypatch.setattr(mcp_server, "CLI_VAULT", parsed)
    monkeypatch.setenv(run.ENV_CLONE, "/клон-из-окружения")
    monkeypatch.setenv(run.ENV_MASTER, "/мастер-из-окружения")
    assert mcp_server.vault_path(run.ENV_CLONE) == "/клон"
    assert mcp_server.vault_path(run.ENV_MASTER) == "/мастер-из-окружения"
    monkeypatch.delenv(run.ENV_MASTER)
    assert mcp_server.vault_path(run.ENV_MASTER) is None


# ─────────────────────────────── check_turn ──────────────────────────────────

def test_check_turn_red_draft_names_the_missing_slot():
    verdict = mcp_server.check_turn(RED_DRAFT)
    assert verdict["passed"] is False and verdict["verdict"] == "КРАСНЫЙ"
    assert len(verdict["findings"]) == 1
    finding = verdict["findings"][0]
    assert (finding["checker"], finding["line"], finding["severity"]) == ("turn_end", 3, "red")
    assert VARIANTS in finding["message"]
    assert verdict["not_measured"] == [] and verdict["infra"] == []
    assert verdict["calibration_reds"] == []


def test_check_turn_green_fixture_text_passes():
    verdict = mcp_server.check_turn(open(GREEN_TURN_END, encoding="utf-8").read())
    assert (verdict["passed"], verdict["findings"]) == (True, [])
    assert len(verdict["checkers"]) == 17 and verdict["checkers_skipped"] == []


def test_check_turn_kind_spec_skips_handoff_only_checkers():
    verdict = mcp_server.check_turn(RED_DRAFT, kind="spec")
    assert "turn_end" in verdict["checkers_skipped"]
    assert (len(verdict["checkers"]), len(verdict["checkers_skipped"])) == (7, 10)
    assert verdict["kind"] == "spec"


def test_check_turn_unknown_kind_is_a_refusal():
    """Неизвестный вид отбирает ноль чекеров: это отказ, а не зелёный прогон."""
    with pytest.raises(ToolError) as exc:
        mcp_server.check_turn(RED_DRAFT, kind="нет-такого")
    assert "kind" in str(exc.value)


def test_check_turn_non_string_text_is_a_refusal():
    with pytest.raises(ToolError):
        mcp_server.check_turn(None)


def test_check_turn_checker_error_fails_closed(monkeypatch):
    """Отказ чекера на черновике: passed ложно, отказ назван, чекер не измерен."""
    def explodes(text, config):
        if TARGET in text:
            raise RuntimeError("подменённый чекер отказал")
        return REAL_WHITESPACE(text, config)

    monkeypatch.setattr(whitespace_diff, "check", explodes)
    verdict = mcp_server.check_turn(RED_DRAFT + f"\n<!-- {TARGET} -->\n")
    assert verdict["passed"] is False
    statuses = {row["status"] for row in verdict["infra"]}
    assert run.CHECKER_ERROR in statuses
    assert any(row["check"] == "whitespace_diff" for row in verdict["infra"])
    assert "whitespace_diff" in {row["checker"] for row in verdict["not_measured"]}


def test_check_turn_disqualified_checker_is_not_measured(monkeypatch):
    """Дисквалифицированный калибровкой чекер не голосует нулём находок."""
    real = run.calibrate

    def limping(checkers, fixtures_dir, limit):
        out = real(checkers, fixtures_dir, limit)
        out["disqualified"] = {"turn_end": "red-fixture-silent"}
        out["reds"] = list(out["reds"]) + ["turn_end: не покраснел на своей red-фикстуре"]
        return out

    monkeypatch.setattr(run, "calibrate", limping)
    verdict = mcp_server.check_turn(RED_DRAFT)
    assert verdict["passed"] is False
    assert verdict["findings"] == []          # чекер не запускался вовсе
    reasons = {row["checker"]: row["reason"] for row in verdict["not_measured"]}
    assert "turn_end" in reasons and "калибровка" in reasons["turn_end"]
    assert verdict["calibration_reds"]


def test_check_turn_import_failure_is_infra(monkeypatch):
    """Неимпортированный чекер — отказ опоры, а не молчание: passed ложно."""
    real = run.load_checkers

    def broken(manifest, kind):
        active, skipped, failed = real(manifest, kind)
        return active, skipped, failed + [{"name": "выдуманный",
                                           "module": "linter.checkers.нет",
                                           "exc_type": "ModuleNotFoundError",
                                           "message": "нет модуля"}]

    monkeypatch.setattr(run, "load_checkers", broken)
    verdict = mcp_server.check_turn(open(GREEN_TURN_END, encoding="utf-8").read())
    assert verdict["passed"] is False
    assert any(row["status"] == run.CHECKER_IMPORT_ERROR for row in verdict["infra"])


def test_check_turn_writes_no_files(monkeypatch, vault_pair):
    """Инструмент отчётов не пишет: reports/ остаётся пустым после вызова."""
    config = vault_pair.config()
    monkeypatch.setattr(run, "load_config", lambda: config)
    mcp_server.check_turn(RED_DRAFT)
    assert os.listdir(vault_pair.reports) == []


def test_module_imports_nothing_that_writes():
    """Поверхность записи закрыта белым списком импортов, а не чёрным — вызовов.

    Чёрный список молча пропускает то, чего в нём нет: `shutil.copy`,
    `os.replace`, `Path.write_bytes` — и гард с именем «пишущих вызовов нет»
    зеленел бы на модуле, который пишет. Белый список импортов закрывает класс:
    без `shutil`, `tempfile`, `pathlib`, `subprocess` и `io` писать остаётся
    нечем, кроме `open` и `os.*`, а их и меряет тест ниже.

    `argparse` в списке — разбор путей вольта из командной строки. Своей двери
    записи он не открывает: единственная — `argparse.FileType`, и она стоит в
    перечне пишущих ниже.
    """
    tree = ast.parse(open(SERVER, encoding="utf-8").read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"__future__", "argparse", "importlib.util", "os", "re",
                        "sys", "typing", "run", "mcp.server",
                        "mcp.server.mcpserver.exceptions"}, sorted(imported)


def test_module_has_no_writing_calls():
    """Ни одного пишущего вызова: `open` только на чтение, `os.*` — только не пишущие.

    Клиент поднимает сервер по нескольку раз в секунду; пишущий старт сделал бы
    из этого гонку. Свойство статическое — меряется статически, тем же приёмом,
    что контракт имени job'а в tests/test_ci_contract.py.
    """
    tree = ast.parse(open(SERVER, encoding="utf-8").read())
    writers = {"makedirs", "mkdir", "remove", "unlink", "rmdir", "rmtree",
               "rename", "replace", "truncate", "symlink", "link", "chmod",
               "chown", "utime", "write", "writelines", "write_text",
               "write_bytes", "touch", "copy", "copy2", "copyfile", "move",
               "mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile",
               "FileType"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.attr if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", ""))
        if name in ("write", "writelines"):
            # Запись в stderr — не файловый эффект: это единственный канал, по
            # которому отказ опоры доходит до клиента (stdout занят протоколом).
            target = ast.unparse(node.func.value) if isinstance(node.func, ast.Attribute) else ""
            assert target == "sys.stderr", ast.dump(node)
            continue
        assert name not in writers, ast.dump(node)
        if name == "open":
            modes = [a.value for a in node.args[1:2] if isinstance(a, ast.Constant)]
            assert modes and modes[0] == "r", ast.dump(node)


def test_no_hardcoded_vault_fallback_in_the_bridge():
    """У моста отката нет ни константой, ни литералом пути в коде.

    Тот же гард, что `tests/test_vault_env.py::test_no_hardcoded_vault_fallback`
    держит на `run.py`, — и заведён он потому, что дверей путей вольта стало
    две: к переменной добавился аргумент запуска. Пока литерала нет, гард
    ничего не меняет; его предмет — чтобы он не появился незаметно, когда
    очередной отказ `vault_env_unset` захочется «починить» умолчанием. Умолчание
    опаснее его отсутствия: прогон на чужой машине читал бы посторонний каталог,
    и «вольт не адресован» стало бы неотличимо от «вольт прочитан».

    Меряется двумя слоями. Текстовый закрывает машину владельца целиком, включая
    комментарии: её каталогов в репозитории нет ни в каком виде. Слой AST
    закрывает класс шире — абсолютный путь литералом В КОДЕ, — и намеренно не
    трогает докстринги: измеренный cwd клиента (`/mnt/c/…`) в прозе назван, и
    назван по делу. За литералами гард не идёт: откат через переменную-константу
    он не увидит, и это его граница, а не молчание о ней.
    """
    assert not hasattr(mcp_server, "DEFAULT_MASTER")
    assert not hasattr(mcp_server, "DEFAULT_CLONE")

    source = open(SERVER, encoding="utf-8").read()
    assert "vaults/" not in source
    assert "Obsidian" not in source

    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or id(node) in docstrings:
            continue
        if not isinstance(node.value, str):
            continue
        assert not node.value.startswith(("/", "~")), (node.lineno, node.value)


def test_draft_label_does_not_borrow_the_client_cwd(monkeypatch, tmp_path):
    """Свидетельство отказа называет предмет, а не каталог запуска клиента.

    `run.run_checker` зовёт `repo_rel` на пути артефакта. Относительная метка
    стала бы там путём от cwd — у клиента это `/mnt/c/Windows/system32`, каталог
    чужой машины, которого в WSL нет. Владелец лечит прогон по этой строке.
    """
    def explodes(text, config):
        if TARGET in text:
            raise RuntimeError("подложный отказ")
        return REAL_WHITESPACE(text, config)

    monkeypatch.setattr(whitespace_diff, "check", explodes)
    monkeypatch.chdir(tmp_path)                    # cwd вне репозитория
    verdict = mcp_server.check_turn(RED_DRAFT + f"\n<!-- {TARGET} -->\n")
    row = next(r for r in verdict["infra"] if r["check"] == "whitespace_diff")
    assert "<черновик>" in row["message"]
    assert str(tmp_path) not in row["message"]


def test_ignore_without_reason_is_failing(monkeypatch):
    """Изъятие без причины — severity error: оно валит вердикт наравне с красным.

    Молчаливое изъятие неотличимо от отсутствия предмета, и мост обязан читать
    его так же, как прогон (`run.FAILING` — red и error).
    """
    draft = ("# Ход\n\n<!-- lint:ignore turn_end -->\n1= путь А\n2= путь Б\n\n"
             + CLOSING)
    verdict = mcp_server.check_turn(draft)
    assert verdict["passed"] is False
    assert any(f["severity"] == "error" and f["checker"] == "ignore_without_reason"
               for f in verdict["findings"])
    with_reason = draft.replace("lint:ignore turn_end -->",
                                "lint:ignore turn_end — форма ответа владельца -->")
    kept = mcp_server.check_turn(with_reason)
    assert (kept["passed"], kept["ignores_applied"]) == (True, 1)


# ─────────────────────────────── list_rules ──────────────────────────────────

def test_list_rules_matches_the_registry():
    listed = mcp_server.list_rules()
    registry = yaml.safe_load(open(os.path.join(ROOT, "rules", "registry.yaml"),
                                   encoding="utf-8"))
    assert listed["count"] == len(registry["rules"])
    assert [r["rule_id"] for r in listed["rules"]] == \
           [r["rule_id"] for r in registry["rules"]]
    assert listed["computed_at"] == registry["computed_at"]
    first = listed["rules"][0]
    assert first["content_hash"] == registry["rules"][0]["content_hash"]
    assert first["heading"] == registry["rules"][0]["source"]["heading"]


def test_list_rules_touches_no_vault(monkeypatch):
    """Хэши отдаются из реестра: ни git-вызова, ни пересчёта по вольту."""
    def boom(*args, **kwargs):
        raise AssertionError("list_rules полез в вольт")

    from linter import canon
    monkeypatch.setattr(run, "_git", boom)
    monkeypatch.setattr(canon, "hash_rule", boom)
    assert mcp_server.list_rules()["count"] == 20


# ───────────────────────────────── queue ─────────────────────────────────────

ROADMAP = "02-synthesis/roadmap.md"

QUEUE_TEXT = """# Роадмап (синтетический)

## §6

**Единая очередь контура на 2026-09-07 (owner-акт `8=да`).** Порядок:

1. **`turn_end`** (B) — **закрыт 2026-09-08**, merge PR #4 в `main`.
2. **Мост MCP** (C) — `run.py` за stdio-MCP; предел: связь мягкая.
   Продолжение пункта: не раньше закрытия B — слово «закрыт» здесь без жирного.

3. **B-P2b** (B) — шесть shell/env-форм; средний.

Критерий выхода B остаётся и достигается пакетами 1 и 3.

### Дорожка Control

4. Это уже не очередь: список за границей раздела.
"""


def queue_config(pair) -> dict:
    config = pair.config()
    config["queue"] = {"file": ROADMAP,
                       "heading_pattern": r"^\*\*Единая очередь контура",
                       "closed_pattern": r"\*\*закрыт"}
    return config


def write_roadmap(pair, text: str = QUEUE_TEXT) -> str:
    path = os.path.join(pair.master, ROADMAP)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_queue_head_is_the_first_open_item(monkeypatch, vault_pair):
    """Голова — первый пункт без признака закрытия, а не первый пункт списка."""
    path = write_roadmap(vault_pair)
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    got = mcp_server.queue()
    assert got["source"] == path
    assert got["as_of"] == "2026-09-07"
    assert [(i["position"], i["closed"]) for i in got["items"]] == \
           [(1, True), (2, False), (3, False)]
    assert got["head"]["position"] == 2
    # Продолжение пункта склеено: строка без своего номера принадлежит пункту…
    assert "Продолжение пункта" in got["items"][1]["text"]
    # …и «закрыт» без жирного признаком закрытия не является.
    assert got["items"][1]["closed"] is False
    # Пустая строка внутри списка его не обрывает, а заголовок — обрывает.
    assert all(i["position"] != 4 for i in got["items"])


def test_queue_env_unset_is_a_named_refusal(monkeypatch, vault_pair):
    """Вольт не адресован — назван отказ с лечением, а не умолчание на чей-то каталог.

    Лечение называет оба канала и не велит чинить тот, который до сервера не
    доходит: блок `env` записи клиента остаётся у процесса Windows (измерено
    2026-09-08), и текст, посылающий владельца туда, был бы неисполнимым.
    """
    write_roadmap(vault_pair)
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    monkeypatch.setattr(mcp_server, "CLI_VAULT", {})
    monkeypatch.delenv(run.ENV_MASTER, raising=False)
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    message = str(exc.value)
    assert "vault_env_unset" in message and run.ENV_MASTER in message
    assert mcp_server.VAULT_OPTIONS[run.ENV_MASTER] in message
    assert "`args` записи сервера" in message


def test_queue_missing_file_names_the_absolute_path(monkeypatch, vault_pair):
    config = queue_config(vault_pair)
    config["queue"]["file"] = "02-synthesis/нет-такого.md"
    monkeypatch.setattr(run, "load_config", lambda: config)
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    assert os.path.join(vault_pair.master, "02-synthesis/нет-такого.md") in str(exc.value)


def test_queue_without_config_block_is_a_refusal(monkeypatch, vault_pair):
    """Снятая данная — отказ инструмента, а не чтение по умолчанию в коде.

    Тот же довод, что у `turn_end.ConfigDefect`: «ключа нет» обязано быть
    отличимо от «значение не встретилось».
    """
    write_roadmap(vault_pair)
    monkeypatch.setattr(run, "load_config", lambda: vault_pair.config())
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    assert "config_missing_key" in str(exc.value) and "queue.file" in str(exc.value)


def test_queue_heading_not_found_is_a_refusal(monkeypatch, vault_pair):
    """Форма раздела сменилась — отказ, а не пустая очередь."""
    write_roadmap(vault_pair, "# Роадмап\n\nРаздела очереди здесь нет.\n")
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    assert "queue_heading_not_found" in str(exc.value)


def test_queue_prose_instead_of_items_is_a_refusal(monkeypatch, vault_pair):
    """За зачином нет пункта — отказ, а не поиск списка дальше по файлу."""
    write_roadmap(vault_pair,
                  "**Единая очередь контура на 2026-09-07.** Порядок:\n\nПрозой.\n")
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    assert "queue_items_not_after_heading" in str(exc.value)


def test_queue_does_not_adopt_a_foreign_numbered_list(monkeypatch, vault_pair):
    """Проза между зачином и списком не пропускается: чужой список — не очередь.

    Прежний разбор перепрыгивал любую прозу и латался на первый попавшийся
    нумерованный список ниже — молча, с `isError=false`. Владелец получил бы
    ЧУЖОЙ список под именем очереди контура: не «очередь не найдена», а
    неверная очередь, что хуже отказа.
    """
    write_roadmap(vault_pair,
                  "**Единая очередь контура на 2026-09-07.** Порядок:\n\n"
                  "Раздел переписывается, список временно ниже.\n\n"
                  "## Открытые вопросы\n\n"
                  "1. Вопрос владельцу — это не пункт очереди.\n"
                  "2. И этот тоже.\n")
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    assert "queue_items_not_after_heading" in str(exc.value)


def test_queue_survives_an_indented_sublist(monkeypatch, vault_pair):
    """Разрежённый список с подпунктом не обрывает очередь на подпункте.

    Пустая строка перед строкой с отступом — форма обычного markdown-списка.
    Обрыв на ней срезал бы хвост очереди молча: голова стала бы `None` при
    живых пунктах ниже, и «очередь кончилась» было бы неотличимо от «разбор
    не дочитал».
    """
    write_roadmap(vault_pair,
                  "**Единая очередь контура на 2026-09-08.** Порядок:\n\n"
                  "1. **`turn_end`** — **закрыт 2026-09-08**.\n\n"
                  "   - предпосылка: гейт зелёный\n"
                  "   - цена: раунд владельца\n\n"
                  "2. **Мост MCP** — голова очереди.\n\n"
                  "3. **B-P2b** — следующий.\n\n"
                  "Критерий выхода B остаётся.\n")
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    got = mcp_server.queue()
    assert [i["position"] for i in got["items"]] == [1, 2, 3]
    assert got["head"]["position"] == 2
    assert "предпосылка: гейт зелёный" in got["items"][0]["text"]


def test_queue_heading_may_wrap_onto_several_lines(monkeypatch, vault_pair):
    """Зачин — абзац, а не строка: перенос не превращает его хвост в прозу."""
    write_roadmap(vault_pair,
                  "**Единая очередь контура на 2026-09-08 (owner-акт),**\n"
                  "заменяет очередь B; ранжируется по цене задержки.\n\n"
                  "1. **Мост MCP** — голова.\n")
    monkeypatch.setattr(run, "load_config", lambda: queue_config(vault_pair))
    got = mcp_server.queue()
    assert got["head"]["position"] == 1
    assert "заменяет очередь B" in got["heading"]
    assert got["as_of"] == "2026-09-08"


def test_queue_broken_pattern_is_a_typed_refusal(monkeypatch, vault_pair):
    """Битый регэксп данной — названный отказ с ключом, а не голое `re.error`.

    Клиент иначе видит «Error executing tool queue»: отказ есть, лечить негде.
    """
    write_roadmap(vault_pair)
    config = queue_config(vault_pair)
    config["queue"]["heading_pattern"] = r"^\*\*Единая очередь контура ("
    monkeypatch.setattr(run, "load_config", lambda: config)
    with pytest.raises(ToolError) as exc:
        mcp_server.queue()
    message = str(exc.value)
    assert "config_invalid_pattern" in message and "queue.heading_pattern" in message


def test_queue_position_comes_from_the_number_not_the_order():
    """Позиция берётся из номера владельца: перенумерация не сдвигает голову молча."""
    text = ("**Единая очередь контура на 2026-09-08.**\n\n"
            "2. **Мост MCP** — голова.\n"
            "3. **B-P2b** — следующий.\n")
    parsed = mcp_server.parse_queue(text, r"^\*\*Единая очередь контура", r"\*\*закрыт")
    assert [i["position"] for i in parsed["items"]] == [2, 3]
    assert parsed["head"]["position"] == 2


def test_queue_all_items_closed_gives_no_head():
    """Все пункты закрыты — головы нет, и это `None`, а не первый пункт."""
    text = ("**Единая очередь контура на 2026-09-08.**\n\n"
            "1. **A** — **закрыт 2026-09-01**.\n"
            "2. **B** — **закрыт 2026-09-08**.\n")
    parsed = mcp_server.parse_queue(text, r"^\*\*Единая очередь контура", r"\*\*закрыт")
    assert parsed["head"] is None and len(parsed["items"]) == 2


def test_queue_reads_the_real_roadmap_if_the_vault_is_addressed():
    """Живой вольт: если он адресован, инструмент читает настоящий раздел.

    Вольт только читается. Переменной нет (гейт CI) — тест не измеряет, и это
    названо пропуском, а не зелёным.
    """
    master = run.env_path(run.ENV_MASTER)
    if not master:
        pytest.skip(f"{run.ENV_MASTER} не задана — живой вольт не адресован")
    config = run.load_config()
    path = os.path.join(os.path.expanduser(master), config["queue"]["file"])
    if not os.path.isfile(path):
        pytest.skip(f"{path} недоступен")
    got = mcp_server.queue()
    assert got["items"] and got["head"] is not None
    assert got["items"][0]["position"] == 1
