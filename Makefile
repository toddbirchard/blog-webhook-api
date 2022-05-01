PROJECT_NAME := $(shell basename $CURDIR)
VIRTUAL_ENVIRONMENT := $(CURDIR)/.venv
LOCAL_PYTHON := $(VIRTUAL_ENVIRONMENT)/bin/python3

define HELP
Manage $(PROJECT_NAME). Usage:

make run        - Run $(PROJECT_NAME) locally.
make install    - Create local virtualenv & install dependencies.
make deploy     - Set up project & run locally.
make update     - Update dependencies via Poetry and output resulting `requirements.txt`.
make format     - Run Python code formatter & sort dependencies.
make lint       - Check code formatting with flake8.
make clean      - Remove extraneous compiled files, caches, logs, etc.

endef
export HELP


.PHONY: run install deploy update format lint clean help

env: ./.venv/bin/activate


all help:
	@echo "$$HELP"


.PHONY: run
run: env
	if [[ "./asgi.py" ]]; then service $(PROJECT_NAME) start; else $(LOCAL_PYTHON) asgi.py; fi


.PHONY: install
install:
	if [ ! -d "./.venv" ]; then python3 -m venv $(VIRTUAL_ENVIRONMENT); fi
	. .venv/bin/activate
	$(LOCAL_PYTHON) -m pip install --upgrade pip setuptools wheel
	$(LOCAL_PYTHON) -m pip install -r requirements.txt


.PHONY: deploy
deploy:
	make clean
	make install
	make run


.PHONY: test
test: env
	$(LOCAL_PYTHON) -m \
		coverage run -m pytest -v \
		--disable-pytest-warnings \
		&& coverage html --title='Coverage Report' -d .reports \
		&& open .reports/index.html


.PHONY: update
update:
	export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=true
	if [ ! -d "./.venv" ]; then python3 -m venv $(VIRTUAL_ENVIRONMENT); fi
	.venv/bin/python3 -m pip install --upgrade pip setuptools wheel
	poetry update
	poetry export -f requirements.txt --output requirements.txt --without-hashes


.PHONY: format
format: env
	isort --multi-line=3 .
	black .


.PHONY: lint
lint:
	$(LOCAL_PYTHON) -m flake8 . --count \
			--select=E9,F63,F7,F82 \
			--exclude .git,.github,__pycache__,.pytest_cache,.venv,logs,creds,.venv,docs,logs,.reports \
			--show-source \
			--statistics


.PHONY: clean
clean:
	find . -name 'poetry.lock' -delete
	find . -name '.coverage' -delete
	find . -wholename '**/*.pyc' -delete
	find . -wholename '__pycache__' -delete
	find . -type d -wholename '.venv' -exec rm -rf {} +
	find . -type d -wholename '.pytest_cache' -exec rm -rf {} +
	find . -type d -wholename '**/.pytest_cache' -exec rm -rf {} +
	find . -type d -wholename './logs/*' -exec rm -rf {} +
	find . -type d -wholename './.reports/*' -exec rm -rf {} +
