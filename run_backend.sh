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
    
    cd backend

    # 1. Ensure venv exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # 2. Activate venv
    source venv/bin/activate

    # 3. Install/Update dependencies
    echo "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    # 4. Read configuration from root config.yml (now that PyYAML is definitely in venv)
    local CONFIG_PATH="../config.yml"
    if [ -f "$CONFIG_PATH" ]; then
        COVERAGE_THRESHOLD=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH'))['backend'].get('coverage_threshold', 90))" 2>/dev/null || echo "90")
        RUN_LINT=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH'))['backend'].get('checks', {}).get('lint', True))" 2>/dev/null || echo "True")
        RUN_FORMAT=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH'))['backend'].get('checks', {}).get('format', True))" 2>/dev/null || echo "True")
        RUN_TYPE=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH'))['backend'].get('checks', {}).get('type_check', True))" 2>/dev/null || echo "True")
        RUN_TEST=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH'))['backend'].get('checks', {}).get('test', True))" 2>/dev/null || echo "True")
    else
        COVERAGE_THRESHOLD="90"
        RUN_LINT="True"
        RUN_FORMAT="True"
        RUN_TYPE="True"
        RUN_TEST="True"
    fi

    # 5. Linting (Ruff)
    if [ "$RUN_LINT" == "True" ]; then
        echo "Running Lint Check (ruff)..."
        if ! ruff check .; then
            echo -e "${RED}Linting failed. Run './run_backend.sh fix' to attempt automatic fixes.${NC}"
            exit 1
        fi
    else
        echo "Skipping Lint Check..."
    fi

    # 6. Formatting Check (Ruff)
    if [ "$RUN_FORMAT" == "True" ]; then
        echo "Running Format Check (ruff)..."
        if ! ruff format --check .; then
            echo -e "${RED}Formatting failed. Run './run_backend.sh fix' to reformat code.${NC}"
            exit 1
        fi
    else
        echo "Skipping Format Check..."
    fi

    # 7. Type Checking (Mypy)
    if [ "$RUN_TYPE" == "True" ]; then
        echo "Running Type Check (mypy)..."
        if ! mypy . --ignore-missing-imports; then
            echo -e "${RED}Type checking failed.${NC}"
            exit 1
        fi
    else
        echo "Skipping Type Check..."
    fi

    # 8. Run tests with coverage
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

fix_code() {
    echo -e "${BLUE}Running Auto-Fixers (Ruff)...${NC}"
    cd backend
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -q ruff

    echo "Fixing linting issues..."
    ruff check --fix . || true
    echo "Formatting code..."
    ruff format .
    echo -e "${GREEN}Code fixed and reformatted!${NC}"
    cd ..
}


run_server() {
    echo -e "${BLUE}Starting Backend Server...${NC}"
    
    cd backend 2>/dev/null || true
    if [ ! -d "venv" ]; then
        echo "Environment not found. Running setup..."
        cd ..
        setup_and_test
        cd backend
    fi
    source venv/bin/activate

    # Read port from config.yml
    if [ -f "../config.yml" ]; then
        PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml'))['backend'].get('port', 8000))" 2>/dev/null || echo "8000")
    else
        PORT="8000"
    fi

    # Run server
    echo -e "${GREEN}API documentation available at http://localhost:${PORT}/docs${NC}"
    PORT=$PORT python3 -m app.main
}



if [ "$MODE" == "test" ]; then
    setup_and_test
elif [ "$MODE" == "fix" ]; then
    fix_code
elif [ "$MODE" == "run" ]; then
    run_server
else
    setup_and_test
    run_server
fi
