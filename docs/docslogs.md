# Documentation Maintenance Logs

## 2026-05-20
- Updated `docs/index.html` to reflect the correct number of tools (180+) in line with `README.md`.
- Updated `docs/index.html` Quick Start instructions to use the automated `setup.ps1` and `setup.sh` scripts instead of manual `pip install` commands.
- Updated `README.md` test counts and status badges to 444 tests passed following Code AST Parser plugin implementation.
- Updated `tests/README.md` to reflect over 440+ comprehensive tests.
- Aligned documentation files and version history dates in `docs/version_history.md`.

## 2026-05-19
- Created `docs/contributor_guide.md` with instructions for dev setup, plugin registration, coding standards, and running tests.
- Removed hardcoded C:\AgenticOs paths from core/memory_manager.py, config/prompts.yaml, and tests/test_all_tools_shadow.py.

## 2026-05-18
- Updated documentation across README.md, architecture.md, privacy_data_policy.md, troubleshooting.md, autonomous_operations.md, and security_guardrails.md to reflect recent architectural changes to memory management (ContextEngine, MemoryManager, MEMORY.md), ToolRegistry self-healing, and dynamic plugin loading.
- Generalized references to data/memory.sqlite3 and data/logs to support workspace-relative paths.
- Updated documentation to v2.1.1, removing hardcoded C:\AgenticOs paths.
- Added `docs/CATALOG.md` as the canonical documentation index for all Markdown docs.
- Updated `README.md` to point to `docs/CATALOG.md` from the top navigation and Documentation Center.
- Fixed broken local Markdown links in `core/README.md` by replacing `file:///c:/...` paths with repository-relative links.
- Fixed broken local Markdown links in `docs/ultimate_pc_control.md` by replacing `file:///c:/...` paths with repository-relative links.
- Updated `SECURITY.md` with a "Security Documentation Catalog" section linking to security and safety docs.
- Updated `docs/visual_index.md` summary to v2.1.1 and linked it to `docs/CATALOG.md`.
- Updated `task.md` task references from Windows-specific `C:\\AgenticOs` paths to `<REPO_ROOT>` and replaced `tools_list` with `/tools`.

## 2026-05-17
- Fixed broken tool references in `docs/api_reference.md` and `docs/setup_guide.md`
- Replaced non-existent `tools_list` command with `/tools` in docs
- Replaced `fast_disk_audit` and `eventlog_query` in `troubleshooting.md` with existing tools
- Added `url_presets.yaml` to the configuration list in `runtime_configuration.md`
- Updated all references to version numbers like `v2.0` and `v2.1` to `v2.0.0`

## 2026-05-16
- Updated `README.md` to correct the tool count badge from 50 to 180.
- Updated `README.md` to correct the test count badge from 98_passed to 387_passed.
- Updated `README.md` main description to correct the tool count from 50 to 180.
- Updated `README.md` "API & Tool Reference" link description to correct the tool count from 50 to 180.
- Updated `README.md` to point "Autonomous Test Suite" link to existing `docs/testing_guide.md` instead of the broken `docs/test_suite.md`.
- Updated `docs/api_reference.md` to correct the tool count statement from 300+ to 180+.
- Created `core/README.md` with a brief description.
- Created `tools/README.md` with a brief description.
- Created `workspace/README.md` with a brief description.
- Created `docs/docslogs.md` to track future documentation changes.
