#!/bin/bash
# AgenticOS: Environment Configuration Script for Linux/macOS
# This script initializes the project structure and prepares the global launcher.

# Bold colors for terminal output
CYAN='\033[1;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No Color

# Get the script directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${CYAN}[INFO] Configuring AgenticOS environment for Unix/Linux/macOS...${NC}"

# 1. Check if the directory exists
if [ ! -d "$PROJECT_ROOT" ]; then
    echo -e "${RED}[ERROR] Project directory not found at $PROJECT_ROOT.${NC}"
    exit 1
fi

# 2. Create required directories
echo -e "${WHITE}[INFO] Initializing project structure...${NC}"
DIRS=("workspace" "data" "data/logs" "bin")
for dir in "${DIRS[@]}"; do
    path="$PROJECT_ROOT/$dir"
    if [ ! -d "$path" ]; then
        mkdir -p "$path"
        echo -e "${GRAY}[INFO] Created directory: $dir${NC}"
    fi
done

# 2b. Auto-generate workspace README.md if missing
WORKSPACE_README="$PROJECT_ROOT/workspace/README.md"
README_TEMPLATE="$PROJECT_ROOT/config/workspace_readme_template.md"
if [ ! -f "$WORKSPACE_README" ] && [ -f "$README_TEMPLATE" ]; then
    cp "$README_TEMPLATE" "$WORKSPACE_README"
    echo -e "${GRAY}[INFO] Automatically generated workspace README.md from template.${NC}"
fi

# 3. Ensure launcher script is executable
BIN_PATH="$PROJECT_ROOT/bin"
LAUNCHER="$BIN_PATH/agent"
if [ -f "$LAUNCHER" ]; then
    chmod +x "$LAUNCHER"
    echo -e "${GREEN}[INFO] Set execution permissions for $LAUNCHER${NC}"
else
    echo -e "${RED}[ERROR] Launcher script not found at $LAUNCHER${NC}"
    exit 1
fi

# 4. Verify Python Installation
echo -e "${WHITE}[INFO] Verifying Python installation...${NC}"
if command -v python3 > /dev/null; then
    PYTHON_CMD="python3"
elif command -v python > /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python was not found on your system. Please install Python 3.12+ first.${NC}"
    exit 1
fi
PYTHON_VER=$($PYTHON_CMD --version)
echo -e "${GRAY}[INFO] Detected Python: $PYTHON_VER${NC}"

# 5. Initialize Virtual Environment
VENV_PATH="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${WHITE}[INFO] Creating Python virtual environment (venv)...${NC}"
    $PYTHON_CMD -m venv "$VENV_PATH"
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}[ERROR] Failed to create virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}[SUCCESS] Virtual environment created successfully.${NC}"
else
    echo -e "${GRAY}[INFO] Virtual environment already exists.${NC}"
fi

# 6. Install Python Dependencies
PIP_PATH="$VENV_PATH/bin/pip"
PYTHON_EXE_PATH="$VENV_PATH/bin/python"
PLAYWRIGHT_PATH="$VENV_PATH/bin/playwright"

if [ ! -f "$PIP_PATH" ] || [ ! -f "$PYTHON_EXE_PATH" ]; then
    echo -e "${RED}[ERROR] Virtual environment executables not found. Please delete 'venv' folder and run setup again.${NC}"
    exit 1
fi

echo -e "${WHITE}[INFO] Upgrading pip inside virtual environment...${NC}"
"$PYTHON_EXE_PATH" -m pip install --upgrade pip

REQ_FILE="$PROJECT_ROOT/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    echo -e "${WHITE}[INFO] Installing Python dependencies from requirements.txt...${NC}"
    "$PIP_PATH" install -r "$REQ_FILE"
fi

REQ_DEV_FILE="$PROJECT_ROOT/requirements-dev.txt"
if [ -f "$REQ_DEV_FILE" ]; then
    echo -e "${WHITE}[INFO] Installing development dependencies from requirements-dev.txt...${NC}"
    "$PIP_PATH" install -r "$REQ_DEV_FILE"
fi

# 7. Install Playwright Chromium Browser
if [ -f "$PLAYWRIGHT_PATH" ]; then
    echo -e "${WHITE}[INFO] Installing Playwright Chromium browser...${NC}"
    "$PLAYWRIGHT_PATH" install chromium
else
    echo -e "${YELLOW}[WARNING] Playwright executable not found. Skipping Playwright installation.${NC}"
fi

# 8. Configure Credentials (.env)
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
    if [ -f "$ENV_EXAMPLE" ]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo -e "${GREEN}[SUCCESS] Automatically generated .env file from template.${NC}"
        
        if command -v xdg-open > /dev/null; then
            echo -e "${CYAN}[INFO] Opening .env file in default GUI editor...${NC}"
            xdg-open "$ENV_FILE" &
        elif command -v open > /dev/null; then
            echo -e "${CYAN}[INFO] Opening .env file in default GUI editor...${NC}"
            open "$ENV_FILE" &
        elif command -v nano > /dev/null; then
            echo -e "${CYAN}[INFO] Please edit the newly created .env file to configure your API keys.${NC}"
        fi
    fi
else
    echo -e "${GRAY}[INFO] .env file is already configured.${NC}"
fi

# 9. Display PATH configuration instructions
echo -e "\n${WHITE}[INFO] To register the 'agent' command globally, add it to your shell configuration:${NC}"

SHELL_RC=""
if [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

echo -e "${GRAY}Detected shell: $SHELL (Config file: $SHELL_RC)${NC}"
echo -e "\n${YELLOW}Run the following commands to update your path:${NC}"
echo -e "${CYAN}echo 'export AGENTICOS_HOME=\"$PROJECT_ROOT\"' >> $SHELL_RC${NC}"
echo -e "${CYAN}echo 'export PATH=\"\$PATH:$BIN_PATH\"' >> $SHELL_RC${NC}"
echo -e "${CYAN}source $SHELL_RC${NC}"

echo -e "\n${GREEN}[SUCCESS] Environment initialization complete!${NC}"
echo -e "${YELLOW}[TIP] Once path is configured, you can launch the agent from anywhere by running 'agent'.${NC}"
