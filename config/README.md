# AgenticOs Config Layout

Keep `../config.yaml` small. It is the user-facing override file.

Advanced defaults live here and are loaded in the explicit order defined by
`CONFIG_LAYERS` in `core/runtime_config.py`:

- `providers.yaml` - local/cloud provider settings and rate limits
- `runtime.yaml` - agent loop, autonomy, heuristics, recovery behavior
- `policy.yaml` - permissions, security, system control, performance policy
- `tools.yaml` - tool switches, custom keys, terminal settings, timeouts
- `storage.yaml` - memory, cache, logging, audit settings
- `prompts.yaml` - system prompt and tool-list prompt sizing

Merge order:

```text
providers.yaml -> runtime.yaml -> policy.yaml -> tools.yaml -> storage.yaml -> prompts.yaml -> ../config.yaml
```

If the same key appears in both places, `../config.yaml` wins.
