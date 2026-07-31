# architecture-drawer

一个面向 [Claude Code](https://code.claude.com)、Codex、Open Code、Pi Agent 等 AI 编程助手的 Skill：用自然语言描述你的系统架构，即可生成**多层技术架构 SVG 图**，并且经 13 维质量评估器自动验证布局，并导出为**可编辑的 PowerPoint**（`pptx`）——每个形状都是原生的、可调整大小的 PPT 元素，而非扁平化图片。

> 用 Skill 画架构图，导出为可编辑 PPT。


![License](https://img.shields.io/badge/license-MIT-blue)

[English](README.md) · 简体中文

---

## 功能概览

- **用代码绘制** —— Agent 通过流式 Python API（`SVGDrawer`）放置矩形、圆形、文本和连接器，并自动注册语义节点/边。
- **验证而非断言** —— `evaluate_svg` 解析**实际渲染的 SVG**（而非 API 调用本身），对碰撞、边界、覆盖率、连接落点、幽灵锚点、边穿节点、交叉、间距、字体层级、配色、文本溢出、构图预算以及文本-形状重叠等 13 个维度打分。
- **导出可编辑 PPTX** —— `svg_to_pptx` 将每个 SVG 元素映射为原生 PowerPoint 形状（矩形→矩形、圆形→椭圆、直线→连接器、路径→自由曲线、文本→文本框），支持箭头渲染、贝塞尔曲线摊平以及透明度/虚线注入。同时提供图片栅格化降级模式。
- **生成 → 评估 → 修正** 工作流，内置 `auto_refine` 自动迭代修正布局问题（间距、边距等）。

## 样例展示

下列架构图均由 skill 完全根据文本描述生成，并经 13 维评估器打分（每张 ≥76/100）。它们同时作为 `evals/` 下的回归测试用例。

### vLLM —— 高吞吐 LLM 推理服务（PagedAttention）

![](docs/showcase/vllm_arch.png)

六层请求流水线（客户端 → API 服务 → 引擎 → 分页 KV 缓存 → 执行层 → 优化）。实线 = 数据流；虚线 = 缓存/块管理。*S1 单色蓝方案。*

### MLIR AI 编译器 —— 多流执行流水线

![](docs/showcase/mlir_pipeline.png)

4 层 × 多列矩阵（图优化 → 变换 → 降级 → 代码生成），含垂直融合分组与并发多流重叠时间轴。*8 色分类配色。*

### Agent 基础设施 —— 分层架构

![](docs/showcase/agent_infra_architecture.png)

五个水平层（应用 → 编排 → 核心能力 → 执行 → 基础设施）+ 横切的安全/可观测带。中英双语标签。*中性灰 + 5 个着色核心模块。*

## 最佳实践

1. **先想清楚架构的文字版描述。** 在写代码之前，用自然语言把架构讲清楚——分几层、每层有哪些组件、它们之间怎么连接、有没有特殊标注。一份清晰的文字描述（如 `evals/*/input.md` 中的规格）是高质量图表最大的前提。对于开源项目，可以直接使用 deepwiki 描述的系统架构文字描述。
2. **让 skill 自动生成。** 将系统架构文字描述提交给 skill，让它生成初始 `gen.py` 和 SVG。评估器会自动捕获重叠、连接错位和交叉等问题。
3. **skill 自动审查分数。** 如果分数 ≥80，说明图表结构合理。如果 <80，Agent 能自动用 `auto_refine` 或多轮 LLM 修正（`--llm-iter`）自动修复布局问题。
4. **导出 PPTX 做最终润色。** 运行 `svg_to_pptx()` 获得可编辑的 PowerPoint 文件。在那里调整配色、字体、箭头和布局以匹配品牌或出版风格——这些属于展示层，而非生成器代码的工作。

建议第一步可以和 deepwiki 或者 Agent 进行多轮讨论，给出系统架构的文字描述，然后使用该 Skill 快速自动出一版 PPTX 格式的系统架构图。最后，根据实际需求，人工再进一步精细地微调配色、图中文字等等。相对 Nano Banana 或 GPT-Image2 等直接出图，当前项目更简单、可控性更高、成本更低且可以人工手动做进一步的微调。

## 安装

### Claude Code（插件市场）

本项目已上架 [Claude Code 插件市场](https://code.claude.com/docs/en/plugin-marketplaces)。添加并安装：

```
/plugin marketplace add conne/architecture-drawer
/plugin install architecture-drawer@architecture-drawer
```

或通过 CLI：

```bash
claude plugin marketplace add conne/architecture-drawer
claude plugin install architecture-drawer@architecture-drawer
```

使用 `--scope project`（通过版本控制共享）或 `--scope local`（gitignored）。默认是 `user`。

### Codex CLI

> Codex CLI 同样支持 [Agent Skills](https://agentskills.io) 目录结构。

将 skill 目录复制到 Codex 的 skills 目录（通常位于 `~/.codex/skills/`）：

```bash
cp -r plugins/architecture-drawer/skills/architecture-drawer ~/.codex/skills/architecture-drawer
```

也可以项目级安装（推荐）：

```bash
mkdir -p .codex/skills
cp -r plugins/architecture-drawer/skills/architecture-drawer .codex/skills/
```

安装后，在 Codex CLI 中通过指令使用：

```
> Please draw the architecture of vLLM and export to PPTX
```

Codex 会自动读取 `SKILL.md` 中的工作流规范并执行生成 → 评估 → 修正的完整流程。

### 其他 Agent 平台（Gemini CLI、Cursor、Copilot）

每个 skill 都是独立的 [Agent Skills spec](https://agentskills.io) 目录。复制到对应平台的 skills 目录即可：

| 平台 | 默认 skills 路径 |
|---|---|
| Gemini CLI | `~/.gemini/skills/` |
| Cursor (@rules) | `.cursorrules` 或 `cursor/skills/` |
| Copilot CLI | 按平台指引配置 |

```bash
cp -r plugins/architecture-drawer/skills/architecture-drawer .agents/skills/architecture-drawer
```

## 依赖

Agent 生成的 `gen.py` 会导入 skill 内的三个纯 Python 模块（`svg_utils.py`、`evaluator.py`、`svg2pptx.py`）。你无需手写这些代码——Agent 会完成。只需安装以下依赖，生成的图表就能渲染和导出：

| 依赖 | 用途 | 安装 |
|---|---|---|
| `python-pptx >= 1.0` | PPTX 导出（`svg2pptx.py`） | `pip install python-pptx` |
| `rsvg-convert` | PNG 栅格化（`rasterize_svg`） | `apt install librsvg2-bin` / `brew install librsvg` |
| `pytest >= 8` | 运行测试套件 | `pip install pytest` |

## 仓库结构

```
architecture-drawer/
├── .claude-plugin/marketplace.json              # Claude Code 插件市场注册表
├── plugins/architecture-drawer/
│   ├── .claude-plugin/plugin.json               # 插件清单
│   └── skills/architecture-drawer/
│       ├── SKILL.md                             # Agent 可读的工作流规范
│       ├── scripts/                             # svg_utils.py · evaluator.py · svg2pptx.py
│       ├── references/design_specs.md           # 4 套预设配色方案（S1–S4）
│       ├── evals/                               # 7 个回归测试用例（每个含 gen.py）
│       └── assets/
├── tests/                                       # pytest：分数阈值 + SVG 快照比对
│   ├── conftest.py
│   ├── test_regression.py
│   ├── test_skill_spec.py                       # Agent Skills 规范合规检测
│   └── golden/*.svg                             # 快照基线
└── examples/                                    # 生成-评估-导出循环的最小示例
```



## 鸣谢

本项目几何/连接检测部分借鉴了以下开源项目（均深入研究了其参考文档和验证实现）：

- **[ink-graph](https://github.com/qaz1230sp/ink-graph)**：箭头被节点遮挡、边穿节点、扇出对齐、标记尺寸、枢纽节点等参考。
- **[fireworks-tech-graph](https://github.com/yizhiyanhua-ai/fireworks-tech-graph)**：构图质量合约、碰撞检测、语义角色、变换矩阵累积、「评估而非断言」理念。
- **[svg-animations](https://github.com/supermemoryai/skills)**：SMIL/CSS 动画基础。
- **[svg-design](https://github.com/tryopendata/skills)**：原生图元、严格 XML 规范等约定。
- **[svg2pptx](https://github.com/benouinirachid/svg2pptx)**（原项目）：PPTX 导出模块的架构蓝图。

完整致谢见 [`SKILL.md`](plugins/architecture-drawer/skills/architecture-drawer/SKILL.md)。

## 协议

MIT — 详见 [LICENSE](LICENSE)。
