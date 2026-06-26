<!-- generated-by: gsd-doc-writer -->
# Contributor Guide

Thank you for your interest in contributing to AgenticOS! This document outlines general guidelines for reporting bugs, submitting features, and preparing pull requests.

---

## Development Setup

For initial installation and workspace preparation:
- Follow the [Setup Guide](file:///c:/Users/pawar/AgenticOS/manuals/setup.md) to set up Python and install required scripts.
- Refer to the [Developer Onboarding Guide](file:///c:/Users/pawar/AgenticOS/manuals/onboard.md) for local dev dependencies and code verification commands.

---

## Coding Standards

To maintain code quality across the codebase:
- **Linting & Formatting**: We use Ruff to format Python files. Run formatting before making commits:
  ```bash
  ruff format .
  ```
- **Type Safety**: All new functions and abstractions should include type annotations under PEP-484.
- **Tool Development**: Decorate your system or custom ops using `@tool` from `kernel/base.py` and register them in the registry.

---

## Pull Request Guidelines

When submitting a Pull Request:
1. Fork the repository and create a new branch from `main` following our branch naming patterns (e.g. `feat/feature-name`, `fix/bug-name`).
2. Implement your changes. Ensure you write robust unit spec under `spec/` matching your new feature's domain.
3. Verify that all 612 spec in the test suite pass successfully:
   ```bash
   venv\Scripts\pytest
   ```
4. Run formatting checks:
   ```bash
   ruff check .
   ruff format .
   ```
5. Commit messages should be clear and concise (e.g., following Conventional Commits format like `feat(platform): add linux screenshot helper`).
6. Push your branch and open a PR. Provide a description of the problem solved, testing methodologies used, and validation results.

---

## Issue Reporting

If you encounter bugs, security issues, or have feature requests:
- Open a GitHub issue detailing:
  - Clear steps to reproduce the problem.
  - Expected behavior vs actual outcomes.
  - Runtime environment details (Python version, Operating System, configured provider).
  - Relevant logs or stack traces from the `data/logs/` directory.
