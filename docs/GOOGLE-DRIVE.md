# Индекс и эмбеддинги на Google Диске

Индекс корпуса курса «Право интеллектуальной собственности» (эмбеддинги и
чанки) распространяется как **файлы на Google Диске**: репозиторий
самодостаточен. Агент или пользователь скачивает архив по ссылке,
инструмент проверяет SHA-256 и разворачивает индекс в локальный корпус
(`COURSE_CORPUS_ROOT/index/`), после чего работают `make search`,
`make verify` и локальный RAG-API.

## Состав архива

Один архив — **`ip-law-index-2026-09-13-v2.zip`** (61 140 512 байт):

| Файл | Размер | SHA-256 |
|---|---|---|
| `annoy.index` | 32 162 796 Б | `F91D8BFD…C2414C4D` |
| `chunks.jsonl` | 26 056 832 Б | `89DCBA22…9766342C` |
| `embeddings.npy` | 27 984 512 Б | `F625A477…FF2883` |
| `config.json` | 9 502 Б | `63F0934F…31613CE8` |

Точные контрольные суммы архива и файлов находятся в `index-manifest.json`.

Индекс покрывает **186 файлов корпуса, 18 219 чанков** (модель
`paraphrase-multilingual-MiniLM-L12-v2`, 384 измерения, чанк 1400/140).
Состав: 50 статей под CC-лицензиями, 78 статей Wikipedia (CC BY-SA 4.0),
16 текстов договоров и законов, 11 трактатов общественного достояния,
14 файлов судебной практики.

**Где лежит:** папка `courses-indexes` на Google Диске. Прямая ссылка уже
вписана в `index-manifest.json` (`archive.url`) — достаточно
`make corpus-fetch` без параметров. Просмотр файла:
`https://drive.google.com/file/d/1y2bRH30i9GhJdXtRe7hjVS6eiY8YA5kU/view`.

Архив пока содержит `annoy.index` для совместимости со старой сборкой.
Текущие инструменты поиска используют `embeddings.npy` напрямую.

## Как выложить и подключить

1. Соберите архив из `COURSE_CORPUS_ROOT/index/` (например,
   `Compress-Archive -Path index\chunks.jsonl, index\config.json, index\embeddings.npy -DestinationPath course-index-ip-law-<дата>.zip`),
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
