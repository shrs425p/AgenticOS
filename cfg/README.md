# AgenticOs Config Layout

Keep `../cfg.yaml` small. It is the user-facing override file.

Advanced defaults live here and are loaded in the explicit order defined by
`CONFIG_LAYERS` in `kernel/settings.py`:

- `providers.yaml` - local/cloud provider settings and rate limits
- `runtime.yaml` - agent loop, autonomy, heuristics, recovery behavior
- `policy.yaml` - permissions, security, system control, performance policy
- `ops.yaml` - tool switches, custom keys, terminal settings, timeouts
- `storage.yaml` - memory, cache, logging, audit settings
- `prompts.yaml` - system prompt and tool-list prompt sizing

Merge order:

```text
providers.yaml -> runtime.yaml -> policy.yaml -> ops.yaml -> storage.yaml -> prompts.yaml -> ../cfg.yaml
```

If the same key appears in both places, `../cfg.yaml` wins.
