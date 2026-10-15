# C0: подготовленный разбор 10c

Это подготовка обязательного терминального разбора после K, не применённая запись канона. C0 ещё ждёт окончательной приёмки, push/merge и state changes. Новый milestone не начат. Факты взяты из append-only журнала, raw CLI/оценок, owner receipts и review; конечный общий контроллер не является независимым судьёй.

## Инвентаризация всего C0

| Наблюдение | Класс/слой | Исход и доказательство |
|---|---|---|
| Initial handoff draft не нёс достаточного provenance/turn end | pre-emission lint, К1/К4 формы | 30 mechanical findings сохранены; A исправлен до measured start, baseline reds scoped; initial-handoff-lint-before/final |
| Черновик условного M1 K имел три provenance findings и одно срабатывание на условную фразу о публикации | pre-emission lint, не новая попытка C0 | K.lint-before сохранён; добавлен явный провенанс чтения, условие переписано без имитации remote state; финальный K проверен отдельно |
| Настоящая подпись TaskManagement существовала у контроллера, но отсутствовала в builder FS | исправленный controller К4 boundary | одна same-context continuation с фактическим receipt; costs сохранены; не новый owner акт |
| WebPan private password был ошибочно сделан обязательным в первом unsigned плане | исправленный scope/completeness incident | review восстановило optional поле до подписи, same context; исходный README неизменён |
| Own harness: OpenAPI path count, SIGTERM status assumption, generator self-reference, truncation первой сотней сообщений | исправленные К2/К6 случаи | raw failures и affected reruns сохранены, не surviving recurrence |
| Control WebPan/Chatroom/Multilingual тесты потеряли живой процесс между командами | исправленные К3 orchestration, три попытки | ConnectionRefused не скрыт; строители сами добавили owned launch/readiness/cleanup внутри попытки |
| Altrego RBAC automatic OPTIONS оказался вне JSON-contract coverage | исправленный К6 | disabled и затронутые тесты повторены до сдачи |
| Chatroom runtime claim для часов/диагностики требовал behavioral evidence | controller review, не owner reexplanation | две коррекции реально исполнены; backward clock и password leak mutant достигли целевых assertions |
| Chatroom A «no validation outstanding» при неисполненных missing-runtime/import-failure scenarios | surviving manual К2 judgment, один инцидент | два named checks явно unexecuted в controller review и итоговом отчёте; артефакт не переоткрыт |
| WebPan control audit содержит capability IDs/paths | static privacy/completeness finding | runtime leak не подтверждался; не превращено в наблюдённую утечку или oracle contamination |
| Multilingual A выявил отсутствие движка до Build | unmet capability, не снятое требование | owner разрешил частичную попытку; review выше условного добавления ресурсов; движок повторно не запрошен |
| Werkzeug startup probe нарушил exercised-path network guard | исправленный runtime incident | первоначальные три failures сохранены, startup исправлен с прежним guard; startup errors не counted witnesses |
| Multilingual runbook language coverage не проходит | действующий unmet result | snippet выполнен дословно, exit 1 сохранён; mock/словарь/identity не признаны общим переводом |
| Goal status blocked требует повторного outer steering | infra/owner friction | пять resume directives внутри уже нужных signature acts; новая цель/попытка не создавалась; активные минуты неизвестны |
| WSL Node Filesystem MCP не читал большой log, Invalid string length | read infra, resolved | тот же MCP на установленном Windows Node прочитал tail=120, guard/root сохранены; vault не правился |
| Auto-review ошибочно приписал control32/33 оценке A | approval infra, resolved до процесса | read-only показал отсутствие каталога A; тот же запрос одобрен; первая оценка A25/33, ни один run не повторён |

Внешние TaskManagement/RBAC convention disagreements, WebPan all-skip и слабые linguistic assertions — свойства fit оракула, не автоматически рецидивы процесса. Большинство нулей К1–К7 обозначают отсутствие подтверждённого сохранившегося случая в конечном просмотре, не отсутствие всех ошибок. Ручные классы не складываются с количеством mechanical findings. Для Chatroom подготовлена строка §B существующего runtime-evidence правила: поиск по свежему полному реестру не нашёл прежней пары «это правило × К2», предложен счёт 1 с обязательной повторной проверкой перед owner-внесением.

## Однозначные уроки и их дом

