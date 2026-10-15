# C0 / Altrego: итог эксперимента

Эксперимент выполнен: пять заранее выбранных задач, десять независимых попыток и десять первых внешних оценок. Полный проход — **1/5 задач в каждой ветви**. Рост проходимости Altrego A на этой выборке не наблюдался; время CLI и reported input tokens были выше. Экономия активного времени владельца не установлена: все шесть актов подписи явно отмечены «не измерено».

Это готовый результат для приёмки, **не owner acceptance и не закрытый merge**. Push, merge, публикация, применение предложений vault и начало M1 не выполнялись. Частичные сервисы остаются частичными.

## Замороженная рамка

Сравнивались Codex CLI без Altrego и тот же CLI с полным применимым процессом Altrego A: реальная подпись неизменного брифа, read-only Spec/plan, scope review, реальная подпись документации/Build, исполнение и отчёт. Общий контроллер не реализовывал сервисы и не передавал решения/результаты между контекстами.

Источник — [Microsoft DKI_LLM / RepoGenesis](https://github.com/microsoft/DKI_LLM/tree/c090b7d57e3996c8900e86fecd16085b27e07f29/RepoGenesis), ревизия c090b7d57e3996c8900e86fecd16085b27e07f29. Исходная MIT и вложенные лицензии проверены по дереву: отдельного вложенного LICENSE в выбранном RepoGenesis не найдено; происхождение текстов требований не установлено полностью. Это предел проверки, не автоматическая лицензия всех возможных вложений. Эталонные реализации не предоставлялись строителям. [Исследование источников/NB-27, NB-50–52](source-review.md), [инвентарь](source-inventory-v1.json).

Интейк зафиксирован до чтения выбранных требований. Выбор — первые пять по SHA-256(seed + newline + task) из заранее ограниченной популяции 22 Python-задач; Java исключена до чтения из-за отсутствующих Maven/Docker. Seed, порядок и критерии: [sampling](sampling-policy-v1.json), [selection](selection-v1.json), [intake](intake-policy-v1.json). Детерминированный выбор не означает случайную репрезентативную выборку рынка.

Immutable manifest SHA-256: `5eb39300fc4c49018c1355a302042f9209def4314fbd1d2583303b99589262a1`. Все 3767 frozen files проверены; [seal](campaign-seal.json), [manifest](../reports/c0-campaign/manifest-v1.json). Правила Altrego заморожены на 006e445ea5199f9a4e86ee75df5571d8bf5167d2; harness commit c784410ad5a712ef2254ea9efff17d5e4b5891be. Заголовок protocol-draft отражает подготовительную редакцию; фактический гейт запуска — уже существующий sealed manifest.

Общие условия: CLI 0.160.0, gpt-6-astra, medium, подписка ChatGPT, 1800 активных wall-clock секунд/до восьми стадий на попытку, две CPU affinity; без hard token/total-memory quota для строителя. Offline immutable Python 3.12 runtime, одинаковый http.client, без install/внешних сервисов/платного API. Оценщик: startup 15s, tests 300s, 4GiB virtual address per child, две CPU. Эти условия ограничивают перенос, особенно для перевода; не менялись после исходов. Server-side revision весов модели недоступна: pinned имя/настройки и бинарник CLI не обещают побитово повторяемой генерации. Одна попытка на ветвь, последовательный порядок и меняющаяся нагрузка общего хоста не дают оценки variance или причинности.

Фактическая изоляция: clean client/session, apps/plugins/web/MCP выключены у строителей; restricted native FS и localhost-only commands; outer read-only root/private tmpfs/PID namespaces; отдельные service/test FS и PID у оценщика с private network. Синтетические positive/negative, ложный stdout-score, omissions и denial checks сохранены до кампании в [preflight](../reports/c0-recovery). Публичные тесты были физически недоступны инструментам строителей; возможная обучающая контаминация не исключена. Контроллер видел оракулы и обе ветви: независимость источника не означает независимость оператора.

## 1. Исходы и знаменатели

| Задача | Контроль: passed / expected | Altrego A: passed / expected | All-pass контроль / A | Парный разбор |
|---|---:|---:|---|---|
| TaskManagement | [34/44](../reports/c0-campaign/01-TaskManagement-control/evaluation/results/result.json) | [31/44](../reports/c0-campaign/02-TaskManagement-altrego/evaluation/results/result.json) | нет / нет | [разбор](../reports/c0-campaign/TaskManagement-pair/Pair-report.md) |
| WebPan | [0/22](../reports/c0-campaign/04-WebPan-control/evaluation/results/result.json) | [0/22](../reports/c0-campaign/03-WebPan-altrego/evaluation/results/result.json) | нет / нет | [разбор](../reports/c0-campaign/WebPan-pair/Pair-report.md) |
| simple-rbac-service | [8/9](../reports/c0-campaign/05-simple-rbac-service-control/evaluation/results/result.json) | [8/9](../reports/c0-campaign/06-simple-rbac-service-altrego/evaluation/results/result.json) | нет / нет | [разбор](../reports/c0-campaign/simple-rbac-service-pair/Pair-report.md) |
| Chatroom | [9/9](../reports/c0-campaign/08-Chatroom-control/evaluation/results/result.json) | [9/9](../reports/c0-campaign/07-Chatroom-altrego/evaluation/results/result.json) | да / да | [разбор](../reports/c0-campaign/Chatroom-pair/Pair-report.md) |
| Multilingual | [32/33](../reports/c0-campaign/09-Multilingual-control/evaluation/results/result.json) | [25/33](../reports/c0-campaign/10-Multilingual-altrego/evaluation/results/result.json) | нет / нет | [разбор](../reports/c0-campaign/Multilingual-pair/Pair-report.md) |

Полный знаменатель — **5 пар/10 попыток**. Операционный чистый знаменатель — **5 пар/10 попыток**, исключённых пар нет: в просмотренных трассах не наблюдались доступ к oracle/reference/другой ветви и tampering. Это конечное ручное суждение общего контроллера, не доказательство отсутствия public/training contamination. При обнаружении загрязнения одной ветви протокол исключает обе; симметричных исключений здесь не потребовалось.

Контроль: 83 passed, 12 failed, 22 skipped из фиксированных 117; A: 73 passed, 22 failed, 22 skipped из 117. Errors/timeouts в этих внешних оценках — 0. Сумма checks дана как описание неоднородных тестов, не как более сильный показатель, чем paired task all-pass. Полный проход — только Chatroom, по 1/5; ничьи по all-pass во всех пяти парах. Завершённые попытки и оценки не повторялись.

WebPan: все 22 теста обеих ветвей skipped, потому что upstream readiness fixture требует undocumented /api/v1/health; контроль явно вернул 404, у A маршрут отсутствует по source, лог фиксирует rejection. Пропуски не приняты за успех и не удалены из первичного знаменателя. TaskManagement и RBAC имеют спорные конкретные конвенции, не полностью заданные README; сырые баллы не пересчитаны. RBAC неизвестный never-assigned user: oracle ждёт 200/empty, обе ветви дают 404; known-empty user работает отдельно.

Multilingual: control 32/33 со словарём, A 25/33 с явным unavailable и пустым каталогом; **общий перевод не выполнен у обеих**. Оракул проверяет непустой translated_text, но не правильность смысла. Разница баллов не превращает словарь в общий перевод. Owner отдельно разрешил неполную измеряемую попытку в прежних условиях; ни требование, ни runtime не изменены.

## 2. Цена и нагрузка владельца

| Задача | Контроль CLI s | A CLI s | Контроль input / output | A input / output |
|---|---:|---:|---:|---:|
| TaskManagement | 118.933 | 1022.633 | 107581 / 6648 | 942655 / 28824 |
| WebPan | 319.494 | 1479.241 | 231532 / 11072 | 1694182 / 45633 |
| simple-rbac-service | 86.620 | 464.932 | 72329 / 3292 | 258507 / 13089 |
| Chatroom | 200.366 | 785.382 | 131675 / 5825 | 504506 / 20177 |
| Multilingual | 270.671 | 939.541 | 152492 / 8091 | 620337 / 24939 |
| Итого | 996.084 | 4691.729 | 695609 / 34928 | 4020187 / 132662 |

CLI time A/control = 4.710×; input tokens = 5.779×. Это наблюдение полного процесса при одинаковом потолке, не оценка денежной стоимости токенов или owner time. Контроль: 5 стадий, A: 12. Cached input — подмножество input (588544 / 3679616), reasoning output — подмножество output (2054 / 14888). Последний reported cumulative total взят один раз на контекст; стадии не суммированы как независимые накопленные totals. [Машинные метрики](../reports/c0-campaign/final-metrics.json), [append-only journal](../reports/c0-campaign/attempts.jsonl).

Дополнительные денежные расходы — 0; использована существующая подписка, платный API не включался. Расход квоты подписки и полная телеметрия общего контроллера не измерены. Goal registry stale blocked counter не используется как полный расход C0. Подготовка/исследование/smoke и controller review не включены в per-arm CLI totals. Owner waiting исключён; часы по промежуткам сообщений не вычислялись.

Нагрузка владельца: шесть реальных response acts — одна общая подпись пяти исходных брифов и пять подписей documentation+Build. Во всех active_minutes=null по явной отметке владельца. Общая подпись не разделена искусственно на пять затрат. Наблюдённых ручных переносов CLI-промптов владельцем — 0: запускал контроллер. Наблюдённых повторных объяснений требований сервиса — 0; это не оценка всех когнитивных затрат. Пять явных outer-goal resume directives находились внутри тех же подписывающих сообщений, а не пяти новых актов. Multilingual добавил явное owner-уточнение приоритета review/отсутствия новых ресурсов внутри последнего гейта. Окончательная приёмка ещё не получена. [Owner workload](../reports/c0-campaign/owner-workload.jsonl).

Controller→builder handoffs: 5 control/12 A. Дополнительные контроллерские вмешательства отделены: доступная копия реальной подписи TaskManagement (одна continuation), WebPan optional-password scope correction (одна continuation), Chatroom review с двумя behavior corrections (один review), Multilingual review замороженных условий (один review). Они не объявлены минутами владельца. Данные не устанавливают ни экономию, ни увеличение его активного времени.

## 3. К1–К7 и линтер

Единица ручного счёта — отдельный наблюдённый инцидент в просмотренной попытке; исправленные до сдачи случаи отделены от сохранившихся. Основной класс выбирается один, чтобы не умножать один случай по нескольким строкам. Разбор делал общий контроллер; независимой gold-разметки нет. Каждый attempt имеет trace-review.json; исторические ранние review сохраняют тогдашний pending status, внешний итог берётся из result.json.

| Класс | Контроль: сохранившиеся подтверждённые рецидивы | A: сохранившиеся подтверждённые рецидивы | Исправленное / предел покрытия |
|---|---:|---:|---|
| К1 провенанс | 0 наблюдено | 0 наблюдено | Verified hashes и фактические outputs; pre-emission lint findings отдельно |
| К2 соответствие измерения вопросу | 0 наблюдено | 1 | Chatroom A заявил отсутствие outstanding checks, но missing-interpreter/import-failure не запускались; OpenAPI count и SIGTERM assumption исправлены до сдачи |
| К3 исполнимость инструкции | 0 наблюдено | 0 наблюдено | Control WebPan/Chatroom/Multilingual исправили ConnectionRefused orchestration, raw failures сохранены |
| К4 граница хода/артефакта | 0 наблюдено | 0 наблюдено | TaskManagement receipt был недоступен строителю, controller continuation исправила; gates не подделаны |
| К5 безопасная запись | 0 наблюдено | 0 наблюдено | Own-workspace writes, protected hashes; отсутствие наблюдения не универсальное доказательство |
| К6 полнота по классу | 0 подтверждено | 0 подтверждено | WebPan control: отдельная static privacy finding capability IDs в audit, runtime leak не проверен; A OPTIONS и truncated-history coverage исправлены |
| К7 приёмка детектора | 0 наблюдено | 0 наблюдено | Control не заявлял calibrated mutation sensitivity; A witnesses исполнены, переводческий witness честно blocked |

Нули означают только отсутствие **подтверждённого сохранившегося** случая в конечном просмотре. Из них нельзя выводить отсутствие классов, преимущество процесса или отсутствие продуктовых дефектов. Общий перевод/WebPan malware/Docker gaps учитываются как unmet/unconfirmed, не автоматически как К-рецидивы. A WebPan первоначально сузил optional password — scope review исправило до подписи; исправленный инцидент сохранён. [Инвентарь К и уроки](LESSONS.md).

Mechanical lint — отдельное измерение артефактов контроллера, не whole-service outcome. Initial pre-emission draft: 30 findings (turn_end 10, claim_provenance 20), 0/10 green. После исправления A: 5/5 A green; у пяти baseline prompts по одному turn_end red осознанно неприменимо, Altrego marker в control не добавлен. Additional WebPan owner draft имел один claim_provenance red, исправлен до выдачи. Все финальные execution handoffs и owner requests имеют saved green check_turn; not_measured/infra/calibration_reds в этих целевых проверках пусты. Покрытие — 18 handoff checkers, не детекторы всех К1–К7 или бизнес-логики. [Lint summary](../reports/c0-campaign/linter-measurement-summary.json), [scope baseline reds](../reports/c0-campaign/handoff-review.md). Черновик K получил ещё четыре pre-emission findings (три claim_provenance и одно live_channel_slot на условной фразе); исходный verdict сохранён, текст исправлен. Финальный K: green, findings/not_measured/infra/calibration_reds пусты; это не подпись владельца и не запуск M1.

## 4. Пассивный интейк и связь с исходом

Исходные assessments заморожены, 4/5 приняты. Chatroom не прошёл I4: lifecycle/persistence не определены. Owner acceptance исходных брифов — другой акт, не изменение score. Среди четырёх accepted tasks all-pass 0/4 у обеих ветвей; среди одного not-accepted task — 1/1 у обеих. На n=5, неоднородных задачах и ограниченном оракуле это не валидирует интейк как предиктор и не доказывает его вред. Отсутствие persistence в Chatroom не помешало in-memory service выполнить проверяемый API. [Исходный интейк](intake-assessment-v1.json).

## Невыполненное и неизмеренное

TaskManagement: Docker image build, container execution/persistence не подтверждены; Docker socket inspection A был denied. Dockerfile/локальная persistence не заменяют Docker proof. Browser rendering не измерялся.

WebPan A: comprehensive malware-content scanning и full audit-intent/outcome crash reconstruction не реализованы. Long-term 99.9%, power-loss durability, exhaustive fault permutations не измерены. Control не доказал 100 distinct concurrent users и безопасную audit redaction; source содержит capability IDs. Внешний skip gate не проверил core behavior ни одной ветви.

RBAC: неизвестный user имеет oracle convention disagreement, raw 8/9 сохранены. Production load/arbitrary schedules не измерены.

Chatroom A: missing-interpreter/import-failure startup scenarios не исполнены. Обе owner-коррекции — реальный backward test clock и diagnostic canaries с leak witness — исполнены. Host OS clock не менялся; unexpected 500 privacy, sustained load, exhaustive interleavings не измерены. Control clock regression/privacy sensitivity/restart в own tests не измерены.

Multilingual: общий перевод и real catalog/pair support unmet у обеих. A: восемь real-translation cases и identity-translation witness blocked; runbook language-coverage assertion executed and failed. Mock wiring не перевод. Real translation quality, throughput/memory, exhaustive inputs и universal/import-time no-egress proof не измерены. [Последняя пара](../reports/c0-campaign/Multilingual-pair/Pair-report.md) перечисляет каждую заблокированную проверку.

## Полезность оракула и следствия для M1

Факт: внешний oracle обнаруживает несовместимость/неуспех независимо от красивого отчёта и собственных зелёных тестов. Он ограничил самоподтверждение: ни 31/44, ни 8/9, ни 25/33 не названы полным проходом. При этом WebPan all-skip и слабая semantic translation проверка показывают, что один score не равен работающему результату и не измеряет нагрузку владельца. Oracle полезен как дополнительный канал с проверенной применимостью; он недостаточен как единственный критерий успеха Altrego.

Факты для M1: profile должен связать доступы/ресурсы/команды/requirements и существующие инструкции; real process checks и целевые witnesses доступны в bounded service work; полный процесс увеличил measured CLI cost здесь; owner-minute evidence отсутствует; existing service correctness/delivery нуждаются в независимом контракте приёмки. C0 не закрывает D2/D3 или автономность.

Гипотезы для M1, не доказанные C0: универсальный профиль/loader могут уменьшить handoffs и повторные объяснения; предварительная проверка requirement↔runtime↔oracle fit может уменьшить бесполезную работу; пропорциональная docs spine может снизить стоимость при сохранении gates. Проверять в M1 на выбранной полезной доработке с реальными owner-minute отметками, независимыми outcome checks и явной доставкой. Сервис/изменение выбираются в следующем чате, не здесь. M2/SDK/frontend/VPS/evolution не запускались.

## Воспроизводимость, состояние и закрытие

[README harness](README.md), [protocol](protocol-draft.md), pinned source/runtime lock, immutable manifest, append-only journal, raw CLI sessions, artifact seals и trusted evaluator result/JUnit сохранены. Секреты subscription auth не входят в evidence. Для аудита сначала проверить hash-chain/manifest/seals; bootstrap offline runtime из reviewed pinned wheels — по reproduction note в delivery bundle. В текущей кампании дополнительные оценочные прогоны запрещены и не проводились.

Ветка `codex/c0-outcome-oracle` продолжена от проверенного origin/main 006e445. Финальные HEAD/дерево/список локальных коммитов фиксируются после mandatory hooks в reports/c0-delivery/repo-state.json, чтобы не создавать самоссылочный hash в коммите. Push/merge команды подготовлены только для владельца. Локальные reports gitignored: итоговый evidence bundle и его checksum сохраняют все артефакты вне временных builder directories.

Подготовлены [условный заполненный K для M1](M1-kickoff.md), [10c inventory/lessons](LESSONS.md) и точечные proposals существующих r2/log/register в reports/c0-campaign/closure. Это **подготовка**, не применённое vault-закрытие и не старт M1. Корпус/rules/linter не менялись. Goal registry продолжает технически показывать blocked и не поддерживает active/resume; новая цель или новая попытка ради статуса не создавались.

Оставшиеся действия владельца: принять или отклонить отчёт; выполнить выбранный push/merge; применить подготовленные state changes свежим read/safe-write/read-back; подтвердить фактический статус перед запуском K. До этих актов C0 готов к приёмке, не принят/не слит; M1 не начат.
