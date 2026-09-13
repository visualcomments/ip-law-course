# PROVENANCE — происхождение и лицензии корпуса

Корпус курса «Право интеллектуальной собственности» состоит из текстов
**под свободными лицензиями** и **официальных документов**, которые не
являются объектами авторского права (ст. 1259 ГК РФ): законы и
международные договоры могут свободно цитироваться и использоваться.

## Официальные тексты (не объекты авторского права)

| Файл в `txt/` | Документ | Примечание |
| `law__ГК_РФ_часть_IV.txt` | Гражданский кодекс РФ, часть IV (главы 69–77) | Официальный текст, ФИПС (new.fips.ru) |
|---|---|---|
| `law__Berne_Convention_EN.txt` | Бернская конвенция об охране литературных и художественных произведений (акт 1979) | Официальный текст, WIPO (EN) |
| `law__TRIPS_EN.txt` | Соглашение ТРИПС (ВТО), вводная часть | Официальный текст, ВТО (EN) |

Примечание: полные русские тексты ГК РФ (ч. IV) и постановлений Пленума
ВС РФ публикуются на официальных ресурсах (pravo.gov.ru; vsrf.ru) и в
корпус в этой версии не включены ввиду сетевой недоступности — их нормы
в занятиях излагаются самостоятельно (с пометкой «вне корпуса»), а
нормативные положения иллюстрируются свободными статьями (ниже).

## Судебная практика (не объекты авторского права)

| Файл в `txt/` | Содержание |
|---|---|
| `practice__sip_01..08.txt` | Выборка решений Суда по интеллектуальным правам РФ (378 решений, выборка из датасета lawful-good-project/ipc_decisions_4k, HuggingFace; лицензия датасета GPL-3.0) |
| `practice__bench_01..06.txt` | Наиболее релевантные решения судов РФ по праву ИС (71 решение, отбор по ключевым словам из датасета lawful-good-project/sud-resh-benchmark, HuggingFace, GPL-3.0) |

## Статьи Wikipedia (CC BY-SA 4.0)

| Файл в `txt/` | Статья |
|---|---|
| `wiki_ru__Интеллектуальная_собственность.txt` | Интеллектуальная собственность (ru) |
| `wiki_ru__Интеллектуальные_права.txt` | Интеллектуальные права (ru) |
| `wiki_ru__Авторское_право.txt` | Авторское право (ru) |
| `wiki_ru__Смежные_права.txt` | Смежные права (ru) |
| `wiki_ru__Патент.txt` | Патент (ru) |
| `wiki_ru__Изобретение.txt` | Изобретение (ru) |
| `wiki_ru__Полезная_модель.txt` | Полезная модель (ru) |
| `wiki_ru__Промышленный_образец.txt` | Промышленный образец (ru) |
| `wiki_ru__Товарный_знак.txt` | Товарный знак (ru) |
| `wiki_ru__Общественное_достояние.txt` | Общественное достояние (ru) |
| `wiki_en__Copyright.txt` | Copyright (en) |
| `wiki_en__Patent.txt` | Patent (en) |
| `wiki_en__Trademark.txt` | Trademark (en) |
| `wiki_en__Trade_secret.txt` | Trade secret (en) |
| `wiki_en__Industrial_design_right.txt` | Industrial design right (en) |
| `wiki_en__Public_domain.txt` | Public domain (en) |
| `wiki_en__Berne_Convention.txt` | Berne Convention (en) |
| `wiki_en__Paris_Convention.txt` | Paris Convention (en) |
| `wiki_en__WIPO.txt` | World Intellectual Property Organization (en) |
| `wiki_en__Copyright_infringement.txt` | Copyright infringement (en) |

