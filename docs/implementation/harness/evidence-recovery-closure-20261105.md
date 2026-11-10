# 证据恢复收敛与认知建模前置验收

2026-11-05。**来源恢复 Contract 限定 PASS，模型恢复行为 PARTIAL，Web Research 整体基线尚未稳定通过。**

本轮不改变 32K 默认、64K 实验入口、KV/引擎预算、Provider Policy、Goal/Memory 采纳或 Harness 执行所有权；没有 Commit / Push。

## 1. 根因与最小修复

承接 source-attribution-cause-20261105.md：初次工具回传正确，Host 回执仍保留，但压缩后的三个近期正文前缀不能覆盖旧来源。旧来源的 ID/版本没有可靠的模型可见查找入口，模型可能停止、错配或把目录缺失解释为没有快照。窗口增大不能充分解决这个问题。

实际不需要新恢复控制器：原有 web.fetch(url, source_event_id, start_char, max_chars) 已能按已保存版本读取正文、重新验证文件及内容哈希，并且不再次联网。本轮只补来源查找与确定性失败表达。

| 修改文件 | 本轮职责 |
| --- | --- |
| harness/evidence_provenance.py | retained_source_index：从当前 Workflow 的成功 Host 获取回执生成有界来源引用目录；不读取模型引用或摘要建立来源 |
| harness/semantic_state_adapter.py | 在现有状态适配器暴露目录，不新增权威状态或存储 |
| scripts/h3_harness_interactive_repl.py | 正式 H3 出站 Host 快照发布 untrusted 目录；现有 web_fetch 描述说明保存来源读取方式 |
| harness/responses_bridge.py | 复用 24,000-byte 总预算，目录作为可降级辅助信息；省略条目明确计数，不裁切身份字段或挤掉必需约束 |
| phase2/web_capability.py | 保存快照缺失、越界或哈希变化，产生明确 source_unavailable / http_attempted=false / retryable=false，而非 unknown execution effect |
| tests/test_retained_source_recovery.py | 来源、版本、预算、失败、权限/状态不提升和旧目录过期的 11 项定向测试 |

目录最多 32 条、6000 bytes，仅列 source_event_id、URL、content_sha256 和关联 Turn；不提供原文、不声称语义相关、不等于已验证可用或模型已经读取。相同来源的多次读取去重，不同版本保留；相同 ID 的身份冲突排除并计数。未知/缺失身份保持未知。目录本身是 untrusted 投影，不产生权限。

底层读取仍使用现有 run-local Source SQLite 和快照根目录约束。模型选择来源，Host 校验版本及文件；没有自动新 HTTP、替代来源、自动重试或强制工具调用。直接 Capability 调用仍保持 ValueError 兼容；已有 Shared/Legacy 异常接口把已知本地失败转换成可追溯失败 Observation，不改冻结 Runtime。

## 2. 原始失败轨迹的离线恢复检查

输入仍是上一轮原始 32K/64K 工具回放的 execution-contract.trajectory.jsonl 和 model-http-audit.jsonl，没有手选五段正文加入 Context。

- 从全部成功 Host Observation 恢复引用目录，五个目标 ID 均可解析；原始回执内容及哈希不改写。
- 两组各 20 个来源引用均进入最终有界 Host 块；总大小分别为 **23,685 / 23,684 bytes**，低于既有 24,000-byte 限制。
- 目录不是额外免费 Context：这两个原始现场在容纳完整目录时，删掉可选运行说明、旧解释背景，并将三个近期恢复正文前缀裁至 0 字符，身份仍保留且省略被记录。完整工具正文/Host 回执未删；需要正文时必须真正读取保存来源。此处是明确的供给取舍，不能称为无损恢复。
- 这只是证明目录可在原失败现场提供旧来源身份，**不等于已恢复正文，也不等于模型会使用目录**。
- 目录数量或字节上限外的来源明确标记 omitted_sources；当前没有新建分页目录或跨 Run 引用能力，任意未来历史细节并非都能自动恢复。
- 没有来源或异常记录的普通交互不注入空目录；不由此要求工具调用。
- 当新 Workflow 不发布目录时，Bridge 仍移除上一 Workflow 的独立 Host 目录块；不会误删用户在普通文本中引用的标签。

