# Evidence Recovery 工程收尾（2026-11-07）

**VERIFIED（限定）：三项评审遗留完成。Web Research 继续 PARTIAL，不重新定义旧验收结果。**
本轮未运行新的 Web Research 长会话，未更改32K默认、64K实验入口、模型依赖、安全保护或正式认知权限。

## 最小修改与直接证据

1. **harness=None**：retained_source_index 原代码对 None 调用 .get，CPU前后探针复现 AttributeError。
   现在只在关联元数据是 Mapping 时读取 turn_id；缺失身份来源仍不猜测，记录为空。
   已验证Host来源的 ID/URL/hash 保持可查；None、字符串、列表三种负面输入均覆盖。
2. **24,000 bytes 内优先级**：先删既有可选重复说明/旧解释背景，再删目录的完整身份条目，
   仍不足时才缩减近期正文。必需当前请求和约束依旧超限即拒绝，没有静默丢弃或扩大预算。
   未修改原始回执、实际工具正文或历史供给覆盖。
3. **访问事件不可变**：Source SQLite 的 insert_web_access_event 原先允许同一 ID 覆盖URL、hash、时间等。
   前后CPU探针实证旧引用可被重指向；现在同ID必须与已保存的完整规范化事件一致，
   改变观察必须新建 access_event_id。完全相同的重复写入返回原ID，不把URL级latest指针倒退到旧版本。

Source写入使用局部savepoint，失败回滚本次事件与latest指针，不回滚调用者先前工作；仍由调用者commit。
删除了事件级ON CONFLICT UPDATE，URL家族的web_sources.latest仍按原接口更新。
这不是Memory Admission、统一ID系统或Schema迁移，也不保证外部直接SQL/文件篡改不可发生；
保存快照读取的原根目录/内容hash验证继续Fail-Closed，不能在原ID下重新计算hash掩盖变更。

| 实际旧轨迹回放 | 修改前 | 修改后 |
| --- | --- | --- |
| 32K最终Host块 | 23,685 bytes；20条目录；三段正文各0字符 | 23,877 bytes；17条目录、省略3条；正文各300字符 |
| 64K最终Host块 | 23,684 bytes；20条目录；三段正文各0字符 | 23,876 bytes；17条目录、省略3条；正文各300字符 |

**代价公开保留：**预算内不能同时保证所有旧引用和近期正文。被省略目录的旧来源可能仍需已有引用才能读取，
不能把之前手选来源5/5或2026-11-05的自动恢复5/5扩为本轮所有任务通过；本轮未重测模型长任务。
不新增分页/检索模块，不扩大Web工程范围。省略条目不等于没有保存来源，更不等于允许编造。

## 文件、回归与回退

- harness/evidence_provenance.py：缺失关联元数据防护。
- harness/responses_bridge.py：目录先于正文降级。
- memory/sqlite_store.py：事件不可变、幂等及原子失败边界；不修改候选采纳实现。
- tests/test_retained_source_recovery.py：新增2项相关反例。
- tests/test_web_access_immutability.py：5项Source API/事务与版本测试。

本轮定向39项PASS；扩展498项：492 PASS、2 SKIP、3 FAIL、1 ERROR。
四个异常与前轮已独立复现的基线问题一致：错误历史投影位置断言、旧成功消息断言、
含实时钟的全文相等断言、旧来源排序断言。本轮没有为清理结果修改这些无关测试。
测试包含：旧ID重指向拒绝、同URL不同版本可并存、重复旧事件不回退latest、写入失败保持原指针及调用者工作、
commit归属、正文优先、原输入不变、预算不足安全拒绝。

原始记录与本轮增量：

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/engineering-goal-20261107-031055Z/
  before/
  stage-a-before-after-probes.json
  stage-a-replay.json
  stage-a-tests.log
  stage-a-regression.json
~~~

before/保存本轮开始前的工作区版本，不是Git HEAD；回退只逆向本轮增量，不能覆盖已有用户修改。
没有Commit/Push、数据库迁移、真实数据重写、冻结Phase-1或权限改动。
工程收尾允许进入隔离认知研究，不等于完整研究Workflow PASS。
