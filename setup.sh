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
PYTHON_CMD=""
if command -v python3 > /dev/null; then
    PYTHON_CMD="python3"
elif command -v python > /dev/null; then
    PYTHON_CMD="python"
fi

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_VER=$($PYTHON_CMD --version)
    echo -e "${GRAY}[INFO] Detected Python: $PYTHON_VER${NC}"
    
    # Check if Python version is 3.12+
    if $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
        echo -e "${GREEN}[SUCCESS] Python version requirement (3.12+) met.${NC}"
    else
        echo -e "${YELLOW}[WARNING] Detected Python version is older than 3.12.${NC}"
        PYTHON_CMD="" # Reset so we prompt to install the correct version
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}[WARNING] Python 3.12+ was not found on your system.${NC}"
    read -p "Do you want to download and install Python 3.12 automatically? (y/n): " choice
    case "$choice" in 
        [yY]|[yY][eE][sS])
            if [[ "$OSTYPE" == "darwin"* ]]; then
                if command -v brew > /dev/null; then
                    echo -e "${CYAN}[INFO] Installing Python 3.12 via Homebrew...${NC}"
                    brew install python@3.12
                    PYTHON_CMD="python3"
                else
                    echo -e "${RED}[ERROR] Homebrew is not installed. Please install Homebrew or Python 3.12+ manually.${NC}"
                    exit 1
                fi
            elif command -v apt-get > /dev/null; then
                echo -e "${CYAN}[INFO] Installing Python 3.12 via apt...${NC}"
                sudo apt-get update
                sudo apt-get install -y python3.12 python3.12-venv python3-pip
                PYTHON_CMD="python3"
            else
                echo -e "${RED}[ERROR] Automated installation is not supported on this platform. Please install Python 3.12+ manually.${NC}"
                exit 1
            fi
            
            # Re-verify installation
            if command -v $PYTHON_CMD > /dev/null && $PYTHON_CMD -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
                echo -e "${GREEN}[SUCCESS] Python 3.12+ installed successfully!${NC}"
            else
                echo -e "${RED}[ERROR] Installation completed, but Python 3.12+ is still not detected in your PATH. Please restart your shell and run setup again.${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${YELLOW}[INFO] Installation cancelled. Please install Python 3.12+ manually to continue.${NC}"
            exit 1
            ;;
    esac
fi

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
# 9. Perform System Diagnostic & Health Summary
echo -e "\n${CYAN}[INFO] Running System Diagnostics & Health Checks...${NC}"

DIAGNOSTIC_PASSED=true

# Check Internet Connectivity
if ping -c 1 google.com > /dev/null 2>&1 || curl -s --head https://www.google.com > /dev/null 2>&1; then
    echo -e "${GREEN}[SUCCESS] Network Connection: Online${NC}"
else
    echo -e "${YELLOW}[WARNING] Network Connection: Offline or slow${NC}"
    DIAGNOSTIC_PASSED=false
fi

# Check .env API Keys
PLACEHOLDERS=()
if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z0-9_]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            KEY="${BASH_REMATCH[1]}"
            VAL="${BASH_REMATCH[2]}"
            VAL=$(echo "$VAL" | xargs)
            if [ -z "$VAL" ] || [[ "$VAL" == your_* ]]; then
                PLACEHOLDERS+=("$KEY")
            fi
        fi
    done < "$ENV_FILE"
fi

if [ ${#PLACEHOLDERS[@]} -gt 0 ]; then
    placeholder_str=$(IFS=, ; echo "${PLACEHOLDERS[*]}")
    echo -e "${YELLOW}[WARNING] Credentials Config: Missing / Placeholder keys found ($placeholder_str)${NC}"
    DIAGNOSTIC_PASSED=false
else
    echo -e "${GREEN}[SUCCESS] Credentials Config: Configured${NC}"
fi

# Check Python & venv executables
if [ -f "$PYTHON_EXE_PATH" ] && [ -f "$PIP_PATH" ]; then
    echo -e "${GREEN}[SUCCESS] Virtual Environment: Configured and healthy${NC}"
else
    echo -e "${RED}[ERROR] Virtual Environment: Missing or corrupted executables${NC}"
    DIAGNOSTIC_PASSED=false
fi

# Summary
echo ""
if [ "$DIAGNOSTIC_PASSED" = true ]; then
    echo -e "${GREEN}[SUCCESS] System Health: Perfect! AgenticOS is ready for launch.${NC}"
else
    echo -e "${YELLOW}[WARNING] System Health: Configuration is incomplete. Please see warnings above.${NC}"
fi

# 10. Display PATH configuration instructions
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
