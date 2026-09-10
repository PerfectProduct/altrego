# RED · unguarded_state_write

Провенанс: `00-system/canon-corrections-register.md`, §D, наблюдения 2026-09-08 (3),
пункт 3 — К6 **с материальным ущербом**. Блок правки записи клиента в PowerShell
не имел проверки между чтением и записью: `ConvertFrom-Json` упал на висячей
запятой, оболочка продолжила построчно, `$j` осталась объектом из прошлого
сеанса консоли, и запись затёрла правку владельца. Канон нёс «цепочки с побочным
эффектом — через `&&`» — формулировку про bash; переноса на PowerShell не
произошло, и лечение, названное там же, есть предмет этого чекера.

Над оградой ниже нет маркера `Handoff for shell` намеренно: область формы
задаётся списком языков, и с маркером блок стал бы исполняемым для всех чекеров —
тогда снятие `shell_langs_extra` не покрасило бы ни одного теста, и «класс, а не
оболочка» осталось бы словами.

```powershell
$p = "D:\Obsidian\TheyGrow\claude_desktop_config.json"
$j = Get-Content $p -Raw | ConvertFrom-Json
$j.mcpServers."altrego-linter".args = @("-e", "/home/dev/altrego/.venv/bin/python")
$j | ConvertTo-Json -Depth 12 | Set-Content $p -Encoding UTF8
```

Тот же класс в bash под `set -euo pipefail`: объявление маскирует код возврата
подстановки (ShellCheck SC2155, ADR-054 NB-43), errexit его не видит, и версия
уходит в имя тега пустой.

```bash
set -euo pipefail
export VER=$(jq -r .version package.json)
gh release create "v$VER" --notes "сборка полосы"
```
