# llama.cpp Architecture

Draw a three-section top-to-bottom layout for the llama.cpp project.

## Section 1: Core Library

Four stacked layer bands (each a container with components):
- **Model Layer** — GGUF format, tokenizer, weight loading, quantization formats.
- **Execution Layer** — compute graph, tensor operations, memory management.
- **Graph Layer** — operator definitions, kernel dispatch, shape inference.
- **Backend Layer** — CPU (BLAS), CUDA, Metal, Vulkan backends.

## Section 2: Inference Execution Flow

A horizontal 6-stage pipeline showing the inference path:
prompt → tokenize → embed → forward pass → sample → detokenize → output.
Connect with solid arrows left → right.

## Section 3: Server Architecture (llama-server)

Routes → request queue → context (slots) → model eval → response.
Show how concurrent slots share the model context.

## Design

- Palette: S2 Categorical (Okabe-Ito, colorblind-safe). Each library layer gets
  a distinct accent color.
- Data-driven layout: components defined in lists, rendered programmatically.
- Section panels use `role="background"` to separate concerns visually.
- Font tiers: 20 / 14 / 12 / 10.