## 3. 真实 Bolt + Codex + Shared 对照

独立记录：

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/evidence-recovery-20261105T131411Z/
~~~

固定 rust-v0.163.0、32K Bolt、1 GiB KV、36 GiB 引擎规划与原保护。四个新 Harness 会话及一次修复后追加会话，每条件一次，不重试追求 PASS。

输入复用真实历史回放的 20 份片段，使用实际 Source SQLite、HTML 快照、WebFetchCapability 和 SharedExecutionBoundary。本地夹具传输只用于预获取；20 次预获取由研究驱动执行并单独标注，**不是模型动作或真实公网获取**。预获取内容没有放进原生模型历史，等价模拟“Host 已保留、模型正文已退出 Context”的供给缺口。模型随后是否读取，完全由真实 Tool Call / Observation 判定。

任务明确列出五个待核对 URL，不给出其 anchor 或 source ID，也不手选正文；允许时只读已有快照、不新联网。对照仅关闭目录条目，保留其他接口与任务。新任务较旧的隐含分组问题更明确，因此不是原长实验的逐字重放，也不是一般研究质量测试。

| 条件 | 实际模型动作 | 正文回传 | 归属 / UNKNOWN | 独立判定 |
| --- | --- | --- | --- | --- |
| 目录关闭对照 | 0 | 0 | 0 个正确，5 个 UNKNOWN | 未恢复；未捏造 anchor，但把目录不可见解释成“无保存快照” |
| 目录启用 | 5 次 web_fetch | 5 份保存正文 | 5/5 正确 | 本次来源查找→执行→回答 PASS，未重新联网 |
| 删除一个确切快照，初次失败接口 | 7 次动作：4 次成功读取、2 次失败读取、1 次不存在文件读取 | 4 份 | 4 个正确 + 缺失项 UNKNOWN | 成功继续其余来源；失败重复，出现虚构内部文件路径及宽泛完成叙述 |
| 用户禁止工具 | 0 | 0 | 5 个 UNKNOWN | 未擅自读取，但声称“历史研究已完成”，Model Behavior FAIL |
| typed 失败修复后追加缺失快照会话 | 0 | 0 | 5 个 UNKNOWN | 模型未调用工具却声称已复核；恢复行为 FAIL，未实际消费 typed 失败 |

目录启用成功会话耗时 152.35 秒；关闭对照 34.83 秒。多出的时间包含真实保存快照读取和生成，不是性能退化 Benchmark，也不是等工作量性能比较。

**出站审计：**各会话首请求均不包含五个目标 anchor；启用目录时可见 20 条身份引用。成功会话的下一模型请求包含五份实际 function_call_output，每份 source_event_id、URL、content_sha256、实际文本 SHA256 均核验；不是仅日志显示工具成功。缺失案例发生一次自然 Compaction（raw line82），后续目录仍通过 Host 出站恢复，四份实际正文回传可追踪。没有声称模型内部推理依赖已得到证明。

五个会话都没有模型阶段的新网络传输；所有成功恢复标记 retained_snapshot、http_attempted=false。模型输出始终记录为非 Source Evidence，Host 的 workflow_completion_established 全部为 false。**不能把这个 false 反过来解释为来源核对也没有完成**：五组核对有执行/答案依据，但完整历史研究没有验收依据，也没有为此增加自动完成规则。

### 已知失败表达修复的证据限度

初次缺失快照实际产生 Capability outcome is unknown，尽管失败发生在本地校验、没有 HTTP。本轮已修正为确定性 source_unavailable，离线真实 Capability→Shared→Observation→工具可见投影均验证为 failure、http_attempted=false、retryable=false，保持缺失细节 UNKNOWN。不能将已保存回执抹除，也不能自动抓取其他版本。

