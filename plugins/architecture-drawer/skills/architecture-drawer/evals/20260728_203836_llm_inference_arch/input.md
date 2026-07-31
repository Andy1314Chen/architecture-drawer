# LLM Distributed Inference Serving — 7-Layer Architecture

Draw a vertical layered stack showing a distributed LLM inference serving
system. A neutral downward "spine" connects the client (top) through seven
architecture bands to the streaming output (bottom).

## Layers (top → bottom)

1. **Client / Gateway** — API requests, load balancing, rate limiting.
2. **API Layer** — request parsing, tokenization, OpenAI-compatible endpoints.
3. **Scheduler / Router** — batching, continuous batching, prefix-aware routing.
4. **Model Worker** — model execution, attention computation, KV cache access.
5. **KV Cache Manager** — paged memory, block allocation, cache eviction.
6. **Distributed Runtime** — tensor parallelism, pipeline parallelism, NCCL.
7. **Hardware (GPU)** — device memory, CUDA kernels, networking (NVLink/InfiniBand).

## Flow

A central vertical spine (neutral gray) carries the request downward through all
layers; streaming output arrows return upward on the side.

## Design

- Palette: neutral/monochrome. Op cards white; layer bands carry subtle tints.
- The spine is a thick neutral line with downward arrows between layers.
- Font tiers: exactly 4 (20 / 14 / 12 / 10).
