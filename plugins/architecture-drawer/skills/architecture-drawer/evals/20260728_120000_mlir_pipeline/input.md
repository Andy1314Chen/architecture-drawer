# MLIR AI Compiler — Multi-Stream Execution Pipeline

Draw a 4-layer matrix diagram showing the MLIR compiler pipeline with multiple
execution streams flowing left → right.

## Structure

A matrix grid: 4 horizontal layers × multiple columns, where each cell is a
compiler stage. Streams flow left (input IR) → right (target code).

### Layers (top → bottom)

1. **Frontend / Import** — source languages (TF, PyTorch, JAX) → dialect import.
2. **Transformation / Optimization** — canonicalization, CSE, inlining,
   pattern rewrites across dialects.
3. **Lowering** — progressive dialect lowering (high-level → low-level → LLVM).
4. **Backend / Code Generation** — LLVM IR → machine code targets (CPU, GPU, TPU).

### Cross-cutting

- A horizontal "multi-stream" annotation showing parallel compilation paths.
- Arrows showing data flow between layers and between columns within a layer.

## Design

- Palette: 8 accents (5 dark strokes + 3 light fills).
- Each layer band has a distinct tint; stage cards are white with colored borders.
- Font tiers: 4 tiers (e.g. 20 / 14 / 12 / 10).
- Canvas ~1440 × 1200.
