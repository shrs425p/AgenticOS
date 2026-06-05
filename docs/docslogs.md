# Documentation Maintenance Logs

## 2026-06-05
- Bumped the overall framework version to `2.2.0` (The "Zero-Trust AST Hardened" Edition) to represent the structural AST command validation and script scanning updates.
- Synchronized version tags across `README.md`, `docs/index.html`, `docs/version_history.md`, `core/runtime.py`, and `tests/test_runtime_zone_cmd.py`.
- Updated test count references and badges in `README.md` to show 494 tests passing.
- Created `docs/command_validation.md` documenting the zero-trust validator, script parser, and PowerShell audits.
- Created `docs/quick_start.md` containing a fast 2-minute setup, CLI run command, and standard agent workflows.
- Created `docs/self_improvement.md` detailing the dreaming reflections engine, logs audits, and offline heuristics.
- Updated existing guides and package-level READMEs to reflect the command validation coordinates and new guides.

## 2026-06-03
- Corrected outdated tool count references from `180+` to `350+` across all active documentation files (`README.md`, `docs/setup_guide.md`, `docs/architecture.md`, `docs/index.html`) to align with the actual `352` registered tools in the `ToolRegistry`.
- Updated disk I/O performance speedup figures from `150x` to `170x` to represent the native Python DFS stack walker benchmarks.
- Replaced the outdated PowerShell pipeline diagram and descriptions in `docs/visual_index.md` with the new stack-based Python `os.scandir` walker flowchart, and resolved a code block formatting rendering bug.
- Updated version reference numbers from `2.1.1` to `2.1.2` in `README.md`, `docs/index.html`, and `docs/version_history.md`.

## 2026-05-22
- Implemented robust Long-Term Memory Filtering & Nonsense Prevention heuristics (`is_meaningful_task`).
- Added early-exit checks to `log_task_completion` to prevent logging trivial conversational greetings/gibberish to daily files (`memory-*.md`) and local task logs.
- Refactored `SelfImprovementDaemon.dream` task reflections to filter out conversational loops using `is_meaningful_task`.
- Programmatically performed retroactive cleanup and visual formatting of historical entries in `workspace/MEMORY.md`.
- Expanded the pytest suite with dedicated unit tests in `tests/test_memory_manager.py` (increasing overall passing test count from 444 to 445).
- Updated status badges and descriptions in `README.md` to reflect 445 tests passed.

## 2026-05-20
- Updated `docs/index.html` to reflect the correct number of tools (180+) in line with `README.md`.
- Updated `docs/index.html` Quick Start instructions to use the automated `setup.ps1` and `setup.sh` scripts instead of manual `pip install` commands.
- Updated `README.md` test counts and status badges to 444 tests passed following Code AST Parser plugin implementation.
- Updated `tests/README.md` to reflect over 440+ comprehensive tests.
- Aligned documentation files and version history dates in `docs/version_history.md`.

## 2026-05-19
- Created `docs/contributor_guide.md` with instructions for dev setup, plugin registration, coding standards, and running tests.
- Removed hardcoded absolute repo paths from core/memory_manager.py, config/prompts.yaml, and tests/test_all_tools_shadow.py.

## 2026-05-18
- Updated documentation across README.md, architecture.md, privacy_data_policy.md, troubleshooting.md, autonomous_operations.md, and security_guardrails.md to reflect recent architectural changes to memory management (ContextEngine, MemoryManager, MEMORY.md), ToolRegistry self-healing, and dynamic plugin loading.
- Generalized references to data/memory.sqlite3 and data/logs to support workspace-relative paths.
- Updated documentation to v2.1.1, removing hardcoded absolute repo paths.
- Added `docs/CATALOG.md` as the canonical documentation index for all Markdown docs.
- Updated `README.md` to point to `docs/CATALOG.md` from the top navigation and Documentation Center.
- Fixed broken local Markdown links in `core/README.md` by replacing absolute file URL paths with repository-relative links.
- Fixed broken local Markdown links in `docs/ultimate_pc_control.md` by replacing absolute file URL paths with repository-relative links.
- Updated `SECURITY.md` with a "Security Documentation Catalog" section linking to security and safety docs.
- Updated `docs/visual_index.md` summary to v2.1.1 and linked it to `docs/CATALOG.md`.
- Updated `task.md` task references from Windows-specific absolute repo paths to `<REPO_ROOT>` and replaced `tools_list` with `/tools`.

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
