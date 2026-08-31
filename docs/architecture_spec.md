# Architecture Spec (Draft — Day 1)

Placeholder for the exported architecture diagram (Task 1A, Roma + Pranay).
Add the final PNG/PDF export here as `architecture_diagram.png` /
`architecture_diagram.pdf`.

## Pipeline overview

```
MAUDE Ingestion (Agent 1)
      |
Product Identity Normalization (Agent 2)
      |
Regulatory Context (Agent 3) --- Scope Validation (Agent 4)
      |
Rate Engine (pure Python, deterministic)
      |
Document Impact Analysis (Agent 5)
      |
Human Decision Gate  <-- DISMISS | INVESTIGATE FURTHER | CONFIRM
      |
Safety Action Pack (DRAFT ONLY) --> QMS handoff
```

## Non-negotiables
- The human decision gate sits **before** any QMS action. No agent may
  bypass it.
- Rate engine refuses to compute on missing/zero denominators rather than
  guessing.
- All LLM outputs (Agents 1, 2, 5) are cached via `CacheManager` so the
  demo can replay entirely offline at $0 cost.
- Safety Action Packs are always labeled `DRAFT` — never auto-published.
