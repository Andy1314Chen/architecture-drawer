# Lessons Learned

Distilled, durable takeaways from experiments. Append newest to the top.
Pair with `SUMMARY.md` (which records the *what*); this records the *why* and
the *next time*.

## Agent harness contracts drift fast — verify against the canonical source

- **Trap:** planning the agent-replay layer against blog/secondary sources for
  opencode surfaced two showstoppers: `--format text` is not a real value
  (official docs: `default`|`json` only), and `.claude/skills` discovery is
  disputed (opencode issue #6266 doubts it ships at all).
- **Fix:** read the **official** docs (`opencode.ai/docs/cli`, `pi.dev` README
  + `skills.md` on the repo) and **probe the real binary** (`pi -p "..."` →
  exit 0) before writing any invocation code.
- **Next time:** for any agent-harness backend, treat the CLI contract as
  unverified until (a) the official flag table confirms it and (b) a one-line
  `cli -p "ping"` returns exit 0 on the target machine.

## Leak-free sandbox ≠ "copy the skill directory"

- **Trap:** the obvious `shutil.copytree(skill_root, sandbox/...)` drags the
  golden `evals/*/gen.py` into the sandbox — the agent transcribes it and
  scores a trivial 100 with zero text→diagram understanding tested. Same
  defect class as inlining the golden SVG.
- **Fix:** copy only the public surface (`SKILL.md` + scripts/references/assets)
  and seed **only the target eval's** `input.md`. A smoke test that asserts
  `evals/` and `gen.py` are absent from the sandbox catches regressions of this
  invariant.
- **Next time:** for any replay/regression harness, enumerate *exactly* what
  enters the sandbox and justify each entry against the anti-leakage rule.

## Refine loops don't need session continuity when the agent reads from disk

- **Observation:** Pi's tools (read/edit/bash) operate on the on-disk
  `gen.py`, so every refine round is self-contained — `continue_run()` can be a
  plain re-`run()`. No session-id bookkeeping, no `-c`/`--session` juggling,
  no cross-round state to corrupt.
- **When it would NOT hold:** if the agent could *only* continue a session
  (not start fresh), or if context were expensive to rebuild, then `-c`
  continuation would matter. Until then, stateless is simpler and more robust.

## `DEL N` is line-precise, not symbol-precise

- **Trap:** `DEL 20` on a file removed line 20 of the *docstring tree*, not
  the `import sys` I intended (which was line 45). The snapshot tag is valid
  for any line; intent is not inferred.
- **Fix:** always `read` the exact range first and confirm the line number
  maps to the construct you mean to touch — especially after an earlier edit
  has renumbered the file.
- **Next time:** treat every `edit`/`DEL` as anchored on a freshly-read line,
  never on memory.

## 默认全删会丢失"可复查性"——保留要做成 opt-in

- **观察**：agent-replay 初版用 `shutil.rmtree(sandbox)` 在断言后清沙箱，纯粹按
  Protocol A 的 anti-leakage 思路设计。但回归跑完 7/7 PASS 后，磁盘上**一个产物
  都没留**——想复查 agent 到底画了什么、或对比两次 run，只能重跑（每次 ~10 分钟）。
- **修正**：加 opt-in `--agent-keep`，开启时把沙箱拷到
  `output/agent_replay/<name>/`（含 gen.py/SVG/PNG/PPTX/score_report.txt）。
  默认仍删（无泄漏、不占空间）。`output/` 本就 gitignore，不会污染版本库。
- **下次**：任何"临时产物 + 验证"的回归层，把"默认全删"当作一个权衡而非默认——
  失败 case / 调试场景的可复查性，值得一个 opt-in 留存开关。区分"防泄漏"（不让
  golden 进沙箱）和"可复查"（保留 agent 的真实产物），两者正交，不要混为一谈。

## `finally` 里"先做事再清理"会因做事失败而泄漏

- **观察**：`_agent_replay_one` 的 `finally` 先 `_persist_sandbox(...)` 再
  `shutil.rmtree(sandbox)`。persist 抛异常 → rmtree 不执行 → 沙箱泄漏，且异常
  取代了 try 里已算好的 return 值（case 真实结果被掩盖）。
- **修正**：把 finally 里的"工作"包进 try/except，让"清理"无条件执行；persist 是
  opt-in 调试用途，失败只打 stderr 警告，不影响 case 判定。
- **下次**：任何 `try: ... finally: <work>; <cleanup>` 结构，若 `<work>` 可能抛，
  必须单独包 try/except——否则清理被跳过、且真实结果被掩盖。Python 3 的异常链
  (`__context__`) 虽保留了原异常，但测试看到的是 finally 抛的那个，诊断价值低。
