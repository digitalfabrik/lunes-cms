TOOLS := ./tools

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "; printf "Lunes CMS — make targets\n\n"} \
	     /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)

.PHONY: install
install: ## Install CMS into local venv
	$(TOOLS)/install.sh

.PHONY: install-clean
install-clean: ## Wipe venv and reinstall
	$(TOOLS)/install.sh --clean

.PHONY: install-pre-commit
install-pre-commit: ## Install + register pre-commit hooks
	$(TOOLS)/install.sh --pre-commit

.PHONY: run
run: ## Start dev server (migrate, translate first)
	$(TOOLS)/run.sh

.PHONY: run-fast
run-fast: ## Start dev server, skip migrate/translate
	$(TOOLS)/run.sh --fast

.PHONY: test
test: ## Run pytest with coverage
	$(TOOLS)/test.sh

.PHONY: black
black: ## Format code with black
	$(TOOLS)/black.sh

.PHONY: isort
isort: ## Sort imports with isort
	$(TOOLS)/isort.sh

.PHONY: pylint
pylint: ## Run pylint
	$(TOOLS)/pylint.sh

.PHONY: mypy
mypy: ## Run mypy type check
	$(TOOLS)/mypy.sh

.PHONY: format
format: black isort ## Run black + isort

.PHONY: lint
lint: pylint mypy ## Run pylint + mypy

.PHONY: translate
translate: ## Regenerate + compile translation file
	$(TOOLS)/translate.sh

.PHONY: check-translations
check-translations: ## Verify translation file is up to date
	$(TOOLS)/check_translations.sh

.PHONY: resolve-translation-conflicts
resolve-translation-conflicts: ## Auto-resolve .po merge conflicts
	$(TOOLS)/resolve_translation_conflicts.sh

.PHONY: load-test-data
load-test-data: ## Load fixtures into the database
	$(TOOLS)/load_test_data.sh

.PHONY: docs
docs: ## Build Sphinx documentation
	$(TOOLS)/build_documentation.sh

.PHONY: docs-clean
docs-clean: ## Clean build of documentation
	$(TOOLS)/build_documentation.sh --clean
