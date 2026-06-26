# Context: Phase 4 (Memory, Extensibility, and Resiliency Harness)

## Scope & Requirements
- **MEM-01**: Semantic vector storage matching (numpy IVF).
- **MEM-02**: Exponential decay functions with 30-day half-life.
- **MEM-03**: Episodic memory clustering (numpy K-Means centroids).
- **MEM-04**: Evidence field validation.
- **MEM-05**: Cross-instance memory sharing.
- **EXT-01**: Async tool protocol execution.
- **EXT-02**: Streaming tool outputs.
- **EXT-03**: Remote plugin downloader.
- **EXT-04**: Tool dependency version resolver.
- **EXT-05**: Tool piping composers.
- **TEST-01**: E2E multi-step workflows.
- **TEST-02**: Mutation test validation.
- **TEST-03**: Performance regression benchmarks.
- **TEST-04**: Chaos monkey test harness.

## Key Decisions
- No external FAISS library dependency: implement IVF partition index using numpy K-Means clustering.
- Embeddings default to local math/hash offline generators if keys are missing.
- Async execution handled via `asyncio` inside dispatcher wave executors.
