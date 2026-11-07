# Корпус курса «Право интеллектуальной собственности»

Корпус — набор текстов под свободными лицензиями и официальных документов
в каталоге `COURSE_CORPUS_ROOT/txt/` (по умолчанию `ip_law_corpus/txt`),
индекс — в `COURSE_CORPUS_ROOT/index/`.

## Состав (427 файлов, расширение 2026-11-07)

| Категория | Файлов | Лицензия |
|---|---|---|
| `law__*` — договоры и законы | 46 | официальные документы (не объекты АП) |
| `lesson1__*` — PD-трактаты занятия 1 | 17 | общественное достояние |
| `oa__*` — научные статьи | 83 | CC BY / CC BY-SA (NC/ND исключены из новой выборки) |
| `pd__*` — трактаты | 66 | общественное достояние |
| `practice__*` — судебная практика | 14 | решения судов (GPL-3.0 датасеты) |
| `ru__*` — русскоязычные публикации | 22 | свободные лицензии |
| `wiki_en__*` | 96 | CC BY-SA 4.0 |
| `wiki_ru__*` | 45 | CC BY-SA 4.0 |
| `wikipedia__*` (старые) | 23 | CC BY-SA 4.0 |

- **Официальные тексты (не объекты авторского права)**: ГК РФ часть IV;
  Бернская конвенция (2 изд. + Implementation Act 1988); **Соглашение ТРИПС**
  (полный текст по частям + TRIPS_COVID_Waiver); Римская конвенция (2 изд.);
  Конвенция о фонограммах (2 изд.); Конвенция о спутниковом вещании (2 изд.);
  Всемирная конвенция об авторском праве (2 изд.); Статут Анны (1709); ACTA;
  ТПП гл. 18 (2 изд.); Кодекс ИС Филиппин (2 изд.); Конвенция УПОВ; ДАП/WCT
  (2 изд.); ДАИФ/WPPT (2 изд.); **НОВОЕ 2026-11-07**: Парижская конвенция
  (1883 и 1911 — полный текст через трансклюзию Wikisource!); Европейская
  патентная конвенция (EPC); Соглашение о едином патентном суде; DMCA
  (Title I — 512/1201; Title II); Закон США об авторском праве 1976 г.
  (полный, 210K симв.); Berne Implementation Act 1988; Copyright Law
  Circular 92 (Title 17 USC).
- **Wikipedia (CC BY-SA 4.0)**: 17 RU + 37 EN (база) + 26 RU и 42 EN
  (новые: Лицензионный договор, Исполнитель, Фонограмма, Плагиат, Бернская
  конвенция RU, ВОИС, Коммерческая тайна, Ноу-хау, Географическое указание,
  Копилефт, Creative Commons RU, Открытый доступ RU, Патентный тролль RU;
  EN: Patent claim/application/prosecution/examiner, Prior art, Novelty,
  Inventive step, DMCA, Sony v. Universal, Feist, Campbell v. Acuff-Rose,
  Eldred v. Ashcroft, Trademark dilution, Well-known trademark, Database
  right, Parallel importation, Exhaustion, Biopiracy, Gene patent, Oncomouse,
  Traditional knowledge и др.).
- **Трактаты PD (Internet Archive + Gutenberg)**: прежние 54 + новые
  (Gutenberg): Wordsworth «Law of Copyright», Copinger «Treatise on the Law
  of Copyright» (1,1 МБ, базовый английский трактат), Putnam «International
  Copyright», Warner «Literary Copyright», Thompson «Trade-Marks», «Recent
  discussions on the abolition of patents», «Patents and How to Get One»,
  «US Copyright Law Circular 92», Arguments перед Комитетом по патентам
  (1904/1906), Patent Laws of Hawaii, Classification of Patents.
- **Статьи под CC-лицензиями (DOAJ)**: 83 файла. Новая выборка 2026-11-07
  допускает **только CC BY / CC BY-SA / CC0** (NC/ND исключены). Манифесты —
  `catalog/doaj-manifest-2026-11-07.json`, `catalog/doaj-extra-2026-11-07.json`.
- **Судебная практика**: 378 решений СИП РФ (GPL-3.0) + 71 решение из
  sud-resh-benchmark (GPL-3.0).

Подробная таблица лицензий по каждому файлу — `docs/corpus-new-sources.md`.

## Сборка корпуса (порядок)

Скрипты сбора (в рабочем пространстве корпуса, каталог `build-iplaw/`):
`fetch_treaties.py` (договоры из Wikisource через трансклюзию HTML),
`fetch_wikipedia.py` (статьи Wikipedia с атрибуцией CC BY-SA),
`fetch_gutenberg.py` (PD-книги через зеркало pglaf), `fetch_doaj.py`
(CC-статьи DOAJ с проверкой лицензии журнала), `build_sources_map.py`
(проверка покрытия занятий), `build_index.py` (GPU-индекс). В репозитории
корпус не хранится — только `corpus-manifest.json` и `index-manifest.json`
с контрольными суммами; файлы лежат в HuggingFace dataset
`brics-edtech/ip-law-corpus`.

## Закрытый пробел 2026-11-07

**Парижская конвенция (1883, 1911) теперь в корпусе полным текстом** —
получена через трансклюзию постраничных сканов United States Treaty Series
на Wikisource (ранее страница-дизамбигуация считалась препятствием).
Добавлены также EPC, Unified Patent Court, DMCA, US Copyright Act 1976.
PCT, Мадридское, Гаагское, Ниццкое, Страсбургское соглашения по-прежнему
представлены постатейными трактатами 1887–1915 гг. и статьями Wikipedia
(RU+EN), т.к. их современные консолидированные тексты на WIPO Lex отдаются
внутри JS-оболочки. Пересказ вместо первоисточника в корпус не
подставлялся.

## Автоматическая проверка покрытия занятий

`build-iplaw/build_sources_map.py` (в рабочем каталоге сбора) строит карту
«занятие → источники» и гарантирует **≥ 10 источников на каждое из 16
занятий** (минимум: занятие 06 — 13). Карта — `catalog/sources-map.json`.

## Индекс

Индекс (модель paraphrase-multilingual-MiniLM-L12-v2, точный косинусный
поиск, чанки 1400/140) пересобран 2026-11-07 на GPU:
**427 файлов, ~60 000 чанков** (было 282/50 302). Распространение —
HuggingFace dataset **`brics-edtech/ip-law-corpus`**: texts.zip (тексты),
embeddings.npy, chunks.jsonl, config.json; SHA-256 — в
`corpus-manifest.json` / `index-manifest.json`. Скачивание: `make
corpus-fetch` (автоматически подтягивает с HF по манифестам).

Верификация цитат — `verification/REPORT.md`.