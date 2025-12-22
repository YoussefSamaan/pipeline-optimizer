#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

MODE=$1

setup_and_test() {
    echo -e "${GREEN}Starting Backend Setup...${NC}"
    
    # Read configuration from config.yml
    if [ -f "config.yml" ]; then
        COVERAGE_THRESHOLD=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend'].get('coverage_threshold', 90))" 2>/dev/null || echo "90")
        RUN_LINT=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend'].get('checks', {}).get('lint', True))" 2>/dev/null || echo "True")
        RUN_FORMAT=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend'].get('checks', {}).get('format', True))" 2>/dev/null || echo "True")
        RUN_TYPE=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend'].get('checks', {}).get('type_check', True))" 2>/dev/null || echo "True")
        RUN_TEST=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend'].get('checks', {}).get('test', True))" 2>/dev/null || echo "True")
    else
        COVERAGE_THRESHOLD="90"
        RUN_LINT="True"
        RUN_FORMAT="True"
        RUN_TYPE="True"
        RUN_TEST="True"
    fi

    cd backend

    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install requirements
    echo "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    # Read configuration from config.yml (now that PyYAML is available in venv)
    # Config is in root, so we use ../config.yml
    if [ -f "../config.yml" ]; then
        COVERAGE_THRESHOLD=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('coverage_threshold', 90))" 2>/dev/null || echo "90")
        RUN_LINT=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('checks', {}).get('lint', True))" 2>/dev/null || echo "True")
        RUN_FORMAT=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('checks', {}).get('format', True))" 2>/dev/null || echo "True")
        RUN_TYPE=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('checks', {}).get('type_check', True))" 2>/dev/null || echo "True")
        RUN_TEST=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('checks', {}).get('test', True))" 2>/dev/null || echo "True")
    else
        COVERAGE_THRESHOLD="90"
        RUN_LINT="True"
        RUN_FORMAT="True"
        RUN_TYPE="True"
        RUN_TEST="True"
    fi

    # 1. Linting (Ruff)
    if [ "$RUN_LINT" == "True" ]; then
        echo "Running Lint Check (ruff)..."
        if ! ruff check .; then
            echo -e "${RED}Linting failed. Please run 'ruff check --fix .'${NC}"
            exit 1
        fi
    else
        echo "Skipping Lint Check..."
    fi

    # 2. Formatting Check (Ruff)
    if [ "$RUN_FORMAT" == "True" ]; then
        echo "Running Format Check (ruff)..."
        if ! ruff format --check .; then
            echo -e "${RED}Formatting failed. Please run 'ruff format .'${NC}"
            exit 1
        fi
    else
        echo "Skipping Format Check..."
    fi

    # 3. Type Checking (Mypy)
    if [ "$RUN_TYPE" == "True" ]; then
        echo "Running Type Check (mypy)..."
        if ! mypy . --ignore-missing-imports; then
            echo -e "${RED}Type checking failed.${NC}"
            exit 1
        fi
    else
        echo "Skipping Type Check..."
    fi

    # Run tests with coverage
    if [ "$RUN_TEST" == "True" ]; then
        echo "Running tests (Threshold: ${COVERAGE_THRESHOLD}%)..."
        export PYTHONPATH=$PYTHONPATH:.
        if pytest --cov=app --cov-fail-under=$COVERAGE_THRESHOLD tests/; then
            echo -e "${GREEN}Backend tests passed with >${COVERAGE_THRESHOLD}% coverage!${NC}"
        else
            echo -e "${RED}Backend tests failed or coverage <${COVERAGE_THRESHOLD}%. Aborting.${NC}"
            exit 1
        fi
    else
        echo "Skipping Tests..."
    fi
    cd ..
}

run_server() {
    echo -e "${BLUE}Starting Backend Server...${NC}"
    
    # Read port from config.yml
    if [ -f "config.yml" ]; then
        PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend']['port'])" 2>/dev/null || echo "8000")
    else
        PORT="8000"
    fi

    cd backend
    source venv/bin/activate

    PORT=$PORT python -m app.main
}


if [ "$MODE" == "test" ]; then
    setup_and_test
elif [ "$MODE" == "run" ]; then
    setup_and_test
    run_server
else
    setup_and_test
    run_server
fi
