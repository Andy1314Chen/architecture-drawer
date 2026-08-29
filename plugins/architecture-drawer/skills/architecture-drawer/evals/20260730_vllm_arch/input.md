# vLLM — High-Throughput LLM Serving with PagedAttention

Draw a layered top-to-bottom pipeline (request → response) for the vLLM
inference serving stack, with the PagedAttention / paged KV-cache abstraction
on the right.

## Layers (top → bottom)

1. **Title bar** — "vLLM — High-Throughput LLM Serving with PagedAttention",
   subtitle "PagedAttention · Continuous Batching · High Throughput".
2. **Client** — single node: "Client / Application" (OpenAI API · HTTP / SDK).
3. **API Server** — container with two nodes: "FastAPI / ASGI Server" (request
   routing · streaming) and "OpenAI-compatible API"
   (/v1/completions · /v1/chat/completions).
4. **LLM Engine (Core)** — left container with three nodes:
   - AsyncLLMEngine (top center)
   - Scheduler (left, bullets: FCFS + priority scheduling · continuous batching ·
     preemption on KV-cache OOM · decode-step orchestration)
   - BlockManager (right, bullets: logical ↔ physical blocks · block tables
     (paging) · copy-on-write fork · reference counting)
5. **Paged KV Cache (GPU Memory)** — right container: logical blocks row,
   block table mapping (L0→P3 etc.), and a physical KV cache blocks grid
   showing allocated vs free blocks (allocated need not be contiguous → low
   fragmentation).
6. **Execution Layer (GPU workers)** — bottom container: Worker → ModelRunner →
   PagedAttention Kernel, plus an Optimizations & CUDA Kernels band
   (continuous batching · prefix caching · chunked prefill · speculative
   decoding; quantization AWQ/GPTQ/FP8 · tensor/pipeline parallelism · LoRA
   multi-adapter · prefix-aware scheduling).

A small legend at the bottom distinguishes the two edge kinds.

## Edges

- **Solid** (data / request flow): client → openai_api; fastapi → openai_api;
  openai_api → async_engine → scheduler → worker → modelrunner → pagedattn →
  phys_blocks.
- **Dashed** (cache / block management): scheduler ↔ blockmanager (alloc /
  free); blockmanager ↔ phys_blocks (manage physical).

English only. Layout, palette, typography, and all geometry are yours to
design — follow the architecture-drawer skill's design system and let the
evaluator guide iteration.