1. **Внешний балл требует собственного verdict о пригодности измерения.** Дом — существующие delivery-contract §11 (измерение должно отвечать вопросу), правила oracle C0. Точная прикладная формулировка для M1 framing: «Сохранить raw outcome вместе с skips/infra; отдельно назвать связь проверяемого поведения с требованием, пропуски покрытия и пределы. Не менять score/знаменатель после результата». Проверка — в приёмочном отчёте есть raw result и fit analysis; допустимые попадания — static-only packet с явно иной единицей; момент — рамка и outcome review; повод — C0 WebPan all-skip/Multilingual semantic weakness. Это применение существующего правила, **новая правка канона не предлагается**.
2. **Owner time нельзя заменить CLI cost или ожиданием.** Дом — существующий контракт измерений C0 и r2 owner metric. Прикладная формулировка: «Active minutes — только фактическая самоотметка; unknown сохраняется; handoffs, повторные объяснения и вмешательства считаются отдельными актами». Проверка — null не превращён в 0 и нет gap estimate; допустимые попадания — нет для активного времени; момент — gate и закрытие; повод — все шесть подписей C0 not measured. Новое правило не требуется.
3. **Запускаемый мутант ещё не доказывает целевую чувствительность.** Дом — действующий delivery-contract §11, detector acceptance. Прикладная формулировка: «Засчитывать только named target failure после рабочего baseline; startup/setup crash оставлять отдельным failure; unavailable baseline означает blocked». Проверка — raw witness содержит конкретную assertion и baseline; допустимые попадания — явно static guard со своей единицей; момент — acceptance нового runtime detector; повод — C0 startup probe и blocked identity-translation witness. Канон уже содержит требование, дополнительный текст не добавляется.
4. **Handoff исполним только из состояния получателя.** Дом — существующий prompt-kit artifact integrity и граница хода. Прикладная формулировка: «Фактический receipt и подписанный текст должны быть доступны адресату с проверяемыми hashes до зависимой команды». Проверка — receiver verification в raw CLI; допустимые попадания — короткий go-ahead без внешнего дословного текста; момент — каждая соответствующая эмиссия; повод — TaskManagement inaccessible receipt. Это структурно исполнено в оставшихся попытках, правила/manifest во время кампании не менялись.

Самооценка формулировок: 100/100 по однозначности, наблюдаемой проверке, допустимым попаданиям, моменту и конкретному поводу. Оценка относится к ясности этих применений существующих правил, не к доказанной эффективности нового лечения.

## Сознательно не внесено

Не предлагаются новые защищённые правила, ослабление gates или thresholds, замена источника тестов, расширение runtime, перенос канона, универсальный переводчик, D2/D3 и утверждение «Altrego вреден/полезен всем». На n=5 причинность и owner-time эффект не установлены. Оптимизация профиля/loader/пропорциональности docs и раннего resource/oracle fit — гипотезы для рамки M1, не исполнение M1 и не принятые правила. Новые тексты корпуса/registry не менялись.

## Очередь и обещанные фиксации

Очередь r2 сохраняется: C0 ждёт owner acceptance, затем M1, затем M2 и прежний backlog. По C0 нельзя ранжировать всю очередь в owner-hours: часы не измерены. Для инфраструктурного M1: рецидивы/цена владельца — не установлены; размер задаётся будущей рамкой; место №5 после C0 — прямой owner priority 2026-10-14, не измеренный WSJF. Критического вытеснения без названного порога не вводим.

Обещанные фиксации C0: полный отчёт, last pair, four metrics/owner load, preserved raw evidence, M1 K, 10c lessons и proposals существующих носителей — подготовлены в этом delivery. Actual vault writes/приёмка/push/merge остаются владельцу; их отсутствие явно названо, обещание применить позже автоматически не даётся. Product system-map не меняется: в app/** Altrego продуктовых изменений нет, бенчмарк-сервисы не развёрнуты.

Для записи владельцем: «C0: уроков, требующих нового правила канона, нет; инциденты и применение действующих правил записаны в отчёте 10c. Внесение новых правил не выполнялось». Эта строка подготовлена в log append предложения закрытия, не объявлена уже внесённой. Предложения r2/log/register и read-hash anchors — reports/c0-campaign/closure; применять только свежим чтением/safe-write/read-back после owner-акта.

Sources: c0/RESULTS.md; final-metrics.json; attempts.jsonl; owner-workload.jsonl; все trace-review.json; initial-handoff-lint-before/final; blocker-audit.jsonl; свежий Filesystem MCP canon-corrections-register, delivery-contract, prompt-kit K и r2. Порядок подготовленных артефактов: 10a proposals → K → этот 10c разбор. Реальное post-merge закрытие не имитировано.
