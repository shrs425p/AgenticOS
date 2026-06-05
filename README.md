# AgenticOS: High-Performance Autonomous Framework

AgenticOS is a secure, high-performance personal AI orchestration framework supporting local and cloud LLMs. It features a zero-trust execution environment with robust, AST-like structural command validation to block unauthorized actions, shell chaining, and obfuscation attacks.

---

## Key Features

- **Zero-Trust Guardrails**: Structural command validator and PathGuard path enforcement.
- **High-Performance Execution**: Native depth-first search disk traversal and zero-lag rendering.
- **Resilient Integration**: Centralized logging, early schema validation, and API rate-limit shields.
- **Dynamic Extensibility**: Decorator-based tool registry with hot-reloading plugin support.

---

## Quick Start

### 1. Installation
Run the automated environment setup script to configure the virtual environment and dependencies:

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

**macOS / Linux (Bash):**
```bash
./setup.sh
```

### 2. Configuration
Open the newly created `.env` file in the root directory and add your API keys (e.g. `GOOGLE_API_KEY`, `NVIDIA_API_KEY`).

### 3. Running the Agent
Start the agent loop from any terminal directory:
```bash
agent
```

---

## Documentation Index

Refer to the technical manuals under `docs/` for deeper architectural and operational guidelines:

- [**Setup Guide**](docs/setup_guide.md): Advanced installation, environment requirements, and troubleshooting.
- [**System Architecture**](docs/architecture.md): Deep dive into the orchestrator loop, memory SQLite backend, and abstractions.
- [**Runtime Configuration**](docs/runtime_configuration.md): Complete guide to layered YAML overrides and environment variables.
- [**Testing Guide**](docs/testing_guide.md): Guide to our automated pytest harness and mock strategies.
- [**Contributor Guide**](docs/contributor_guide.md): Local development guidelines and PR processes.

---

## Project Structure

- `core/`: Core runtime orchestration, database, and security guardrails.
- `tools/`: Categorized tool library (filesystem, terminal, web) and custom plugins.
- `config/`: Layered YAML configuration files.
- `tests/`: Automated test suite.
- `docs/`: Technical manuals and guides.

---

## License

Distributed under the Apache-2.0 License. See `LICENSE` for details.
