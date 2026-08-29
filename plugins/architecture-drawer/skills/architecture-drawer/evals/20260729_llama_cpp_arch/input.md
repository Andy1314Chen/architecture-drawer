# llama.cpp Architecture

Draw a three-section top-to-bottom layout for the llama.cpp project.

## Section 1: Core Library

Four stacked layer bands (each a container with components):
- **Model Layer** — GGUF format, tokenizer, weight loading, quantization formats.
- **Execution Layer** — compute graph, tensor operations, memory management.
- **Graph Layer** — operator definitions, kernel dispatch, shape inference.
- **Backend Layer** — CPU (BLAS), CUDA, Metal, Vulkan backends.

The four layers form a dependency/abstraction stack (top depends on those
below), conveyed by arrows linking each band to the one beneath it.

## Section 2: Inference Execution Flow

A horizontal 6-stage pipeline showing the inference path:
prompt → tokenize → embed → forward pass → sample → detokenize → output.
Connect with solid arrows left → right.

## Section 3: Server Architecture (llama-server)

Routes → request queue → context (slots) → model eval → response.
Show how concurrent slots share the model context: a central
`server_context` block holds the active slots, with I/O components
(routes / queue on one side, model eval / response on the other) flanking it
on a single horizontal flow line.

Layout, palette, typography, and all geometry are yours to design — follow
the architecture-drawer skill's design system and let the evaluator guide
iteration.
