.PHONY: install test lint format build publish

PACKAGE_VERSION = $(shell grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

install:
	uv sync --extra pmr --extra server

test:
	uv run coverage run -m pytest src tests
	uv run coverage combine
	uv run coverage report
	uv run coverage xml

lint:
	uv run ruff check src tests || exit 1
	uv run mypy src tests || exit 1
	uv run black --check --diff src tests || exit 1

format:
	uv run ruff check --fix src tests
	uv run black src tests

build: build39 build310 build311 build312

build39:
	python_version=3.9 make buildversion

build310:
	python_version=3.10 make buildversion

build311:
	python_version=3.11 make buildversion

build312:
	python_version=3.12 make buildversion
	docker tag dancardin/responsaas:py3.12-$(PACKAGE_VERSION) dancardin/responsaas:latest

buildversion:
	sed -r "s!%%PYTHON_VERSION%%!${python_version}!g;" Dockerfile.template > .Dockerfile
	image_tag="dancardin/responsaas:py${python_version}-$(PACKAGE_VERSION)"; \
	docker build \
		-t "$${image_tag}" \
		-f .Dockerfile \
		--cache-from type=gha,scope="$(GITHUB_REF_NAME)-$${image_tag}" \
		--cache-to type=gha,mode=max,scope="$(GITHUB_REF_NAME)-$${image_tag}" \
		--output type=docker \
		.

publish: publish39 publish310 publish311 publish312

publish39:
	python_version=3.9 make publishversion

publish310:
	python_version=3.10 make publishversion

publish311:
	python_version=3.11 make publishversion

publish312:
	python_version=3.12 make publishversion
	docker push dancardin/responsaas:latest

publishversion:
	docker push "dancardin/responsaas:py${python_version}-$(PACKAGE_VERSION)"
