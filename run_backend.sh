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
    
    # Read coverage threshold from config.yml
    if [ -f "config.yml" ]; then
        COVERAGE_THRESHOLD=$(python3 -c "import yaml; print(yaml.safe_load(open('config.yml'))['backend']['coverage_threshold'])" 2>/dev/null || echo "90")
    else
        COVERAGE_THRESHOLD="90"
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

    # Run tests with coverage
    echo "Running tests (Threshold: ${COVERAGE_THRESHOLD}%)..."
    export PYTHONPATH=$PYTHONPATH:.
    # Fail if coverage is under threshold
    if pytest --cov=app --cov-fail-under=$COVERAGE_THRESHOLD tests/; then
        echo -e "${GREEN}Backend tests passed with >${COVERAGE_THRESHOLD}% coverage!${NC}"
    else
        echo -e "${RED}Backend tests failed or coverage <${COVERAGE_THRESHOLD}%. Aborting.${NC}"
        exit 1
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
    # Run server specifying the port from config
    PORT=$PORT python -m app.main
}


if [ "$MODE" == "test" ]; then
    setup_and_test
elif [ "$MODE" == "run" ]; then
    # Even in run mode, we should confirm tests pass for strict enforcement if user wants it
    # But usually 'run' is after 'test'. Let's follow the request strictly: "if not to not build and run"
    setup_and_test
    run_server
else
    setup_and_test
    run_server
fi
