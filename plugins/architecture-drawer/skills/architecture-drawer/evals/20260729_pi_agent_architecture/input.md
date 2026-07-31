# π Agent — Architecture Diagram

Draw an AI agent runtime architecture with labels INSIDE component rectangles
(no text overflow). Bilingual labels (English title + Chinese subtitle).

## Layout

Left column: 5 horizontal layers, each a container with component cards:

1. **Interface Layer** — TUI (交互式终端), RPC (JSONL 协议), Print (打印/JSON),
   SDK (createAgentSession()).
2. **Session Layer** — AgentSession (智能体协调器), SessionManager (持久化·压缩),
   ExtensionRunner (扩展·自定义工具), ResourceLoader (技能·模板·主题).
3. **Agent Core** — Agent/agentLoop (回合生命周期管理), AgentContext
   (systemPrompt·messages·tools), AgentEvent (事件序列·工具执行).
4. **Model Providers** — OpenAI (GPT-4o·o3), Anthropic (Claude 3.5/4),
   Google (Gemini).

Below the layers:
- **LLM API box** — dashed border, "LLM API · OpenAI / Anthropic / Google 统一流式调用".
- **Event sequence example** — a monospace info box showing one `prompt()` call's
  event lifecycle (agent_start → turn_start → message_start… → tool_execution… →
  agent_end).

## Flow

- **Left spine (down, dark blue)** — request下行: top → bottom through all layers.
- **Right spine (up, orange)** — AgentEvent 事件流: bottom → top.
- **Tool execution arrow** (dashed, right side) — points to "Bash · 文件操作".

## Design

- Palette: 7 accents. Layer bands use blue tints (light → dark); flow arrows
  use dark blue (down) and orange (up).
- Font tiers: 20 / 14 / 12 / 10. All labels `bbox=False` (text doesn't enter
  collision registry).
- Canvas ~1260 × 860.
