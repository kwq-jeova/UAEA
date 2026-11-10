# 人工验收：Context / 正文续读 / 长Turn（2026-11-04）

工程自动验证完成；**现在需要一轮真实人工测试**。不要沿用修复前的Harness会话。
本次目标是模型是否实际使用正文与执行事实，不仅看对话流畅度。

## 1. 模型与Harness入口

若已有同配置、受原保护启动器管理的Bolt服务在8003，可继续复用，不重启它。
若无Bolt服务且Qwen未占用GPU，在WSL终端1运行：
~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
~~~
等待真实就绪；沿用32K、固定1GiB KV、36GiB规划及现有资源保护。门禁失败不改阈值。

关闭旧Harness会话后，在WSL终端2运行：
~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 420 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/context-continuity-manual
~~~
保留[ARTIFACTS]的新目录。没有新增人工测试脚本，也没有新的模型环境。
如果8003服务配置不明或保护失效，不启动另一份服务；记录现象即可。

## 2. 少量真实交互

1. 用自己的话提出真实研究问题，说明Google、时间和来源限制。可以沿用上一轮研究，但本报告不预先认定其事实前提正确。
2. 要求它搜索后选择2–3篇可访问文章，实际打开；正文不足时，使用web.fetch的已保存来源ID续读后续片段，避免只反复获取前900字符。无需你手填JSON或游标。
3. 要求区分原文、自己的推断、未能获取或未能支持的部分；无法访问时不要声称读过。观察是否仍反复访问同一失败页面。
4. 加入一项真实条件或后续研究问题，检查它是否保留原约束、承认证据不足并完成必要综合，而不是只列“下一步准备做”。

不必制造Compaction，不必追求固定工具次数。若自然触发压缩，保留原会话继续观察；没有触发就记未触发。
不必为了测试编造模型误解；如有真实误解，用自己的话纠正并说明是否在后续保持。

## 3. 遇到长任务超时

若出现“wait timed out; Turn is NOT confirmed stopped”，说明外层等待结束，原Turn尚未确认终结。
此时可输入：
- /turn status：看最后观测的待处理身份；不是实时完成证明。
- /turn wait：继续等待原任务，不新增turn/start、不重新发送原研究。
- /turn cancel：请求取消并等终结确认。只收到ACK不算取消完成；仍未确认时继续阻止新任务。

不要用普通的“继续”重启尚未终结的任务；它会明确提示未发送、未保留。
无需刻意用极短超时制造这个场景；未自然发生则记录未触发。取消只针对本Harness的Turn，不关闭External模型服务。

## 4. 反馈与结束

请告知新会话目录、哪些回答不符合真实意图/原文，以及是否见到超时、压缩或报错。
我会核对实际片段起止/hash、是否发生新HTTP、出站Context、失败事实去重与Workflow状态，不能以模型口头“已读取/完成”代替执行记录。

结束时Harness输入exit。External模式会保留Bolt；只有本次自己新启动的模型，才在终端1按Ctrl+C并等待原保护启动器清理。
本次不做Goal正式采纳，不使用/goal adopt、revise或clear。
