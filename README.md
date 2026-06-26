<!-- generated-by: gsd-doc-writer -->
# AgenticOS: High-Performance Autonomous Framework

[![Status](https://img.shields.io/badge/status-production_stable-orange?style=flat-square)](https://github.com/shrs425p/AgenticOS)
[![Latest Version](https://img.shields.io/github/v/release/shrs425p/AgenticOS?style=flat-square&label=latest)](https://github.com/shrs425p/AgenticOS)
[![License](https://img.shields.io/badge/license-Apache_2.0-red?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows_|_macOS_|_Linux-blue?style=flat-square)](#)

AgenticOS is a secure, high-performance personal AI orchestration framework designed to empower AI agents with direct, secure, and robust execution capabilities on local operating system runtimes (Windows, macOS, Linux). It seamlessly integrates local models (Ollama) and cloud providers (NVIDIA, Google Gemini, Groq, OpenAI) with a modular ecosystem of specialized ops.

---

## Installation

To install AgenticOS and set up the local environment:

### Prerequisites
- Python >= 3.10
- Git

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/shrs425p/AgenticOS.git
   cd AgenticOS
   ```
2. Run the platform-specific installer script (which sets up the virtual environment, installs dependencies, and copies configurations):
   - **On Windows (PowerShell):**
     ```powershell
     .\setup.ps1
     ```
   - **On macOS/Linux (Bash):**
     ```bash
     chmod +x setup.sh
     ./setup.sh
     ```

---

## Quick Start

1. **Verify Setup:** Run the built-in system diagnostics and reachability check:
   ```bash
   venv\Scripts\python main.py --health
   ```
   *(On macOS/Linux, run `source venv/bin/activate` followed by `python main.py --health`)*

2. **Configure Provider:** Copy `.env.example` to `.env` and configure your API keys (e.g. `NVIDIA_API_KEY`, `GEMINI_API_KEY`) or ensure Ollama is running locally at `http://localhost:11434`.

3. **Run the Runtime:** Start the main agent orchestration loop:
   ```bash
   venv\Scripts\python main.py
   ```

4. **Self-Reflection (Dream Cycle):** Run the performance reflection tuner:
   ```bash
   venv\Scripts\python main.py --dream
   ```

---

## Usage Examples

### Command Line Interface

```bash
# Run in dry-run mode (runs the orchestrator without executing modifying ops)
python main.py --dry-run

# Run active health check to diagnose platform dependencies
python main.py --health

# Run the self-evolution dream cycle to optimize performance metrics
python main.py --dream
```

---

## Contributing

See [manuals/contribute.md](file:///c:/Users/pawar/AgenticOS/manuals/contribute.md) for contribution guidelines, branch conventions, and PR processes.

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
