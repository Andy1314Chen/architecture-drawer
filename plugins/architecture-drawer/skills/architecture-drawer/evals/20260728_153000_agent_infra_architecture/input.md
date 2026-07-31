# Agent Infrastructure — Layered Architecture

Draw a 5-layer horizontal stack (top → bottom) representing an AI agent
infrastructure platform, with a cross-cutting band on the right.

## Layers (top → bottom)

1. **Application** — end-user facing apps and interfaces.
2. **Orchestration** — agent coordination, session management, routing.
3. **Core Capabilities** — the 5 core modules (highlighted with accent colors):
   memory, planning, tool-use, retrieval, evaluation.
4. **Execution & Environment** — runtime, sandboxing, resource management.
5. **Infrastructure** — compute, storage, networking foundation.

## Cross-cutting band (right side)

- **Observability** — logging, tracing, metrics spanning all layers.
- **Security** — auth, access control, audit spanning all layers.

## Design

- Palette: 5-accent categorical for the core modules; neutral grays elsewhere.
- Each layer is a container rect with a header label and component cards inside.
- Bilingual labels (CN title + EN subtitle) per layer.
- Font tiers: 20 / 14 / 12 / 10.
