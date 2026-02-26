.PHONY: test test-unit test-act help clean

# Default target
.DEFAULT_GOAL := help

# Color output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Environment
VENV ?= venv
PYTHON := $(VENV)/bin/python3
PYTEST := $(VENV)/bin/pytest

##@ Testing

test-unit: ## Run unit tests only (fast, ~1s)
	@echo "$(GREEN)Running unit tests...$(NC)"
	@$(PYTEST) tests/ -v --tb=short
	@echo "$(GREEN)✅ All unit tests passed$(NC)"

test-cli: ## Run CLI specific tests
	@echo "$(GREEN)Running CLI tests...$(NC)"
	@$(PYTEST) tests/test_cli.py -v
	@echo "$(GREEN)✅ CLI tests passed$(NC)"

test-act: ## Run integration test with real Google Sheets (requires secrets)
	@if [ ! -f act_setup/local.secrets ]; then \
		echo "$(RED)❌ Error: act_setup/local.secrets not found$(NC)"; \
		echo "See act_setup/README.md for setup instructions"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running GitHub Actions workflow locally with act...$(NC)"
	@./act_setup/run_update_sheet.sh
	@echo "$(GREEN)✅ Integration test completed$(NC)"

test: test-unit test-act ## Run both unit and integration tests

backfill: ## Backfill historical data (2020-2025). Usage: make backfill ARGS="--start 2020 --end 2025 --dry-run"
	@if [ ! -f act_setup/local.secrets ]; then \
		echo "$(RED)❌ Error: act_setup/local.secrets not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Starting historical backfill (2020-2025)...$(NC)"
	@rm -f .okr_conn_cache.json
	@export PYTHONPATH=src && $(PYTHON) -m egi_okr.backfill $(ARGS)
	@echo "$(GREEN)✅ Backfill completed$(NC)"

##@ Development

clean: ## Remove Python cache and build artifacts
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .coverage htmlcov/ .okr_conn_cache.json 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

##@ Help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  $(YELLOW)make test-unit$(NC)       # Fast unit tests"
	@echo "  $(YELLOW)make test-act$(NC)        # Integration test (requires secrets)"
	@echo "  $(YELLOW)make test$(NC)            # Run all tests"
	@echo "  $(YELLOW)make clean$(NC)           # Clean build artifacts"
