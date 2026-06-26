# Context: Phase 1 (Remove Bloated Filesystem Tools)

## Scope & Requirements
- Identify and remove bloated filesystem ops (like `read_file`, `write_file`, `append_file`, `delete_file`, etc.) that can be handled directly by terminal execution.
- Maintain kernel terminal, process, git, and search ops.
- Ensure that the agent can successfully perform all file operations via standard terminal commands (e.g. `cat`, `echo`, python script execution).
- Update tool registries and spec to align with the removal of these ops.

## Key Decisions
- Modify `FileManager` in `ops/filesystem/__init__.py` to remove/disable editing, mutations, and read/write mixins (`ReadWriteMixin`, `EditMixin`, `MutationsMixin`).
- Retain structured search, listing, and grep ops if they provide unique semantic or structured value that terminal ops don't natively return.
- Fix/remove/mock unit spec that rely on the deleted filesystem ops.
