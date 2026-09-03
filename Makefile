# Makefile для агента: короткие цели для работы с курсом и корпусом

PY ?= python3
VENV_PY ?= $(PY)

.PHONY: help search index-fetch session assignment verify serve status quotes

help:
	@echo "Цели:"
	@echo "  make search QUERY=\"...\"     семантический поиск по корпусу (k=5)"
	@echo "  make index-fetch URL=\"...\"  скачать/развернуть индекс с Google Диска"
	@echo "  make session n=18            материалы занятия 18 (текст+цитаты+источники)"
	@echo "  make assignment n=18         вопросы и задания занятия 18"
	@echo "  make verify                  проверка всех цитат курса по корпусу"
	@echo "  make serve port=8765         запуск RAG-API (Ctrl+C — стоп)"
	@echo "  make status                  состояние курса и корпуса"

search:
	test -n "$(QUERY)" || (echo "Укажите QUERY=..."; exit 1)
	$(VENV_PY) tools/rag_search.py "$(QUERY)" -k $(K)

index-fetch:
	$(PY) tools/index_fetch.py $(if $(URL),--url "$(URL)")


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