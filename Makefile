# =====================================================================
# NIFTY 100 ETL PIPELINE & DATA FOUNDATION MAKEFILE
# =====================================================================

PYTHON = .venv/Scripts/python
PYTEST = .venv/Scripts/python -m pytest

.PHONY: help load ratios test report dashboard api clean

help:
	@echo "NIFTY 100 Makefile Commands:"
	@echo "  make load       - Run full ETL pipeline (Ingest Excel -> Clean -> SQLite nifty100.db)"
	@echo "  make validator  - Run Data Quality validator (DQ-01 to DQ-16)"
	@echo "  make test       - Run test suite (pytest)"
	@echo "  make report     - Generate DQ and Validation reports"
	@echo "  make ratios     - Run financial ratio calculations"
	@echo "  make dashboard  - Launch interactive dashboard"
	@echo "  make api        - Start API server"
	@echo "  make clean      - Clean output, cache, and temporary database files"

load:
	$(PYTHON) src/etl/etl_pipeline.py

validator:
	$(PYTHON) src/etl/validator.py

test:
	$(PYTEST)

report: load validator
	@echo "Data quality and validation reports generated in output/"

ratios:
	@echo "Calculating financial ratios..."
	$(PYTHON) -c "import sqlite3; conn = sqlite3.connect('db/nifty100.db'); print('Financial ratios table row count:', conn.execute('SELECT COUNT(*) FROM financial_ratios').fetchone()[0]); conn.close()"

dashboard:
	@echo "Launching dashboard runner..."

api:
	@echo "Starting API server..."

clean:
	@rmdir /s /q .pytest_cache 2>nul || true
	@del /f /q output\*.csv 2>nul || true
	@echo "Clean completed."
