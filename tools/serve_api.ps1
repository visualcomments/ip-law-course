# Запуск RAG-API (Windows PowerShell)

if (-not $env:COURSE_CORPUS_ROOT) { Write-Error "Установите COURSE_CORPUS_ROOT (см. CORPUS.md)"; exit 2 }
$ROOT = $env:COURSE_CORPUS_ROOT
$py = $env:COURSE_VENV_PY
if (-not $py) { $py = "python" }
$api = Join-Path $ROOT "scripts\rag_api.py"
if (-not (Test-Path $api)) { Write-Error "Корпус не найден: $api (см. CORPUS.md)"; exit 2 }
$port = 8765
if ($args.Count -gt 0) { $port = $args[0] }
Write-Host "RAG API: http://127.0.0.1:$port  (Ctrl+C — стоп)"
& $py $api --port $port