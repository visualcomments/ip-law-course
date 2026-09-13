# Индекс и эмбеддинги на Google Диске

Индекс корпуса курса «Право интеллектуальной собственности» (Annoy + эмбеддинги +
чанки) распространяется как **файлы на Google Диске**: репозиторий
самодостаточен. Агент или пользователь скачивает архив по ссылке,
инструмент проверяет SHA-256 и разворачивает индекс в локальный корпус
(`COURSE_CORPUS_ROOT/index/`), после чего работают `make search`,
`make verify` и локальный RAG-API.

## Состав архива

Один архив — **`ip-law-index-2026-09-13.zip`** (27 958 844 байт, 26,7 МБ):

| Файл | Размер | SHA-256 |
|---|---|---|
| `annoy.index` | 14 771 016 Б | `04D1D7BA…917825` |
| `chunks.jsonl` | 12 569 515 Б | `8A23A3F4…A1AF987` |
| `embeddings.npy` | 12 874 880 Б | `55295AF1…39985F` |
| `config.json` | 7 630 Б | `7EB5DDD1…42DFB961` |

`SHA-256` архива: `E410AB4CC3310312195BF13A94EC7BACCB215CEAABF5B7E2EC73EA3BC6BC5E6D`.
Точные значения — в `index-manifest.json`.

Индекс покрывает **146 файлов корпуса, 8 382 чанка** (модель
`paraphrase-multilingual-MiniLM-L12-v2`, 384 измерения, чанк 1400/140).
Состав: 50 статей под CC-лицензиями, 54 статьи Wikipedia (CC BY-SA 4.0),
16 текстов договоров и законов, 12 трактатов общественного достояния,
14 файлов судебной практики.

**Где лежит:** папка `courses-indexes` на Google Диске. Прямая ссылка уже
вписана в `index-manifest.json` (`archive.url`) — достаточно
`make corpus-fetch` без параметров. Просмотр файла:
`https://drive.google.com/file/d/12aQ2Ncn5ZXXWWA_GW-UwE0yGO06f0_xo/view`.

**Сквозная проверка (2026-09-13).** `tools/corpus_fetch.py --index-only` по
ссылке из манифеста: SHA-256 подтверждена, индекс установлен,
`chunks: 8382, files: 146`. Ссылка проверена анонимно: Google отдаёт
HTML-страницу подтверждения (для больших файлов это норма), а после
следования форме — `application/octet-stream` и настоящий ZIP; загрузчик
`corpus_fetch.py` это обрабатывает сам.

## Как выложить и подключить

1. Соберите архив из `COURSE_CORPUS_ROOT/index/` (например,
   `Compress-Archive -Path index\annoy.index, index\chunks.jsonl, index\config.json, index\embeddings.npy -DestinationPath course-index-ip-law-<дата>.zip`),
   посчитайте SHA-256 каждого файла и архива.
2. Загрузите архив на Google Диск; общий доступ: **«Все, у кого есть
   ссылка» → «Читатель»**.
3. Скопируйте share-ссылку и подключите индекс:
   ```bash
   make index-fetch URL="https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
   # или
   export COURSE_INDEX_URL="https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
   make index-fetch
   ```
4. Инструмент `tools/index_fetch.py` скачает архив, проверит SHA-256
   (по `index-manifest.json`, если заполнен), распакует и атомарно
   заменит `COURSE_CORPUS_ROOT/index/`.

После развёртывания: `make search QUERY="..."`, `make verify`,
`make serve` — как с любым локальным корпусом.

## Обновление индекса

```bash
# 1. Пересобрать индекс и собрать архив из index/ (4 файла в корне архива)
# 2. Посчитать SHA-256 архива и каждого файла
# 3. Залить на Диск (OAuth от личного аккаунта):
rclone copy ip-law-index-<дата>.zip gdrive:courses-indexes/
rclone link gdrive:courses-indexes/ip-law-index-<дата>.zip    # публичная ссылка
# 4. Обновить index-manifest.json (filename, size_bytes, sha256, url) и закоммитить
```

- `make corpus-fetch` сверяет сумму с манифестом; при несовпадении
  распаковка не производится (защита от повреждённой загрузки).

**Кто может загружать.** Сервисный аккаунт Google **не может** создавать
файлы (`403 Service Accounts do not have storage quota`, квота 0), а
API-ключ не может писать (`401: API keys are not supported by this API`).
Работает OAuth от личного аккаунта (rclone) либо ручная загрузка в браузере.
Выдача сервисному аккаунту прав «Редактор» на папку проблему **не решает**:
квота считается по создателю файла.

**Проверка после заливки обязательна:** прогнать
`python tools/corpus_fetch.py --index-only` — он проходит форму подтверждения
Google и сверяет SHA-256 (именно так будет скачивать студент).

## Переменные окружения

- `COURSE_CORPUS_ROOT` — корень корпуса (`txt/`, `index/`);
- `COURSE_INDEX_URL` — ссылка на архив (альтернатива `--url`/манифеста);
- `COURSE_TXT_DIR`, `COURSE_INDEX_DIR`, `COURSE_REPO_DIR` — переопределения
  каталогов корпуса и репозитория.