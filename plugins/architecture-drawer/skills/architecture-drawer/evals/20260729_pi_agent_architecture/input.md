# π Agent — Architecture Diagram

Draw an AI agent runtime architecture with labels INSIDE component rectangles
(no text overflow). Bilingual labels (English title + Chinese subtitle).

## Layout

Left column: 4 horizontal layer bands stacked top→bottom, each a container
holding 3–4 component cards. Below the bands sit two full-width boxes (LLM API,
then an event-sequence info box).

1. **① 交互界面层 · Interface** (no package) — TUI (交互式终端), RPC (JSONL 协议),
   Print (打印 / JSON), SDK (createAgentSession()).
2. **② 编码智能体层 · pi-coding-agent** (`@earendil-works/pi-coding-agent`) —
   AgentSession (智能体协调器), SessionManager (持久化 · 压缩),
   ExtensionRunner (扩展 · 自定义工具), ResourceLoader (技能 · 模板 · 主题).
3. **③ 智能体核心层 · pi-agent-core** (`@earendil-works/pi-agent-core`) —
   Agent / agentLoop (回合生命周期管理), AgentContext (systemPrompt · messages · tools),
   AgentEvent (事件序列 · 工具执行).
4. **④ AI 抽象层 · pi-ai** (`@earendil-works/pi-ai`) — OpenAI (GPT-4o · o3),
   Anthropic (Claude 3.5/4), Google (Gemini).

Below the layers:
- **LLM API box** — dashed border, "LLM API · OpenAI / Anthropic / Google 统一流式调用".
- **Event sequence example** — a monospace info box showing one `prompt()` call's
  event lifecycle (agent_start → turn_start → message_start … → tool_execution … →
  agent_end) with Chinese explanations per line.

## Flow

- **Left spine (down)** — 请求下行 ↓: request travels top → bottom through all
  4 layers and into the LLM API box.
- **Right spine (up)** — ↑ AgentEvent 事件流: event stream bubbles bottom → top
  back up from the LLM API box through every layer. Use a visually distinct
  color for it (e.g. an event/attention accent vs the request's primary dark).
- **Tool execution arrow** (dashed, far right of the Agent Core band) — points
  outward to "Bash · 文件操作".

Flow spines must route OUTSIDE the card area — never slice through a band's
filled rectangle or the LLM box interior. Layout, exact palette, typography,
and all geometry are yours to design — follow the architecture-drawer skill's
design system and let the evaluator guide iteration.
