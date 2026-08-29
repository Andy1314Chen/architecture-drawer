# LLM Distributed Inference Serving — 7-Layer Architecture

Draw a vertical layered stack showing a distributed LLM inference serving
system. A neutral downward "spine" connects the client (top) through seven
architecture bands to the streaming output (bottom).

## Layers (top → bottom)

Each band is one layer, named bilingually (circled number ①–⑦ + CN + EN).
Components inside each band are neutral op cards.

1. **① 接入与网关层  Gateway Governance** — 4 op cards side-by-side:
   负载均衡 Load Balancer, 认证鉴权 AuthN & AuthZ, 流量控制 Rate Limit,
   Prompt 过滤 Prompt Filter.
2. **② 全局调度与路由  Scheduler & Routing** — three nodes in a row:
   集群资源视图 (GPU 显存/利用率/健康) → 全局调度器 Scheduler (Prefix Cache
   查找 · 负载均衡) ⇢ KV 缓存索引 KV Cache Index (drawn as a database
   cylinder). The sched→kvid edge is dashed (cache-hit lookup).
3. **③ 分布式推理引擎  Inference Engine** — two nested worker containers
   side-by-side: Prefill Worker（计算密集）containing Sequence 切分 /
   Attention 并行 / KV 压缩写入 chips; Decode Worker（访存密集）
   containing Continuous Batch / 动态插入踢出 / 逐 Token 生成 chips. Connected
   by a "KV Cache 转移 · Continuous Batching" arrow.
4. **④ 模型并行与加速  Model Parallelism** — 3 wide cards:
   张量并行 TP (QKV 矩阵列分割 · All-Reduce), 流水线并行 PP (按层分割 ·
   Send/Recv), 序列并行 SP (长序列分割 · 合并).
5. **⑤ 异构存储与通信  Storage & Interconnect** — Storage container
   (HBM 显存 / CPU DRAM / 分布式存储) + NVLink 节点内 and InfiniBand/RoCE
   跨节点 interconnect cards + GPU 节点集群 (8×A100/H100) with 4 GPU chips.
6. **⑥ 隐性优化组件  Hidden Optimizers** — 2 wide cards:
   通信延迟隐藏 Compute-Comm Overlap (计算/通信异步重叠), 动态显存分配 KV
   Cache Swap (换出冷 KV 至 CPU).
7. **⑦ 分离式部署  Disaggregated Serving** — Prefill 集群 (长上下文 ·
   计算饱和) → RDMA 高速网络 (drawn as a hexagon) ⇢ Decode 集群 (快速生成 ·
   带宽饱和). The rdma→dec_cluster edge is dashed (任务队列/中间态).

Top anchor: 客户端 Client (HTTP / gRPC · Prompt + 采样参数). Bottom anchor:
采样 Sampling (Top-P/Top-K) / 流式返回 Stream Output (SSE / WebSocket).

## Flow

A central vertical spine (neutral gray) carries the request downward through
all seven band nodes (client → band1 → … → band7 → output). Internal
horizontal edges show intra-layer flows (L2 resource→scheduler→KV, L3
prefill→decode, L7 prefill→RDMA→decode).

Layer bands may share a color family per concern (gateway/scheduling blue,
engine/parallelism teal, storage amber, optimizers/disaggregation purple) —
keep the total accent count within the skill's design-system budget. Layout,
exact palette, typography, and all geometry are yours to design — follow the
architecture-drawer skill's design system and let the evaluator guide
iteration.
