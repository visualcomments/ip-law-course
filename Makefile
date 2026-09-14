# Makefile для агента: короткие цели для работы с курсом и корпусом

PY ?= python3
VENV_PY ?= $(PY)
K ?= 5
port ?= 8010

.PHONY: help tools-install search index-fetch session assignment verify serve status quotes corpus-fetch corpus-status
.PHONY: law-demo law-run
.PHONY: legal-calibration-validate legal-calibration-export legal-calibration-pr

LEGAL_CALIB_DIR ?= legal-agent-calibration
LEGAL_CALIB_CLI ?= $(LEGAL_CALIB_DIR)/scripts/legal_calibration_session.py
LEGAL_CALIB_REPO ?= lawful-good-project/legal-agent-calibrations

help:
	@echo "Цели:"
	@echo "  make tools-install            установить зависимости инструментов"
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
	@echo "  make legal-calibration-validate JOURNAL=... проверка калибровочной сессии юр-агента"
	@echo "  make legal-calibration-export JOURNAL=... OUT=...  публичный экспорт сессии"
	@echo "  make legal-calibration-pr JOURNAL=...  публикация экспорта на HuggingFace (HF_TOKEN)"

tools-install:
	$(VENV_PY) -m pip install -r tools/requirements.txt

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

# --- Калибровка юридического агента: отдельное первое задание эксперта --------
# Полное задание — legal-agent-calibration/docs/EXPERT-CALIBRATION.md.
# Это не юридическая консультация; публикуется только публичный (редактированный)
# экспорт, токен читается только из HF_TOKEN и никогда не выводится.
legal-calibration-validate:
	test -n "$(JOURNAL)" || (echo "Укажите JOURNAL=путь к session.jsonl"; exit 1)
	$(PY) $(LEGAL_CALIB_CLI) validate --journal "$(JOURNAL)"

legal-calibration-export:
	test -n "$(JOURNAL)" || (echo "Укажите JOURNAL=путь к session.jsonl"; exit 1)
	test -n "$(OUT)" || (echo "Укажите OUT=путь к публичному session.jsonl"; exit 1)
	$(PY) $(LEGAL_CALIB_CLI) export --journal "$(JOURNAL)" --out "$(OUT)"

legal-calibration-pr:
	test -n "$(JOURNAL)" || (echo "Укажите JOURNAL=путь к session.jsonl"; exit 1)
	test -n "$(HF_TOKEN)" || (echo "Нет HF_TOKEN — публикация не выполняется"; exit 1)
	$(PY) $(LEGAL_CALIB_DIR)/publish.py --journal "$(JOURNAL)" --repo-id "$(LEGAL_CALIB_REPO)"

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
