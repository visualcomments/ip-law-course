# Makefile для агента: короткие цели для работы с курсом и корпусом

PY ?= python3
VENV_PY ?= $(PY)

.PHONY: help search index-fetch session assignment verify serve status quotes corpus-fetch corpus-status
.PHONY: law-demo law-run

help:
	@echo "Цели:"
	@echo "  make search QUERY=\"...\"     семантический поиск по корпусу (k=5)"
	@echo "  make corpus-fetch            скачать корпус (индекс + тексты), с проверкой хэшей"
	@echo "  make corpus-status           показать, установлен ли корпус"
	@echo "  make index-fetch URL=\"...\"  совместимость: только индекс"
	@echo "  make session n=18            материалы занятия 18 (текст+цитаты+источники)"
	@echo "  make assignment n=18         вопросы и задания занятия 18"
	@echo "  make verify                  проверка всех цитат курса по корпусу"
	@echo "  make serve port=8765         запуск RAG-API (Ctrl+C — стоп)"
	@echo "  make status                  состояние курса и корпуса"
	@echo "  make law-demo OUT=...        офлайн-демо «закон-графа» (синтетический корпус поправок)"
	@echo "  make law-run OUT=...         «закон-граф» на реальном корпусе (COURSE_CORPUS_ROOT)"

search:
	test -n "$(QUERY)" || (echo "Укажите QUERY=..."; exit 1)
	$(VENV_PY) tools/rag_search.py "$(QUERY)" -k $(K)



session:
	test -n "$(n)" || (echo "Укажите n=НомерЗанятия"; exit 1)
	$(PY) tools/session_material.py $(n)

assignment:
	test -n "$(n)" || (echo "Укажите n=НомерЗанятия"; exit 1)
	$(PY) tools/assignment_brief.py $(n)

verify:
	$(VENV_PY) tools/verify_quotes.py

serve:
	$(VENV_PY) tools/rag_api.py --port $(port)

status:
	$(PY) tools/status.py

quotes:
	$(VENV_PY) tools/quote_finder.py "$(QUERY)"

# --- «Закон-граф»: предиктивный анализ норм права (адаптация top-papers-graph) ---

law-demo:
	$(VENV_PY) -m law_graph.run_dataset --mode synthetic --out $(if $(OUT),$(OUT),runs/law_demo) --export

law-run:
	test -n "$(COURSE_CORPUS_ROOT)" || (echo "Укажите COURSE_CORPUS_ROOT=путь к корпусу (txt/*.txt)"; exit 1)
	$(VENV_PY) -m law_graph.run_dataset --mode corpus --corpus-root "$(COURSE_CORPUS_ROOT)" --out $(if $(OUT),$(OUT),runs/law_corpus) --export

# --- Корпус курса: обязательное получение индекса И текстов -----------------
# Курс не готов к занятиям, пока корпус не установлен: без текстов
# цитируемый фрагмент нечем подтвердить. `make corpus-fetch` вызывается при
# развёртывании (scripts/install.py и botai) и вручную, когда корпуса нет.
corpus-fetch:
	$(PY) tools/corpus_fetch.py $(if $(URL),--url "$(URL)") $(if $(TEXTS_URL),--texts-url "$(TEXTS_URL)") $(if $(FORCE),--force,)

corpus-status:
	$(PY) tools/corpus_fetch.py --status

# Совместимость: старые инструкции и навыки вызывают index-fetch.
index-fetch: corpus-fetch
