# GREEN · unguarded_state_write

Тот же предмет, собранный по лечению реестра §D: между чтением состояния и
записью по нему стоит проверка, что чтение состоялось. **По одному оправданию на
блок** — сложи три в один, и мёртвое станет неотличимо от живого: калибровка
печатает ноль в обоих случаях.

Проверка между чтением и записью (PowerShell): форма, которой в каноне не было.

```powershell
$p = "D:\Obsidian\TheyGrow\claude_desktop_config.json"
$j = Get-Content $p -Raw | ConvertFrom-Json
if (-not $j) { throw "конфигурация не прочитана: запись не делается" }
$j | ConvertTo-Json -Depth 12 | Set-Content $p -Encoding UTF8
```

Сцепка на той же команде (bash): правая часть не исполняется на провале левой.

```bash
CFG="$(cat ~/.config/claude/claude_desktop_config.json)" && printf '%s' "$CFG" > ~/.config/claude/claude_desktop_config.json
```

Режим обрыва выше по блоку и чтение без объявления: `set -e` видит код возврата
подстановки, и запись по пустому значению не исполняется.

```bash
set -euo pipefail
VER=$(jq -r .version package.json)
gh release create "v$VER" --notes "сборка полосы"
```

**Конец хода:** нужно слово владельца — подтвердить редакцию, которую он видит в `package.json`.
