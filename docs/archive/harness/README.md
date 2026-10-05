# Harness 历史文档归档

> Status: CURRENT（历史导航，不是运行基线）
> Role: IMPLEMENTATION_NOTE / 历史导航
> Current reference: [Documentation Guide](../../README.md)
> Governance reviewed: 2026-10-02（文档治理，不等于新实验验证）

本目录保存 UAEA × Codex Harness 集成在 baseline 冻结前的阶段性研究文档。

归档规则：

- 保留原历史文件，必要时复制完整快照归档，不删除历史内容；
- 归档文档用于复现、审计和架构演进对照；
- 当前有效的 Harness Runtime 结论以
  [Harness baseline](../../current/runtime/harness-runtime-baseline-20260926.md) 为准；
  当前 semantic/Web 状态以主 README 和 [Boundary Audit](../../current/architecture/boundary-integrity-audit-20261002.md) 为准；
- H3 probe、trajectory implementation 和 tests 仍保留在当前源码路径，
  因为它们是可复现实验资产，不是废弃文档。

文件：

```text
harness-feasibility-20260912.md
pre-harness-freeze-20260912.md
readme-before-boundary-audit-20261002.md
```

这些文件含有仍有价值的研究段落，见 [Research Foundation Map](../../research/research-foundation-map.md)。
归档不等于全部思想错误，也不授权重新运行旧 probe 或修改冻结 inference。
