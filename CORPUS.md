# Корпус курса «Право интеллектуальной собственности»

Корпус — набор текстов под свободными лицензиями и официальных документов
в каталоге `FALT_CORPUS_ROOT/txt/` (по умолчанию `ip_law_corpus/txt`),
индекс — в `FALT_CORPUS_ROOT/index/`.

## Состав (20 файлов)

- **Официальные тексты (не объекты авторского права)**: Бернская
  конвенция (WIPO, EN), TRIPS — вводная часть (ВТО, EN).
- **Wikipedia (CC BY-SA 4.0)**: 10 статей RU (интеллектуальная
  собственность, авторское право, смежные права, патент, изобретение,
  полезная модель, промышленный образец, товарный знак, общественное
  достояние, интеллектуальные права) + 10 статей EN (copyright, patent,
  trademark, trade secret, industrial design right, public domain, Berne
  Convention, Paris Convention, WIPO, copyright infringement).
- **Книги в общественном достоянии**: Putnam («History of Copyright») и
  Birrell («The Law of Copyright», 1899) — истории авторского права.

## Сборка корпуса (порядок)

Корпус собирается скриптами в каталоге проекта пользователя
(`ip_corpus_v3.py` и др.); в репозитории корпус не хранится — только
`index-manifest.json` с контрольными суммами.

## Индекс

Индекс (Annoy angular, модель paraphrase-multilingual-MiniLM-L12-v2,
чанки 1400/140) собирается по схеме «кластер ПК + сервер» (локальный
пул + ubuntu-server через Ethernet) и распространяется архивом на
Google Диске: `course-index-ip-law-2026-09-03.zip`
(см. `index-manifest.json`, `docs/GOOGLE-DRIVE.md`).

Текущее состояние: **20 файлов, 970 чанков**; верификация цитат —
`verification/REPORT.md` (21 цитата, 0 ошибок).