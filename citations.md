# Citations — правила цитирования и карта «занятие → источники»

Курс опирается на верифицированный корпус (см. `CORPUS.md`). Прямые
цитаты — только из корпуса, дословно (OCR-нормализация пробелов и
переносов допустима), с координатами «файл · фрагмент #N»; покрытие
≥ 0.92 по `tools/verify_quotes.py`.

## Контракт

- Официальные документы (законы, договоры, судебные акты) не являются
  объектами авторского права (ст. 1259 ГК РФ) — их можно цитировать
  свободно.
- Статьи Wikipedia (CC BY-SA 4.0) — атрибуция «Wikipedia (ru/en), статья
  X, CC BY-SA 4.0».
- Книги PD (Putnam, Birrell) — свободны.
- Охраняемые авторским правом учебники и монографии по праву ИС в корпус
  не включаются; их положения излагаются авторским синтезом «вне корпуса».

## Карта «занятие → источники»

Актуальная полная карта с автопроверкой ≥ 10 источников на занятие —
`catalog/sources-map.json`. Ниже — основные источники по занятиям.

| Занятие | Основные источники (файлы корпуса) |
|---|---|
| 01 | `wiki_ru__Интеллектуальная_собственность.txt`, `wiki_ru__Общественное_достояние.txt`, `law__ГК_РФ_часть_IV.txt` (ст. 1225), `wiki_en__Intellectual_property.txt`, `pd__*Shairer*`, OA-статьи (public domain) |
| 02 | `pd__Birrell_Copyright.txt`, `pd__Copinger_Law_of_Copyright_UK.txt`, `pd__Putnam_International_Copyright.txt`, `pd__Warner_Literary_Copyright.txt`, `pd__Wordsworth_Law_of_Copyright.txt`, `law__Statute_of_Anne.txt`, `wiki_en__History_of_copyright.txt`, `wiki_ru__Бернская_конвенция…txt`, `wiki_en__Copyright.txt` |
| 03 | `law__Berne_Convention_EN.txt` (ст. 2(6)), `law__ГК_РФ_часть_IV.txt` (ст. 1259), `wiki_ru__Авторское_право.txt`, `wiki_en__Originality.txt`, OA: ARTISTIC CREATIONS. ORIGINALITY |
| 04 | `wiki_ru__Авторское_право.txt`, `law__ГК_РФ_часть_IV.txt` (ст. 1255), `wiki_en__Moral_rights.txt`, `wiki_en__Copyright_authorship…txt` |
| 05 | `wiki_ru__Авторское_право.txt`, `law__Berne_Convention_EN.txt` (ст. 7), `law__US_Copyright_Act_1976.txt`, `wiki_en__Fair_use.txt`, `wiki_en__Copyright_term*.txt`, OA: THE DURATION OF RIGHTS CONFERRED BY COPYRIGHT |
| 06 | `wiki_ru__Лицензионный_договор.txt`, `wiki_ru__Договор_об_отчуждении…txt`, `wiki_ru__Creative_Commons.txt`, `wiki_ru__Копилефт.txt`, `wiki_en__Copyright_transfer_agreement.txt`, `wiki_en__License.txt`, OA: A JURIDICAL STUDY OF COPYRIGHT TRANSFER STATEMENTS |
| 07 | `wiki_ru__Смежные_права.txt`, `wiki_ru__Исполнитель.txt`, `wiki_ru__Фонограмма.txt`, `law__Rome_Convention_EN/full.txt`, `law__WPPT_EN/full.txt`, `wiki_en__Related_rights.txt`, OA: PERFORMERS/PHONOGRAM PRODUCERS |
| 08 | `wiki_ru__Плагиат.txt`, `wiki_en__Copyright_infringement.txt`, `law__DMCA_Title_I.txt`, `law__DMCA_Title_II.txt`, `wiki_en__Anti-circumvention.txt`, `wiki_en__Sony_Corp_v_Universal…txt`, практика СИП |
| 09 | `wiki_ru__Патент.txt`, `law__Paris_Convention_1883.txt` (полный текст!), `law__Paris_Convention_1911.txt`, `law__European_Patent_Convention.txt`, `law__TRIPS_Wikisource_*.txt`, `wiki_en__Patent.txt`, `pd__Abolition_of_Patents_Discussions.txt` |
| 10 | `wiki_ru__Патент.txt`, `wiki_ru__Изобретение.txt`, `wiki_ru__Полезная_модель.txt`, `wiki_ru__Промышленный_образец.txt`, `wiki_en__Novelty/Inventive_step/Software_patent.txt` |
| 11 | `wiki_ru__Формула_изобретения.txt`, `wiki_ru__Роспатент.txt`, `wiki_ru__Международная_патентная_классификация.txt`, `wiki_en__Patent_claim.txt`, `wiki_en__Patent_application.txt`, `wiki_en__Prior_art.txt`, `wiki_en__Patent_prosecution.txt`, `pd__US_Patents_and_How_to_Get_One.txt` |
| 12 | `law__ГК_РФ_часть_IV.txt` (ст. 1363), `wiki_ru__Патент.txt`, `wiki_en__Compulsory_licence.txt`, `wiki_en__Exhaustion_of_intellectual_property_rights.txt`, `wiki_en__Parallel_importation.txt`, практика СИП |
| 13 | `wiki_ru__Изобретение.txt`, `law__UPOV_Convention.txt`, `wiki_en__Biological_pat.txt`, `wiki_en__Gene_patent.txt`, `wiki_en__Oncomouse.txt`, `wiki_en__Myriad_Genetics.txt`, `wiki_en__Biopiracy.txt`, `wiki_en__Traditional_knowledge.txt` |
| 14 | `wiki_ru__Товарный_знак.txt`, `wiki_ru__Мадридское_соглашение…txt`, `wiki_ru__Гаагское_соглашение…txt`, `wiki_ru__Ниццкое_соглашение.txt`?, `wiki_en__Trademark.txt`, `wiki_en__Trademark_dilution.txt`, `wiki_en__Well-known_trade_mark.txt`, `pd__Thompson_Things_to_Know_About_Trade_Marks.txt`, OA: WELL-KNOWN AND REPUTED TRADEMARK |
| 15 | `law__Berne_Convention_EN.txt`, `law__TRIPS_Wikisource_*.txt`, `law__Paris_Convention_*.txt`, `wiki_ru__Всемирная_организация_интеллектуальной_собственности.txt`, `wiki_en__Berne_Convention.txt`, `wiki_en__Paris_Convention…txt`, практика СИП и судов РФ |
| 16 | итог: `wiki_ru__Интеллектуальная_собственность.txt`, `wiki_ru__Интеллектуальные_права.txt`, OA: THE INTEGRATION OF AI IN DOCTORAL-LEVEL RESEARCH; эссе по всем источникам курса |

Полный перечень файлов корпуса и лицензии — в `PROVENANCE.md` и
`CORPUS.md`; контрольные суммы — в `index-manifest.json`; автоматическая
верификация — `verification/REPORT.md`.