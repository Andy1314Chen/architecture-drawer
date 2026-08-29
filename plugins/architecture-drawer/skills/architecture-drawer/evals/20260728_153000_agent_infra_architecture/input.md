# Agent Infrastructure — Layered Architecture

Draw a **5-layer horizontal stack** (top → bottom) representing an AI agent
infrastructure platform, plus a **cross-cutting Security & Observability band**
on the RIGHT that spans the full height of the stack.

Title: **Agent Infra 架构图** / "Agent Infrastructure · 分层架构 Layered Architecture".

## Layers (top → bottom)

Each layer is a neutral container with a bilingual CN header + EN subtitle,
and holds component cards (or accent modules) inside.

1. **应用层 / Application Layer** — end-user interfaces (3 cards):
   Web 应用 · Web App | REST / API · Gateway | CLI 工具 · CLI.
2. **编排与治理层 / Orchestration & Governance** — agent coordination & control (4 cards):
   生命周期管理 · Lifecycle | 任务调度 · Scheduling | 多智能体协作 · Multi-Agent | 策略控制 · Policy.
3. **核心能力层 / Core Capabilities** — two accent modules side by side:
   - **记忆与上下文 / Memory & Context**: 向量数据库·Vector DB | 知识图谱·Knowledge Graph | RAG 检索·Retrieval.
   - **工具与网关 / Tools & Gateway**: MCP 协议·MCP | API 集成·API Integration | 函数调用·Function Call.
4. **执行与环境层 / Execution & Environment** — two accent modules side by side:
   - **执行引擎 / Execution Engine**: 高并发·Concurrency | 秒级扩容·Autoscale | 快速启动·Fast Start.
   - **环境与沙箱 / Environment & Sandbox**: 代码执行·Code Exec | Serverless·Elastic | 安全隔离·Isolation.
5. **基础设施层 / Infrastructure** — foundation (4 cards):
   计算·Compute GPU/CPU | 存储·Storage | 网络·Network | K8s 编排·Kubernetes.

## Cross-cutting band (right side, full height)

**安全与可观测 / Security & Observability** — a single tall band on the right
spanning ALL five layers, visually distinct from the neutral stack. Contains
6 cards: 身份认证·Authentication | 数据加密·Encryption | 行为审计·Behavior Audit |
日志·Logging | 监控·Metrics | 链路追踪·Tracing.

## Flow & connections

- **Dependency / control flow** — solid vertical arrows down the stack
  centerline linking each adjacent layer (L1→L2→L3→L4→L5).
- **Cross-cutting span** — a dashed horizontal line from each layer's right
  edge to the band's left edge, showing security & observability cut across
  every layer.
- A **legend** strip sits below the stack: core-module color swatches, the
  solid dependency arrow, and the dashed cross-cut line.

All labels are bilingual (CN + EN). The four accent modules plus the security
band use five distinct accent colors; everything else stays neutral. Layout,
exact palette, typography, and all geometry are yours to design — follow the
architecture-drawer skill's design system and let the evaluator guide
iteration.
