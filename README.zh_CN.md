# architecture-drawer

一个 [Claude Code](https://code.claude.com) Skill（同时也是独立的 Python 库），用于生成**多层技术架构 SVG 图**，并通过 13 维质量评估器验证布局，最终导出为**可编辑的 PowerPoint**（`pptx`）——每个形状都是原生的、可调整大小的 PPT 元素，而非扁平化图片。

> 用代码画架构图。导出为可编辑 PPT。

[![Tests](https://github.com/conne/architecture-drawer/actions/workflows/test.yml/badge.svg)](https://github.com/conne/architecture-drawer/actions/workflows/test.yml)
![License](https://img.shields.io/badge/license-MIT-blue)

[English](README.md) · 简体中文

---

## 功能概览

- **代码即蓝图** —— 通过流式 Python API（`SVGDrawer`）放置矩形、圆形、文本和连接器，并自动注册语义节点/边。
- **先验证，再断言** —— `evaluate_svg` 解析**实际渲染的 SVG**（而非 API 调用本身），对碰撞、边界、覆盖率、连接落点、幽灵锚点、边穿节点、交叉、间距、字体层级、配色、文本溢出、构图预算以及文本-形状重叠等 13 个维度打分。
- **导出可编辑 PPTX** —— `svg_to_pptx` 将每个 SVG 元素映射为原生 PowerPoint 形状（矩形→矩形、圆形→椭圆、直线→连接器、路径→自由曲线、文本→文本框），支持箭头渲染、贝塞尔曲线摊平以及透明度/虚线注入。同时提供图片栅格化降级模式。
- **生成 → 评估 → 修正** 工作流，内置 `auto_refine` 实现迭代式几何清理。

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

使用 `--scope project`（通过 VCS 共享）或 `--scope local`（gitignored）。默认是 `user`。

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

### 作为 Python 库使用（无需 Claude）

`.../skills/architecture-drawer/scripts/` 下的三个模块（`svg_utils.py`、`evaluator.py`、`svg2pptx.py`）是纯 Python 文件，直接加入 `sys.path` 即可导入：

```python
import sys
sys.path.insert(0, "path/to/architecture-drawer/plugins/architecture-drawer/skills/architecture-drawer/scripts")

from svg_utils import SVGDrawer, save_svg, rasterize_svg
from evaluator import evaluate_svg
from svg2pptx import svg_to_pptx

d = SVGDrawer(1200, 800, bg="#FFFFFF")
d.arrow_head("arrow", "#333")
d.rect(100, 100, 120, 40, fill="#D5E1EB", stroke="#1B3A5C", node_id="a")
d.rect(300, 100, 120, 40, fill="#D5E1EB", stroke="#1B3A5C", node_id="b")
d.connect("a", "right", "b", "left", stroke="#1B3A5C", marker_end="arrow")

score, report = evaluate_svg(d)
print(f"质量评分: {score}")

save_svg(d.render(), "diagram.svg")
rasterize_svg("diagram.svg", "diagram.png", width=1200)
svg_to_pptx(d.render(), "diagram.pptx")   # 原生可编辑形状
```

### 依赖

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
└── examples/                                    # 最小化独立使用示例
```

## 回归测试套件

`evals/` 下的 7 张图同时作为回归测试用例。每个 `gen.py` 以子进程运行；其打印的质量评分必须达到该用例的阈值，且渲染后的 SVG 必须与 `tests/golden/` 下的快照匹配。

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # 7 个测试，全绿
pytest --regenerate-golden  # 接受变更后刷新快照
```

测试套件**锁定当前质量水平**——它用于捕捉退化，而非在新增检查（如文本重叠）后追溯惩罚旧生成器。只有在有意改进某个生成器后，才手动提升其阈值。

### LLM 回放（可选、非确定性）

默认测试套件验证**引擎层**（SVGDrawer + 评估器 + svg2pptx）对冻结的 `gen.py` 的稳定性。若要同时验证 skill 的核心承诺——*从文本描述生成合规架构图*——每个 eval 附带 `input.md` 文本规格。运行 LLM 回放：

```bash
pytest --llm-replay   # 读取 input.md，经 LLM 重新生成 gen.py，仅比分数
```

回放流程：**仅**将文本规格（`input.md`）+ skill 文档（`SKILL.md`）喂给 LLM，在沙箱临时目录执行新生成的 `gen.py`，断言分数通过统一底线（≥80）。golden SVG **刻意不提供**——给出渲染结果会让回放退化为逆向抄写（坐标被逐像素复制，缺陷被传播）。不做 per-case golden 比对（LLM 输出非确定性）。需要 `claude` CLI。在本地或夜间运行，**不**进 PR 门禁。

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
