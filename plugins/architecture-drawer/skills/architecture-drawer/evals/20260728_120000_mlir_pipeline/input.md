# MLIR AI Compiler — Multi-Stream Execution Pipeline

Draw a 4-layer MATRIX diagram of an AI-compiler runtime pipeline. Four
horizontal layer bands stack top → bottom (the matrix rows); within each band
stages and streams read left → right (the matrix columns). A vertical numbered
spine on the far left links the four bands into one downward flow.

## Structure

A matrix grid: 4 horizontal layers (top → bottom) × multiple stage columns
(left → right). Data and execution flow left → right inside every band.

### Layer 1 — Graph Optimization (compile-time · static DAG & fusion)
- Operator fusion, algebraic reordering, parallel-branch detection.
- A 3-node DAG (**Conv** → **BatchNorm** → **ReLU**) feeding an **Add** node; a
  parallel branch (no data dependency) feeds Add's second input.
- Vertical-fusion group drawn as a dashed box around Conv+BN+ReLU → fused into
  one kernel **K1**. A curved reorder-swap arc marks a commutative D↔C swap.

### Layer 2 — Runtime Scheduling (async launch · priority · load balance)
- A host-side **Task Scheduler** (CPU) fans out to three device streams:
  **Stream 0** · Comm (high priority), **Stream 1** · Compute (kernel queue),
  **Stream 2** · D2D Copy (low priority).
- Each stream owns a device-side queue of small task chips (T / K / cp).

### Layer 3 — Hardware Concurrency (multi-stream overlap · SM partition)
- A GPU **SM array** (4×4 grid) partitioned into MPS/MIG zones: compute, copy,
  comm.
- A horizontal time axis (T0→T3) with three swimlanes — Compute (Tensor Core),
  Copy D2D (layout xform), Comm H2D (next batch) — whose bars overlap in time.

### Layer 4 — Memory Pool (lifetime · in-place · workspace reuse)
- A 4-quadrant ring buffer (**Memory Pool**) whose colored arcs encode
  ownership.
- Three reuse-strategy cards: **In-place Update**, **Workspace Reuse**,
  **Producer→Consumer (L2) Locality**; a full-width **Buffer Lifetime
  Timeline** below.

### Cross-cutting
- Far-left dashed vertical spine with numbered circles 1–4 marking the bands;
  downward-triangle verbs in the band gutters: "lowers", "dispatches",
  "reclaims".
- Right-edge annotation cards in every band explain each stage's technique.

Colors distinguish the pipeline's concerns (graph ops, scheduling, hardware,
memory); keep the accent count within the skill's design-system budget. Layout,
palette, typography, and all geometry are yours to design — follow the
architecture-drawer skill's design system and let the evaluator guide
iteration.