追加真实会话没有执行读取，故**尚未证明模型收到新失败反馈后减少重复读取**。不把这次未执行隐藏为成功，也不再增加循环/提示字段去争取 PASS。模型仍会混淆“看到目录”“读取快照”“完成研究”，这是当前可观察的行为限制。

## 4. 回归、资源与回退

- 新增 11 项定向测试 PASS；最终相关 **70 项**快照/恢复/连接回归 PASS，早期相关 95 项也通过。
- 扩展检查 **415 项：409 PASS、2 SKIP、3 FAIL、1 ERROR**。四个异常在本轮修改前的隔离副本中逐项复现：旧错误历史投影索引断言、旧搜索成功消息断言、包含实时钟的全文相等断言、旧来源排序断言。没有把全套回归写成 PASS，也没有为本轮整理修复无关历史测试。
- Python AST 和 git diff --check 通过。31 项保护/原记录不变性检查通过，包括旧 Qwen UMA、独立模型启动/补丁、冻结 Phase-1 与原始失败实验记录。
- 采样 Dedicated 峰值 **29.35 GiB**、Shared 峰值 **0.255 GiB**；Windows Available 最低 **24.49 GiB**、Commit 余量最低 **46.91 GiB**；WSL Available 最低 **17.49 GiB**、Swap 峰值 **1.375 MiB**。采样值不是硬性峰值保证，内存域不相加。
- 阈值模拟、监控失效终止检查 PASS。本轮服务主动 CONTROLLER_STOP，服务及采样器 remaining=[]，8000/8003 无监听。控制器的主动停止非零退出不代表资源事故；没有关闭外部服务。

完整证据：design.json、original-replay.json、各会话 app-server-events.jsonl / model-http-audit.jsonl / execution-contract.trajectory.jsonl / final-snapshot.json、audited-results.json、typed-failure-amendment.json、regression-final-source-results.json、baseline-known-failures.log、safety.json、protected-checks.json。

before/ 与 this-stage.patch 仅描述本轮五个正式文件增量，不覆盖原有未提交修改。回退时先核对当前文件与本轮 after 哈希，再仅逆向本轮增量；不要整体覆盖已有工作区。新增测试和本报告独立保留。隔离实验代码不成为人工入口。

## 5. 前置验收与架构建议

| 维度 | 判定 | 范围 |
| --- | --- | --- |
| 确定性来源恢复 | PASS（限定） | 现有快照、当前 Workflow、目录预算内，身份与版本可验证 |
| 错误归属 | PARTIAL | 一次自动读取后 5/5 正确，不能保证普遍语义归因 |
| 合理 UNKNOWN | PARTIAL | 缺失/禁止工具时未编造目标值；有时过度弃答并编造读取过程 |
| 任务继续 | PARTIAL | 一次真实自主五次读取完成核对；另一会话停止于文字声明 |
| Host 权威隔离 | PASS（限定） | 模型完成/读取声明不升级为执行、Goal、Memory 或 Workflow 权威 |
| Web Research 限定可用工程基线 | PARTIAL | 恢复通路可用，尚不能宣称连续研究稳定通过 |

保留现有 32K 默认、64K 实验入口。下一步应在普通网页研究中检查同一目录/保存读取路径的使用，而不是加窗口、放大恢复块或建立新控制器。本轮未新增 live Search / Fetch 对照，其历史 PASS 不扩大为当前完整研究 PASS。

**可以继续开展隔离认知建模**：观察单位使用真实用户输入、已验证 Observation 和版本引用；缺失保持 UNKNOWN，Assistant 自述和 Compaction 不升级为支持或正式状态。模型重复失败、虚假“已读取/已完成”、目录 32 条/6000-byte 覆盖限制及跨 Run UNKNOWN 应保留为研究负面样本，不必以消灭所有幻觉为认知建模前提。

正式扩大 Goal/Memory 采纳或自动研究完成判定仍需另行评审。本轮无需新的长时间人工验收；限定实现与反例已留档，现停止。
