# GREEN · env_presupposition

Тот же предмет: каждая предпосылка измеряется строкой выше той, которая на неё
опирается.

```bash
python3 -m venv .venv
./.venv/bin/pip install "pyyaml==6.0.3"
gcloud run services list --region europe-west1
gcloud run services describe theygrow-web --region europe-west1 --format='value(status.url)'
adb devices
adb -s "$(adb devices | awk 'NR==2{print $1}')" shell getprop ro.build.version.release
```

Тот же предмет на правах токена: набор прав измеряется до того, как на него
опираются, — и push файла workflow, и добавление права идут после чтения.

```bash
gh auth status
git add .github/workflows/ci.yml
git commit -m "гейт: лимит прогона"
git push
gh auth refresh -s workflow
```

Тот же класс на чтении по сети: конечный адрес назван самим вызовом, а не
предполагается равным написанному. Первая строка не идёт за редиректом вовсе —
умолчание curl «остановиться на 3xx» и есть fail-closed (ADR-054 NB-45).

```bash
curl -sS https://example.invalid/policy.json -o /tmp/policy.json
curl -sSL -w '%{url_effective}\n' https://example.invalid/policy.json -o /tmp/policy.json
curl -sSL --max-redirs 0 https://example.invalid/policy.json -o /tmp/policy.json
curl -sSL --max-redirs=0 https://example.invalid/policy.json -o /tmp/policy.json
curl -sSL -X POST -w '%{url_effective}\n' https://example.invalid/hook -d @/tmp/payload.json
npm install express@4.18.2
```

Тот же класс переустановки в другой оболочке: редакция названа, и повтор блока
ставит то же самое (ADR-054 NB-44).

```powershell
Install-Module Pester -RequiredVersion 5.6.1
winget install Git.Git --version 2.45.1
```

**Конец хода:** нужно слово владельца — назвать, какой из перечисленных сервисов является предметом пакета.
