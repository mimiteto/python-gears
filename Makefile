TEST_CASE ?=
APP_NAME := gears 
red = \033[31m
color_reset = \033[0m
SHELL := /bin/bash
OS := $(shell uname -s)

ifeq ($(OS),Linux)
	OPEN := xdg-open
else ifeq ($(OS),Darwin)
	OPEN := open
else ifeq ($(OS),Windows_NT)
	OPEN := start
else
	OPEN := echo
endif

.PHONY: venv
venv: venv-build venv-update

.PHONY: venv-build
venv-build:
	python3 -m venv .venv

.PHONY: venv-destroy
venv-destroy:
	deactivate || true
	rm -rf .venv

.PHONY: ensure-venv
ensure-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo -e "$(red)Activate yout venv with:$(color_reset) source .venv/bin/activate"; \
		exit 1; \
	fi

.PHONY: venv-update
venv-update:
	source .venv/bin/activate && pip install -r requirements.txt -r resources/dev-requirements.txt --upgrade
	pip install .

.PHONY: lint
lint: ensure-venv lint-python
	flake8 --exclude=.venv,dist,docs,resources --ignore=E501

.PHONY: lint-python
lint-python: ensure-venv
	flake8 --exclude=htmlcov,.venv,dist,docs,resources .
	find . -name "*.py" -not -path "./.venv/*" | xargs pylint
	radon cc . --min B -j -s | jq .
	radon mi . --min B --max F

.PHONY: qtest
qtest: ensure-venv
	rm -rf htmlcov
	pytest --cov=$(APP_NAME) --cov=tests --cov-report=html:htmlcov .
	$(OPEN) htmlcov/index.html

.PHONE: build
build: ensure-venv
	hatch build

.PHONY: test
test: lint qtest

