VENV = env
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
TEST_CMD = $(VENV)/bin/pytest
PSQL = psql

include .env

# Setup the environment
.PHONY: setup
setup: 
	@echo "Setting up virtual environment..."
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

# Install dependencies (from requirements.txt)
.PHONY: install
install: 
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt

# Run the server 
.PHONY: run
run:
	@echo "Running the server..."
	$(eval export TESTING=False)
	$(PYTHON) app/app.py 

# Run tests
.PHONY: test
test: setup-test-db
	@echo "Running tests with pytest..."
	$(eval export TESTING=True)
	$(TEST_CMD) test/tests.py

# Clean up the virtual environment
.PHONY: clean
clean:
	@echo "Cleaning up virtual environment and __pycache__..."
	rm -rf $(VENV)
	rm -rf app/__pycache__
	rm -rf test/__pycache__
	rm -rf .pytest_cache

# Setup the production database
.PHONY: setup-prod-db
setup-prod-db:
	@echo "Setting up the production database..."
	PGPASSWORD=$(DB_PASSWORD) $(PSQL) -h $(DB_HOST) -U $(DB_USER) -f db/prod-database-create.sql

# Setup the testing database
.PHONY: setup-test-db
setup-test-db:
	@echo "Setting up the testing database..."
	PGPASSWORD=$(DB_PASSWORD) $(PSQL) -h $(DB_HOST) -U $(DB_USER) -f db/test-database-create.sql

# Display help
.PHONY: help
help:
	@echo "Usage:"
	@echo "  make setup         - Set up virtual environment and install dependencies"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Run the server"
	@echo "  make test          - Run tests with pytest"
	@echo "  make clean         - Clean up virtual environment and __pycache__"
	@echo "  make setup-test-db - Setup testing database" 
	@echo "  make setup-prod-db - Setup production database" 
