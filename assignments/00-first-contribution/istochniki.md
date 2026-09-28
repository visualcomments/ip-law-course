# Источники для базового задания (занятие 03)

Файлы локального корпуса курса (путь — от корня соответствующего репозитория /
рабочей копии корпуса). Цитату берите **дословно** и указывайте координату
`файл · фрагмент #N`.

## ip-law-course (профиль `amendment`)

Материал занятия 03 — объекты авторского права (ст. 1259 ГК РФ):

- `txt/law__ГК_РФ_часть_IV.txt` — официальный текст части IV ГК РФ (цитируется в лекции 03);
- `txt/law__Berne_Convention_EN.txt` — Бернская конвенция (англ.), ст. 2(6) — фрагмент #68;
- `wiki_ru__Авторское_право.txt` — перечень объектов (задание лекции 03).

Упоминания изменений (законов, менявших статьи) — в статьях корпуса:

- `reading_ru/ru__Использование_объектов_авторских_прав_для_обучения_искусственного_инте.txt`
- `reading_ru/ru__Объекты_созданные_с_использованием_искусственного_интеллекта_как_объек.txt`
- `reading_ru/ru__Случайность_или_опережение_времени_судьба_отдельных_изменений_законода.txt`
- `reading_ru/ru__Генеративный_искусственный_интеллект_и_авторское_право_105874123134852.txt`

Историческое (PD, англ.) — пример «изменение закона во времени»:

- `merged/lesson1__Macgillivray_Treatise_on_Copyright.txt` (Copyright Act 1911)
- `merged/wiki_en__History_of_copyright.txt`

**Ищите** упоминания вида «Федеральный закон от … № …-ФЗ», «внесены изменения в
статью …», «статьи … признаны утратившими силу».

## history-of-science-and-technology (профиль `experiment`)

Материал занятия 03 — аграрная революция; количественные данные чаще в смежных
источниках корпуса:

- `txt/history_of_engineering__The_Origins_of_Invention_A_Study_of_Industry_Among_Primitive_Peoples.txt`
  (Мейсон, 1895 — источник лекции 03; фрагменты #16010, #15878);
- `merged/lesson1__Bernard_Experimental_Medicine.txt` — физиологические опыты (числа);
- `merged/lesson1__Faraday_Chemical_History_of_a_Candle.txt` — измерения горения;
- `merged/lesson1__Kelvin_Popular_Lectures.txt` — оценки скоростей молекул;
- `merged/lesson1__Tyndall_Fragments_of_Science.txt` — физические опыты.

Топ тематически близкие OA-статьи (англ., реальные измерения):

- `_pdftext/history-of-science-and-technology__oa__From_Neolithic_Revolution_to_industrialization_10.1017_s136510052300021.txt`
- `_pdftext/history-of-science-and-technology__oa__Beyond_Yields_Structural_Factors_Behind_The_Green_Revolutions_Limited__10.31132_2412-5717-2025-.txt`
- `_pdftext/history-of-science-and-technology__oa__Ancient_technology_and_punctuated_change_Detecting_the_emergence_of_th_10.1371_journal.pone.022.txt`
- `_pdftext/history-of-science-and-technology__oa__Crafts_by_Nomads_of_the_Ural_and_Turgai_Regions_at_the_Beginning_of_th_10.15688_jvolsu4.2021.4..txt`

**Ищите** «число + единица» (`год`, `тыс. лет`, `га`, `%`, `°C`, `м`, `кг`, …),
таблицы и сравнения значений.

> Если корпус локально не развёрнут: `make corpus-status` покажет, что есть;
> `make corpus-fetch` скачает индекс и тексты (с проверкой SHA-256). Пока корпуса
> нет — структура записи проверяется (`validate.py`), а дословность цитаты — нет
> (это «проверить нечем», код 2).
