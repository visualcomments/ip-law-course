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

## Расширение корпуса 2026-11-07 (индекс 2026-11-07)

Корпус расширен со 186 до **427 файлов**; индекс пересобран на GPU
(torch + sentence-transformers, GTX 1050 Ti). Цель — гарантированное
покрытие каждого из 16 занятий (≥ 10 источников) и закрытие пробелов
прежней версии.

### 1. Международные договоры полным текстом (`law__*`) — +30 файлов

Получены с en.wikisource.org методом **трансклюзии** `action=parse
&prop=text` (HTML включает содержимое постраничных сканов United States
Treaty Series / оригинальных изданий) с конвертацией в plain text:

| Файл | Документ |
|---|---|
| `law__Paris_Convention_1883.txt` | **Парижская конвенция (1883) — полный текст** (закрыт главный пробел) |
| `law__Paris_Convention_1911.txt` | Парижская конвенция, Вашингтонская редакция (1911) |
| `law__European_Patent_Convention.txt` | Конвенция о выдаче европейских патентов (EPC, полный текст, 139K симв.) |
| `law__Unified_Patent_Court_Agreement.txt` | Соглашение о едином патентном суде (94K симв.) |
| `law__TRIPS_Wikisource_*.txt` (12) | Соглашение ТРИПС по всем частям (I–VII) |
| `law__TRIPS_COVID_Waiver.txt` | Ваучер ТРИПС для вакцин COVID-19 (2022) |
| `law__DMCA_Title_I.txt`, `law__DMCA_Title_II.txt` | DMCA: ст. 512 (safe harbor) и 1201 (anti-circumvention) |
| `law__US_Copyright_Act_1976.txt` | Закон США об авторском праве 1976 г. (полный, 210K симв.) |
| `law__Berne_Implementation_Act_1988.txt` | Акт о присоединении США к Бернской конвенции (1988) |
| `law__Rome/Phonograms/Satellite/WCT/WPPT/UCC/Philippines/TPP_*_full.txt` | дубликаты прежних договоров в более полных редакциях |
| `law__US_Reciprocity_Patents.txt` | Закон США о взаимности патентов |

Договоры — официальные документы, не объекты авторского права
(ст. 1259 ГК РФ; ст. 2(4) Бернской конвенции).

### 2. PD-книги (Project Gutenberg, зеркало pglaf) — +12 файлов

| Файл | Произведение |
|---|---|
| `pd__Copinger_Law_of_Copyright_UK.txt` | Copinger, «A Treatise Upon the Law of Copyright in the United Kingdom and the Dominions» (базовый трактат, 1,1 МБ) |
| `pd__Wordsworth_Law_of_Copyright.txt` | W. Wordsworth, «The Law of Copyright» |
| `pd__Putnam_International_Copyright.txt` | G. H. Putnam, «International Copyright» |
| `pd__Warner_Literary_Copyright.txt` | C. D. Warner, «Literary Copyright» |
| `pd__Abolition_of_Patents_Discussions.txt` | «Recent Discussions on the Abolition of Patents» (GB/FR/DE/NL) |
| `pd__US_Patents_and_How_to_Get_One.txt` | «Patents and How to Get One» (US Dept. of Commerce) |
| `pd__Thompson_Things_to_Know_About_Trade_Marks.txt` | «Things to Know About Trade-Marks» |
| `pd__Arguments_Patents_Copyright_1904/1906.txt` | Парламентские слушания Комитета по патентам США |
| `pd__US_Patent_Office_Classification.txt` | Классификация патентов USPTO |
| `pd__Patent_Laws_Hawaii.txt` | Патентные законы Республики Гавайи |
| `pd__US_Copyright_Law_Circular_92.txt` | Title 17 USC, Circular 92 (полный) |

Все — общественное достояние (издания 1879–1976 до PG-подтверждения PD;
заголовки Gutenberg удалены).

### 3. Wikipedia (CC BY-SA 4.0) — +68 файлов

RU (26): Лицензионный договор, Договор об отчуждении…, Исполнитель,
Фонограмма, Мадридское соглашение, Гаагское соглашение, Страсбургское
соглашение, Европейская и Евразийская патентные конвенции, Патентный
тролль, Копилефт, Плагиат, Бернская конвенция, Всемирная конвенция, ВОИС,
Договор о патентной кооперации, Коммерческая тайна, Ноу-хау,
Географическое указание, Creative Commons, Открытый доступ, Патентное
право, Промышленный образец, Полезная модель, Интеллектуальные права,
Электронная библиотека, Свободное ПО, Формула изобретения, Роспатент,
ФИПС, Евразийская патентная организация, Международная патентная
классификация, Патентный поверенный.

EN (42): Patent claim/application/prosecution/examiner/office action,
Prior art, Provisional application, Patent family, Priority right, Unity
of invention, Divisional/Continuation application, Search report,
Copyright transfer agreement, Neighbouring rights, Anti-circumvention,
Plagiarism, Copyright infringement, Moral rights, Droit de suite,
Parallel importation, Exhaustion, Database right, Sony v. Universal,
Feist, Campbell v. Acuff-Rose, Eldred v. Ashcroft, Trademark dilution,
Well-known trademark, Certification/Collective mark, Domain name,
Cybersquatting, Geographical indication, Traditional knowledge, Biopiracy,
Gene patent, Oncomouse, Myriad, Compulsory licence, Crown copyright,
Watermark, DRM, DMCA и др.

Каждый файл начинается с заголовка атрибуции CC BY-SA 4.0
(источник, лицензия, ссылка на legalcode).

### 4. OA-статьи DOAJ (CC BY / CC BY-SA) — +13 файлов

Новая выборка 2026-11-07 принимает **только CC BY / CC BY-SA** (NC/ND
варианты отклонены, чтобы корпус оставался свободно распространяемым).
Тематика: оригинальность и вдохновение, срок авторского права,
вознаграждение исполнителей и фонограммных продюсеров, налогообложение
прав исполнителей, общеизвестные товарные знаки, text and data mining,
юридический анализ чат-ботов и ИИ. Манифесты —
`catalog/doaj-manifest-2026-11-07.json` и
`catalog/doaj-extra-2026-11-07.json` (152 записи: 83 с полным текстом,
остальные — с абстрактом для контроля релевантности).

### Проверка покрытия

Карта `catalog/sources-map.json` (генератор — `build_sources_map.py`)
фиксирует **≥ 10 источников на каждое из 16 занятий**: минимум — занятие
06 (13), максимум — занятие 09 (88).