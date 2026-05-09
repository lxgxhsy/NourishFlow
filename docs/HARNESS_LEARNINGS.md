# NourishFlow Day 2 · HARNESS LEARNINGS

---

## Day 2 P1 - M1 schema + M2 CLI 骨架

### 实际耗时 vs 预算
预算 1h,实际 ~0.5h。偏差原因:任务范围清晰,无阻塞点。

### Claude Code 撞到的纪律盲区
1. Typer 0.13 + Click 8.3 有已知 `make_metavar()` 兼容 bug,`--help` 直接崩。选型前没先验证 `--help` 能跑通,浪费了一轮调试。

### Claude Code 即时打的临时补丁
- 从 typer 换成 argparse(标准库),零依赖,兼容性有保障。typer 虽然在 pyproject.toml 里,但这个脚本不需要它。

### Claude Code 建议沉淀进 CLAUDE.md v0.2 的条目
- 新条目 6.1:CLI 工具优先用 argparse(标准库),不引入 typer/click 兼容风险。除非项目已有 typer 且验证过 --help 能正常工作。
- 新条目 6.2:任何 CLI 脚本写完第一件事跑 `--help`,确认帮助信息正常再往下走。

### 用户批注(必填,不能跳过)
- _(待用户填写)_

### 如果重做这个 Phase,你会做哪些改进?(必填一条,不许跳)
直接用 argparse 起步,不碰 typer。typer 的"好看"换来的兼容性风险在 MVP 阶段不值得。

---
