# Корпус курса «Право интеллектуальной собственности»

Корпус — набор текстов под свободными лицензиями и официальных документов
в каталоге `COURSE_CORPUS_ROOT/txt/` (по умолчанию `ip_law_corpus/txt`),
индекс — в `COURSE_CORPUS_ROOT/index/`.

## Состав (186 файлов, расширение 2026-09-13)

| Категория | Файлов | Лицензия |
|---|---|---|
| `oa__*` — научные статьи | 50 | CC BY / BY-SA / BY-NC / BY-ND / BY-NC-ND / BY-NC-SA |
| `wiki_en__*`, `wiki_ru__*` | 78 | CC BY-SA 4.0 |
| `law__*` — договоры и законы | 16 | официальные документы (не объекты АП) |
| `practice__*` — судебная практика | 14 | решения судов (GPL-3.0 датасеты) |
| `pd__*` — трактаты | 11 | общественное достояние |

- **Официальные тексты (не объекты авторского права)**: ГК РФ часть IV;
  Бернская конвенция; **Соглашение ТРИПС** (полный текст); Римская
  конвенция; Конвенция о фонограммах (1971); Конвенция о спутниковом
  вещании (1974); Всемирная конвенция об авторском праве; Статут Анны
  (1709); ACTA; ТПП гл. 18; Кодекс ИС Филиппин; Конвенция УПОВ; ДАП (WCT);
  ДАИФ (WPPT).
- **Wikipedia (CC BY-SA 4.0)**: 17 статей RU + 37 новых EN (DMCA, Fair
  use, Copyright term, Patentability, Novelty, Inventive step, Software
  patent, Biological/Pharmaceutical patent, Compulsory license, Trademark
  infringement, Madrid system, Trade dress, Geographical indication, Utility
  model, Moral rights, Related rights, Sui generis, History of copyright,
  Patent troll, Open access, Creative Commons, Copyleft и др.).
- **Статьи под CC-лицензиями (DOAJ)**: 50 работ по авторскому праву,
  патентам, товарным знакам, ТРИПС, ИИ и праву. Лицензия каждой статьи
  подтверждена через запись журнала и Crossref; манифест —
  `catalog/doaj_law_admitted.json`.
- **Трактаты общественного достояния (Internet Archive, до 1925)**:
  Waite «Patent law» (1920), Thompson «Handbook of patent law of all
  countries» (1920), Simonds «Manual of patent law» (1874), Webster «The
  new patent law» (1853), «History of the International Union for the
  Protection of Industrial Property» (1887, 2 тома), Schreiter «Protection
  of industrial property» (1897), Toulmin (1915), Nims «The law of unfair
  competition and trademarks» (1917), Coca-Cola (1923), Putnam, Birrell.
- **Судебная практика**: 378 решений СИП РФ (датасет
  lawful-good-project/ipc_decisions_4k, GPL-3.0) и 71 решение из
  sud-resh-benchmark (GPL-3.0).

Подробная таблица лицензий по каждому файлу — `docs/corpus-new-sources.md`.

## Пробел, который закрыт не полностью

Парижская конвенция, PCT, Мадридское, Гаагское, Ниццкое и Страсбургское
соглашения **не найдены в полном тексте** в свободных источниках
(Wikisource содержит страницы-дизамбигуации, WIPO Lex отдаёт текст внутри
JS-оболочки). Их нормы излагаются в занятиях как авторский синтез
(«вне корпуса») и иллюстрируются трактатами 1887–1915 гг., где эти
соглашения разобраны постатейно. Пересказ вместо первоисточника в корпус
не подставлялся.

## Сборка корпуса (порядок)

Скрипты сбора (в рабочем пространстве корпуса):
`probe_law_sources.py` (какие источники живы), `fetch_treaties_wikisource.py`
(договоры из Wikisource), `fetch_treaty_parts.py` (многочастные тексты),
`fetch_treaties_wipo.py` (WIPO Lex), `fetch_doaj_law.py` (CC-статьи с
проверкой лицензии), `ia_download.py` (PD-трактаты). В репозитории корпус не
хранится — только `index-manifest.json` с контрольными суммами.

## Индекс

Индекс (модель paraphrase-multilingual-MiniLM-L12-v2, точный косинусный
поиск, чанки 1400/140) распространяется архивом на Google Диске:
**`ip-law-index-2026-09-13-v2.zip`** — **186 файлов, 18 219 чанков**.
Ссылка и SHA-256 находятся в `index-manifest.json`. Размещение описано в
`docs/GOOGLE-DRIVE.md`.

Верификация цитат — `verification/REPORT.md`.
