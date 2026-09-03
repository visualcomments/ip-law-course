# Индекс и эмбеддинги на Google Диске

Индекс корпуса курса «Право интеллектуальной собственности» (Annoy + эмбеддинги +
чанки) распространяется как **файлы на Google Диске**: репозиторий
самодостаточен. Агент или пользователь скачивает архив по ссылке,
инструмент проверяет SHA-256 и разворачивает индекс в локальный корпус
(`FALT_CORPUS_ROOT/index/`), после чего работают `make search`,
`make verify` и локальный RAG-API.

## Состав архива

Один архив (`course-index-ip-law-<дата>.zip`) с четырьмя файлами:

| Файл | Содержимое |
|---|---|
| `annoy.index` | ANN-индекс (angular) |
| `embeddings.npy` | матрица эмбеддингов (N × 384, float32) |
| `chunks.jsonl` | чанки текста с метаданными (file, topic, chunk_id) |
| `config.json` | конфигурация индекса (размерность, метрика, число чанков) |

Точные размеры и SHA-256 для каждого файла и архива — в
`index-manifest.example.json` (заполняется при сборке индекса курса).

## Как выложить и подключить

1. Соберите архив из `FALT_CORPUS_ROOT/index/` (например,
   `Compress-Archive -Path index\annoy.index, index\chunks.jsonl, index\config.json, index\embeddings.npy -DestinationPath course-index-ip-law-<дата>.zip`),
   посчитайте SHA-256 каждого файла и архива.
2. Загрузите архив на Google Диск; общий доступ: **«Все, у кого есть
   ссылка» → «Читатель»**.
3. Скопируйте share-ссылку и подключите индекс:
   ```bash
   make index-fetch URL="https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
   # или
   export FALT_INDEX_URL="https://drive.google.com/file/d/FILE_ID/view?usp=sharing"
   make index-fetch
   ```
4. Инструмент `tools/index_fetch.py` скачает архив, проверит SHA-256
   (по `index-manifest.json`, если заполнен), распакует и атомарно
   заменит `FALT_CORPUS_ROOT/index/`.

После развёртывания: `make search QUERY="..."`, `make verify`,
`make serve` — как с любым локальным корпусом.

## Обновление индекса

- Пересобрать индекс (см. `CORPUS.md`), пересчитать SHA-256, обновить
  `index-manifest.example.json`, загрузить новый архив на Диск, обновить
  ссылку в `index-manifest.json`.
- `make index-fetch` сверяет сумму с манифестом; при несовпадении
  распаковка не производится (защита от повреждённой загрузки).

## Переменные окружения

- `FALT_CORPUS_ROOT` — корень корпуса (`txt/`, `index/`);
- `FALT_INDEX_URL` — ссылка на архив (альтернатива `--url`/манифеста);
- `FALT_TXT_DIR`, `FALT_INDEX_DIR`, `FALT_REPO_DIR` — переопределения
  каталогов корпуса и репозитория.