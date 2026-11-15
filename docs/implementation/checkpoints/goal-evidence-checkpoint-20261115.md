# 2026-11-15 Git同步：正文投影、Goal研究与历史报告简档

本次用户明确授权检查Git并云端同步，覆盖此前“本轮不Commit/Push”的实验阶段约束。正式仓库为WSL /home/wqkan_wsl/uaea-n1x/UAEA，origin为https://github.com/kwq-jeova/UAEA.git，main。开始时HEAD=2b3edfc，fetch后HEAD与origin/main差异0/0。

## 实际范围

- 保留并纳入同步此前未提交的文档正文投影、research-only文档Adapter/夹具/Context核账、恢复器兼容以及相应测试；不覆盖这些既有修改，不借同步增加执行机制。
- README、current/research索引与研究地图更新至11-15；保留旧日期段为历史截面，旧“待修/暂停/下一步”不当作新命令。
- 同步11-13至11-15报告与轻量原文副本、字段/成本/资源派生记录。M2存在性保持，M3 PARTIAL，M4/M5 UNKNOWN；最新A摘要异常、B输出3072截断、迁移选点偏差全部披露。
- Windows历史报告做简档与路径/体积清单：74个目录或单文件项目，8,756文件约0.54GiB；排除本轮HandoffDeliverableFocus。原件原位保留、未移动或删除，由用户决定保留。Git只同步简报/清单，不复制整个0.54GiB证据树。
- 当前研究结果与[证据副本入口](../../research/evidence/handoff-goal-20261115/README.md)、[进度正文](../../research/goal-evidence-handoff-status-20261115.md)、[历史报告简档](../../archive/local-reports-20261115/README.md)关联。

## 验证

149项CPU/offline定向回归通过，0失败/错误/跳过，约5.05秒。涵盖document_projection、document_adapter、document_fixture、Harness dynamic tools/provider history、失败Goal历史、Goal integration/continuity/recovery；不是全项目测试或新认知审计。本次不加载模型、不重跑实验。

提交前检查diff空白、改动/新增Python语法、本次文档链接、文件尺寸、常见凭据模式；有限扫描不承诺绝对无敏感信息。完整日志在仓库外git-sync-20261115-v1。当前研究源码修改前副本和before.diff同处保留。

## 权限与原始证据

Phase-1子模块、SQLite Schema、CURRENT引用和正式采纳权限不变；没有新增Goal/Memory Engine或第二Loop。保留现有N1X保护、56/72、64K、1GiB、单并发，util0.65只用于已授权隔离入口。

完整research-records、SSE/Native、Host Journal/profile、数据库、原始模型请求与权重仍在本地，不推送；Git报告路径不保证新clone可复现原环境。文档副本不是第二可修改Goal authority。原报告的“未Commit/Push”描述其历史实验结束时刻，不是本次同步状态。

实际提交和推送结果另存本地维护回执，不把待执行的push预先写成完成。完成同步后不自动开启新实验。