Статьи распространяются по **CC BY-SA 4.0**
(https://creativecommons.org/licenses/by-sa/4.0/legalcode); при
цитировании указывается источник «Wikipedia (ru/en), статья X,
CC BY-SA 4.0». Тексты получены по `action=raw`, из них удалены разметка
и примечания.

## Книги в общественном достоянии (PD)

| Файл в `txt/` | Автор / произведение | Источник |
|---|---|---|
| `pd__History_of_Copyright.txt` | G. H. Putnam, «The Question of Copyright» — материалы по истории авторского права | Internet Archive, PD |
| `pd__Birrell_Copyright.txt` | A. Birrell, «The Law of Copyright» (1899) | Internet Archive, PD |

## Расширение корпуса 2026-09-13 (индекс 2026-09-13)

Корпус вырос с 35 до **146 файлов** (11,1 МБ); индекс — с 1 940 до
**8 382 чанка**. Добавлено четыре группы источников; подробная таблица с
лицензиями по каждому файлу — в `docs/corpus-new-sources.md`.

### 1. Международные договоры и официальные тексты (`law__*`) — 16 файлов

Не объекты авторского права (ст. 1259 ГК РФ; ст. 2(4) Бернской конвенции).
Добавлены полные тексты: **Соглашение ТРИПС** (части I–III, из подстраниц
Wikisource), **Римская конвенция**, **Конвенция о фонограммах** (Женева,
1971), **Конвенция о спутниковом вещании** (Брюссель, 1974), **Всемирная
конвенция об авторском праве**, **Статут Анны** (1709, первый закон об
авторском праве), **ACTA**, **ТПП гл. 18**, **Кодекс ИС Филиппин**,
**Конвенция УПОВ**, **ДАП (WCT)**, **ДАИФ (WPPT)**.

Не найдены в полном виде в свободных источниках: Парижская конвенция, PCT,
Мадридское, Гаагское, Ниццкое, Страсбургское соглашения (на Wikisource это
страницы-дизамбигуации, WIPO Lex отдаёт текст внутри JS-оболочки).
Пробел компенсирован трактатами группы 2, излагающими эти соглашения
постатейно; пересказ вместо текста в корпус **не** подставлялся.

### 2. Трактаты общественного достояния (`pd__*`) — 12 файлов

Internet Archive, OCR `_djvu.txt`, издания до 1925 г.

| Файл | Произведение | Год |
|---|---|---|
| `pd__patentlaw00waitrich.txt` | Waite, «Patent law» | 1920 |
| `pd__handbookofpatent00thomiala.txt` | Thompson, «Handbook of patent law of all countries» | 1920 |
| `pd__manualofpatentla00simorich.txt` | Simonds, «Manual of patent law» | 1874 |
| `pd__cu31924021862440.txt` | Webster, «The new patent law» (Англия) | 1853 |
| `pd__historyofinterna01unit.txt` | «History of the International Union for the Protection of Industrial Property» | 1887 |
| `pd__historyofinterna00unit.txt` | то же, другой том | 1887 |
| `pd__protectionofindu00schr.txt` | Schreiter, «Protection of industrial property» | 1897 |
| `pd__protectionofindu00toul.txt` | Toulmin, «Protection of industrial property» | 1915 |
| `pd__cu31924019270507.txt` | Nims, «The law of unfair competition and trademarks» | 1917 |
| `pd__cocacolaopinions00cocauoft.txt` | Coca-Cola: судебные решения о товарном знаке | 1923 |

Трактаты 1887 и 1897 гг. о международном союзе по охране промышленной
собственности — прямая предыстория Парижской конвенции.

### 3. Научные статьи под свободными лицензиями (`oa__*`) — 50 файлов

Открытый доступ (DOAJ). **Лицензия проверяется на уровне записи журнала**
(в записи статьи DOAJ поле `license` пустое) и дополнительно подтверждается
через Crossref по DOI. Манифест с лицензией каждой статьи —
`catalog/doaj_law_admitted.json`.

Лицензии: CC BY, CC BY-SA, CC BY-NC, CC BY-ND, CC BY-NC-ND, CC BY-NC-SA.
**Лицензии с NC/ND ограничивают коммерческое использование и производные
произведения** — для учебного корпуса допустимо, но при публикации корпуса
ограничение должно быть указано.

Тематика: история и сроки авторского права, ограничения и исключения, fair
use, авторство ИИ-произведений, смежные права, патентоспособность и
неочевидность, программные и биотех-патенты, принудительные лицензии и
доступ к лекарствам, товарные знаки (включая нетрадиционные и trade dress),
ТРИПС и гармонизация, общественное достояние.

### 4. Статьи Wikipedia (`wiki_en__*`, `wiki_ru__*`) — 54 файла

Добавлено 37 англоязычных статей по темам, не покрытым прежним составом:
DMCA, Fair use, Copyright term, Copyright Clause, Patentability,
Novelty (patent), Inventive step and non-obviousness, Patent application,
Patent infringement, Software patent, Biological patent, Pharmaceutical
patent, Compulsory license, Trademark infringement, Madrid system, Trade
dress, Geographical indication, Utility model, Copyright collective, Moral
rights, Related rights, Sui generis, History of copyright, Copyright Act of
1976, Patent troll, Open access, Creative Commons, Free license, Copyleft и др.

Лицензия **CC BY-SA 4.0**; при цитировании указывать «Wikipedia (en/ru),
статья X, CC BY-SA 4.0».

## Лицензионная чистота

- Только свободные лицензии и официальные документы;
- охраняемые авторским правом современные учебники в корпус не
  включаются (излагаются авторским синтезом «вне корпуса»);
- **«открытый доступ» без заявленной лицензии не является основанием для
  включения**: DOAJ-статьи без подтверждённой лицензии отброшены (проверка
  через журнал и Crossref);
- нежелательные файлы выявляются на этапе верификации и чистки индекса.