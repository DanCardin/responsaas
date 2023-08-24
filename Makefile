.PHONY: install test lint format build publish

PACKAGE_VERSION = $(shell python -c 'import importlib.metadata; print(importlib.metadata.version("responsaas"))')

install:
	poetry install --with server -E pmr

test:
	coverage run -m pytest src tests
	coverage combine
	coverage report
	coverage xml

lint:
	ruff src tests || exit 1
	mypy src tests || exit 1
	black --check --diff src tests || exit 1

format:
	ruff --fix src tests
	black src tests

build: build38 build39 build310 build311

build38:
	 python_version=3.8 make buildversion

build39:
	 python_version=3.9 make buildversion

build310:
	 python_version=3.10 make buildversion

build311:
	 python_version=3.11 make buildversion
	 docker tag dancardin/responsaas:py3.11-$(PACKAGE_VERSION) dancardin/responsaas:latest

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

publish: publish38 publish39 publish310 publish311

publish38:
	 python_version=3.8 make publishversion

publish39:
	 python_version=3.9 make publishversion

publish310:
	 python_version=3.10 make publishversion

publish311:
	 python_version=3.11 make publishversion
	 docker push dancardin/responsaas:latest

publishversion:
	docker push "dancardin/responsaas:py${python_version}-$(PACKAGE_VERSION)"
