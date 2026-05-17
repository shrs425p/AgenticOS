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

# 4. Display PATH configuration instructions
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
