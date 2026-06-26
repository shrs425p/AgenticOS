<!-- generated-by: gsd-doc-writer -->
# Developer Onboarding & Development Guide

Welcome to the AgenticOS developer onboarding guide. This document contains standard practices for contributing code, developing tools/plugins, running formatting tools, and submitting pull requests.

---

## Local Setup

To set up a local development environment:
1. Initialize the virtual environment and install standard requirements:
   - On Windows: `.\setup.ps1`
   - On macOS/Linux: `./setup.sh`
2. Install development packages:
   ```bash
   venv\Scripts\pip install -r requirements-dev.txt
   ```
3. Set environment variable overrides in `.env` to enable dry-run logs or debug level verbosity.

---

## Build & Lint Commands

The project uses Python scripts and standard tools for testing and formatting.

| Command / Script | Description |
|------------------|-------------|
| `venv\Scripts\python main.py --health` | Runs active configuration, connection, and import health checks |
| `venv\Scripts\python main.py --dream` | Executes the self-evolution reflection dream cycle |
| `venv\Scripts\pytest` | Executes the full automated test suite |
| `ruff check .` | Runs ruff linting rules over all python files |
| `ruff format .` | Formats all python code blocks in-place |

---

## Code Style

- **Python Formatter**: We use [Ruff](https://github.com/astral-sh/ruff) for linting and code formatting. The configuration is loaded automatically. Make sure to run `ruff format .` before submitting any changes.
- **Typing**: The codebase utilizes PEP-484 type hints. Run static checks or ensure type annotations exist for all public functions, classes, and helper parameters.
- **Safety Guards**: Every new command executor or filesystem modifier tool must integrate with AST validations and `PathGuard` checks.

---

## Branch Conventions

- **Default Branch**: The main branch is `main`.
- **Naming Convention**:
  - `feat/feature-name` for new features/tools.
  - `fix/bug-fix-name` for bug fixes.
  - `docs/docs-update` for documentation changes.
  - `chore/clean-up` for maintenance operations.

---

## Pull Request Process

1. **Create Branch**: Check out a new branch following the branch conventions.
2. **Implement Changes**: Write clean, modular code. If writing tools, decorate them with `@tool` and register them type-safely.
3. **Write Unit Tests**: Add test assertions in the `tests/` directory matching the naming convention `test_*.py`.
4. **Run Verification**: Ensure all unit tests pass cleanly:
   ```bash
   venv\Scripts\pytest
   ```
5. **Format Check**: Run ruff formatting:
   ```bash
   venv\Scripts\ruff format .
   ```
6. **Submit PR**: Open a Pull Request targeting `main`. Summarize what was built, what was tested, and highlight any new API paths or tool schemas.
