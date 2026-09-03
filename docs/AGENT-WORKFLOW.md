# Agent workflow: курс + соученик (botai)

Как ИИ-агент (harness типа botai) эффективно работает с данным курсом.
Короткая версия — `AGENTS.md`; состояние окружения — `make status`.

## Цикл работы агента

1. **Онбординг.** `make status` (состояние курса/корпуса); прочитать
   `syllabus.json` + `agents/courses/ip-law-fall/track.md`;
   установить индекс: `make index-fetch URL="<ссылка>"` (Google Диск,
   `docs/GOOGLE-DRIVE.md`).
2. **Занятие.** `make session n=<NN>` (текст+цитаты+источники),
   `make assignment n=<NN>` (вопросы/задания); объяснения — по материалам
   занятия; при необходимости `make search QUERY="..."`.
3. **Проверка.** Ответы и эссе проверяются по контракту цитирования:
   цитаты только из корпуса с координатами «файл · фрагмент #N»;
   охраняемые авторы — «вне корпуса». `make verify` после любых правок.
4. **Прогресс.** `agents/progress/progress-example.md` — шаблон (по
   конвенции botai); файл прогресса ведётся в пространстве агента.
5. **Supplement.** Занятия 14–19, 26 — авторский синтез (авторы XX в.);
   доп. материалы — только проверяемые источники (списки чтения в
   занятиях), не в корпус.

## Инструменты и контракт

| Что | Команда |
|---|---|
| Поиск по корпусу | `make search QUERY="..."` / `tools/rag_search.py` |
| Индекс с Google Диска | `make index-fetch URL="..."` / `tools/index_fetch.py` |
| Материалы занятия | `make session n=NN` / `tools/session_material.py NN` |
| Задания занятия | `make assignment n=NN` / `tools/assignment_brief.py NN` |
| Проверка цитат | `make verify` / `tools/verify_quotes.py` |
| Локальный RAG-API | `make serve` / `tools/rag_api.py` |
| Статус | `make status` / `tools/status.py` |
| Поиск фразы в корпусе | `make quotes QUERY="..."` / `tools/quote_finder.py` |
| Навыки | `.agents/skills/using-course-corpus`, `.agents/skills/building-agent-ready-course-repo` (+ зеркала .claude/.cursor) |

Все пути/каталоги корпуса — через переменные окружения
(`COURSE_CORPUS_ROOT`, `COURSE_TXT_DIR`, `COURSE_INDEX_DIR`, `COURSE_REPO_DIR`);
в репозитории нет локальных путей и серверной инфраструктуры.