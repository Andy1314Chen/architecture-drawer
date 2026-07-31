# vLLM — High-Throughput LLM Serving with PagedAttention

Draw a layered top-to-bottom pipeline (request → response) for the vLLM inference
serving stack, with the PagedAttention / paged KV-cache abstraction on the right.

## Layers (top → bottom)

1. **Title bar** — "vLLM — High-Throughput LLM Serving with PagedAttention",
   subtitle "PagedAttention · Continuous Batching · High Throughput".
2. **Client** — single node: "Client / Application" (OpenAI API · HTTP / SDK).
3. **API Server** — container with two nodes: "FastAPI / ASGI Server" (request
   routing · streaming) and "OpenAI-compatible API"
   (/v1/completions · /v1/chat/completions).
4. **LLM Engine (Core)** — left container with three nodes:
   - AsyncLLMEngine (top center)
   - Scheduler (left, with bullet list: continuous batching · prefix caching ·
     chunked prefill · speculative decoding)
   - BlockManager (right, with bullets: paged KV cache · block table ·
     non-contiguous allocation)
5. **Paged KV Cache (GPU Memory)** — right container: logical blocks row,
   block table mapping (L0→P3 etc.), and a physical KV cache blocks grid
   showing allocated vs free blocks.
6. **Execution Layer (GPU workers)** — bottom container: Worker → ModelRunner →
   PagedAttention Kernel, plus an Optimizations & CUDA Kernels band
   (quantization AWQ/GPTQ/FP8, tensor/pipeline parallelism, LoRA, etc.).

## Edges

- **Solid** (data / request flow): client → API → engine → scheduler → worker →
  modelrunner → pagedattn → phys_blocks.
- **Dashed** (cache / block management): scheduler ↔ blockmanager,
  blockmanager ↔ phys_blocks.

## Design

- Palette: S1 Monochrome Blue. Op cards fill white; color in layer fills + borders.
- Font tiers: 20 / 14 / 12 / 10.
- Legend at bottom distinguishing solid (data flow) vs dashed (cache management).
