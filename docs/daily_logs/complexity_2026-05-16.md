# Complexity Report 2026-05-16

## Top 10 Most Complex Functions
| Function | File | Score | Risk Level |
|---|---|---|---|
| Agent.run | core/runtime.py | 147 | CRITICAL |
| ToolRegistry.call | core/tool_registry.py | 46 | CRITICAL |
| parse_actions | core/runtime_ui.py | 44 | CRITICAL |
| CLI.handle_command | core/runtime.py | 42 | CRITICAL |
| NvidiaClient.chat | core/model_clients.py | 37 | CRITICAL |
| MemoryManager._generate_insights_from_tasks | core/memory_manager.py | 28 | CRITICAL |
| OpenersMixin.find_app | tools/terminal/openers.py | 27 | CRITICAL |
| Agent.__init__ | core/runtime.py | 26 | CRITICAL |
| validate_tool | core/validators.py | 26 | CRITICAL |
| CLI.select_model | core/runtime.py | 25 | CRITICAL |

## Files with Low Maintainability Index (< 20)
- core/tool_registry.py (CRITICAL)
- core/model_clients.py (CRITICAL)
- core/runtime.py (CRITICAL)
- tools/web/browser.py (CRITICAL)

## Functions Over 50 Lines (Refactor Candidates)
- Agent.run in core/runtime.py (611 lines)
- ToolRegistry.call in core/tool_registry.py (125 lines)
- parse_actions in core/runtime_ui.py (215 lines)
- CLI.handle_command in core/runtime.py (199 lines)
- NvidiaClient.chat in core/model_clients.py (162 lines)
- MemoryManager._generate_insights_from_tasks in core/memory_manager.py (88 lines)
- OpenersMixin.find_app in tools/terminal/openers.py (79 lines)
- Agent.__init__ in core/runtime.py (134 lines)
- validate_tool in core/validators.py (89 lines)
- CLI.select_model in core/runtime.py (72 lines)
- SelfImprovementDaemon._generate_reflections in core/self_improvement.py (76 lines)
- YouTubeMixin.find_youtube_video in tools/web/youtube.py (62 lines)
- OpenersMixin.launch_application in tools/terminal/openers.py (79 lines)
- SearchMixin._ddg_html_search in tools/web/search.py (64 lines)
- Agent._reload_everything in core/runtime.py (78 lines)
- load_config in core/runtime_config.py (78 lines)
- ToolRegistry.download_smart in core/tool_registry.py (65 lines)
- AuditLogger.paths_from_event in core/audit_logger.py (58 lines)
- GeminiClient.chat in core/model_clients.py (66 lines)
- KeyboardMixin.mouse_click in tools/terminal/keyboard.py (51 lines)
- CLI.run in core/runtime.py (73 lines)
- MemoryManager._update_long_term_memory in core/memory_manager.py (71 lines)
- ContextEngine.build_system_prompt in core/context_engine.py (86 lines)
- web_pick_best_link in tools/web/web_pick_best_link.py (56 lines)
- TaskTracker._task_markdown in core/task_tracker.py (90 lines)
- SelfImprovementDaemon.dream in core/self_improvement.py (61 lines)
- BrowserMixin.browser_launch in tools/web/browser.py (58 lines)
- fast_disk_audit in tools/plugins/fast_disk.py (77 lines)
- MediaMixin.media_status in tools/terminal/media.py (67 lines)
- MediaMixin.volume_set in tools/terminal/media.py (62 lines)
- SqliteSessionMemory.add in core/session_memory_sqlite.py (56 lines)
- Agent.verify_action in core/runtime.py (56 lines)
- ContextEngine.compact_history in core/context_engine.py (64 lines)
- KeyboardMixin.hotkey in tools/terminal/keyboard.py (67 lines)
- MediaMixin.volume_get in tools/terminal/media.py (89 lines)
- AuditLogger.tool_call in core/audit_logger.py (54 lines)
- SqliteSessionMemory._init_schema in core/session_memory_sqlite.py (98 lines)

## Overall Complexity Trend vs Yesterday
No previous data to compare.

**Complexity Health**: CRITICAL
