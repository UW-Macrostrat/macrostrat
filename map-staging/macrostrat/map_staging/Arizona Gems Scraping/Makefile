PYTHON := python3
VENV   := .venv
PIP    := $(VENV)/bin/pip
PY     := $(VENV)/bin/python

SCRIPT := new_arizona_gdb_scraper.py

.PHONY: venv install run clean

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install requests beautifulsoup4 tqdm

run: install
	$(PY) $(SCRIPT)

clean:
	rm -rf $(VENV)

