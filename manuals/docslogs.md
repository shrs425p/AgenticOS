# Documentation Maintenance Logs

## 2026-06-05
- Bumped the overall framework version to `2.2.0` (The "Zero-Trust AST Hardened" Edition) to represent the structural AST command validation and script scanning updates.
- Synchronized version tags across `README.md`, `manuals/index.html`, `manuals/history.md`, `kernel/cli.py`, and `spec/runtimezonecmdspec.py`.
- Updated test count references and badges in `README.md` to show 494 spec passing.
- Created `manuals/commands.md` documenting the zero-trust validator, script parser, and PowerShell audits.
- Created `manuals/quick.md` containing a fast 2-minute setup, CLI run command, and standard agent workflows.
- Created `manuals/improve.md` detailing the dreaming reflections engine, logs audits, and offline heuristics.
- Updated existing guides and package-level READMEs to reflect the command validation coordinates and new guides.

## 2026-06-03
- Corrected outdated tool count references from `180+` to `350+` across all active documentation files (`README.md`, `manuals/setup.md`, `manuals/architecture.md`, `manuals/index.html`) to align with the actual `352` registered ops in the `ToolRegistry`.
- Updated disk I/O performance speedup figures from `150x` to `170x` to represent the native Python DFS stack walker benchmarks.
- Replaced the outdated PowerShell pipeline diagram and descriptions in `manuals/visual.md` with the new stack-based Python `os.scandir` walker flowchart, and resolved a code block formatting rendering bug.
- Updated version reference numbers from `2.1.1` to `2.1.2` in `README.md`, `manuals/index.html`, and `manuals/history.md`.

## 2026-05-22
- Implemented robust Long-Term Memory Filtering & Nonsense Prevention heuristics (`is_meaningful_task`).
- Added early-exit checks to `log_task_completion` to prevent logging trivial conversational greetings/gibberish to daily files (`memory-*.md`) and local task logs.
- Refactored `SelfImprovementDaemon.dream` task reflections to filter out conversational loops using `is_meaningful_task`.
- Programmatically performed retroactive cleanup and visual formatting of historical entries in `workspace/MEMORY.md`.
- Expanded the pytest suite with dedicated unit spec in `spec/memorymanagerspec.py` (increasing overall passing test count from 444 to 445).
- Updated status badges and descriptions in `README.md` to reflect 445 spec passed.

## 2026-05-20
- Updated `manuals/index.html` to reflect the correct number of ops (180+) in line with `README.md`.
- Updated `manuals/index.html` Quick Start instructions to use the automated `setup.ps1` and `setup.sh` scripts instead of manual `pip install` commands.
- Updated `README.md` test counts and status badges to 444 spec passed following Code AST Parser plugin implementation.
- Updated `spec/README.md` to reflect over 440+ comprehensive spec.
- Aligned documentation files and version history dates in `manuals/history.md`.

## 2026-05-19
- Created `manuals/contribute.md` with instructions for dev setup, plugin registration, coding standards, and running spec.
- Removed hardcoded absolute repo paths from kernel/memory.py, cfg/prompts.yaml, and spec/alltoolsshadowspec.py.

## 2026-05-18
- Updated documentation across README.md, architecture.md, privacy.md, troubleshooting.md, autonomy.md, and guard.md to reflect recent architectural changes to memory management (ContextEngine, MemoryManager, MEMORY.md), ToolRegistry self-healing, and dynamic plugin loading.
- Generalized references to data/memory.sqlite3 and data/logs to support workspace-relative paths.
- Updated documentation to v2.1.1, removing hardcoded absolute repo paths.
- Added `manuals/CATALOG.md` as the canonical documentation index for all Markdown manuals.
- Updated `README.md` to point to `manuals/CATALOG.md` from the top navigation and Documentation Center.
- Fixed broken local Markdown links in `kernel/README.md` by replacing absolute file URL paths with repository-relative links.
- Fixed broken local Markdown links in `manuals/control.md` by replacing absolute file URL paths with repository-relative links.
- Updated `SECURITY.md` with a "Security Documentation Catalog" section linking to security and safety manuals.
- Updated `manuals/visual.md` summary to v2.1.1 and linked it to `manuals/CATALOG.md`.
- Updated `task.md` task references from Windows-specific absolute repo paths to `<REPO_ROOT>` and replaced `opslist` with `/ops`.

## 2026-05-17
- Fixed broken tool references in `manuals/api.md` and `manuals/setup.md`
- Replaced non-existent `opslist` command with `/ops` in manuals
- Replaced `fastdiskaudit` and `eventlogquery` in `troubleshooting.md` with existing ops
- Added `presets.yaml` to the configuration list in `runtime.md`
- Updated all references to version numbers like `v2.0` and `v2.1` to `v2.0.0`

## 2026-05-16
- Updated `README.md` to correct the tool count badge from 50 to 180.
- Updated `README.md` to correct the test count badge from 98_passed to 387_passed.
- Updated `README.md` main description to correct the tool count from 50 to 180.
- Updated `README.md` "API & Tool Reference" link description to correct the tool count from 50 to 180.
- Updated `README.md` to point "Autonomous Test Suite" link to existing `manuals/testing.md` instead of the broken `manuals/test_suite.md`.
- Updated `manuals/api.md` to correct the tool count statement from 300+ to 180+.
- Created `kernel/README.md` with a brief description.
- Created `ops/README.md` with a brief description.
- Created `workspace/README.md` with a brief description.
- Created `manuals/manualslogs.md` to track future documentation changes.
