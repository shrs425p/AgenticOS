# Context: Phase 1 (Remove Bloated Filesystem Tools)

## Scope & Requirements
- Identify and remove bloated filesystem tools (like `read_file`, `write_file`, `append_file`, `delete_file`, etc.) that can be handled directly by terminal execution.
- Maintain core terminal, process, git, and search tools.
- Ensure that the agent can successfully perform all file operations via standard terminal commands (e.g. `cat`, `echo`, python script execution).
- Update tool registries and tests to align with the removal of these tools.

## Key Decisions
- Modify `FileManager` in `tools/filesystem/__init__.py` to remove/disable editing, mutations, and read/write mixins (`ReadWriteMixin`, `EditMixin`, `MutationsMixin`).
- Retain structured search, listing, and grep tools if they provide unique semantic or structured value that terminal tools don't natively return.
- Fix/remove/mock unit tests that rely on the deleted filesystem tools.
