# 人工测试：真实意图、理解纠正与跨轮保留（约5轮）

**当前已到需要人工佐证的节点。** 这是用户语义判断，不是让用户写代码。
测试Shadow可选投影，不正式采纳Goal，不测试尚未实现的自动语义撤回。

## 启动（WSL Ubuntu，两个终端）

终端1：仅当没有既有Bolt服务且Qwen未运行时，使用原已验收保护启动器：
~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
~~~
等待服务真实就绪；保护门禁失败即停止，不改阈值。若已有本人正常运行的同配置Bolt，可复用，不重复启动；不关闭其他任务的服务。

终端2：
~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared \
  --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 420 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/goal-clarification-manual
~~~
显式覆盖n1x默认Qwen地址/模型；base-url不加/v1。32K/1GiB KV/36GiB预算及保护由原启动器保留，不在Harness端重设。
观察[ARTIFACTS]记录新会话绝对路径。不要使用/goal adopt、revise、switch等正式控制；不要clear或强制Compaction。

## 交互内容（用自己的真实表述）

1. 说明你现在真实想推进的UAEA事项、重要约束和暂不做的事；要求它简短复述“目的、实施路径、约束、尚不确定之处”。不要为了测试编造一个所谓长期Goal。
2. 要求：“请实际调用document.read_section读取README.md的‘历史与下一步’章节；区分读到的原文和你的解释。如果未执行，请明确说未执行。”只需一次真实读取，不扩成研究任务。
3. 检查它是否确有误解。**有真实误解才用自己的话纠正**，例如指出“这是你先前理解错了，不是我在这一轮改变目标”。无误解则记录“纠正未触发”，可以补充一项真实条件；不要人为谎称它误解。确认误解与纠正时分别记录轮次。
4. 提一个简短无关问题，再明确返回第1轮任务。
5. 要求它简述：当前目的与约束、此前哪项解释应修正（若有）、实际已执行/尚未执行的事项、下一步建议的依据。不要求内部推理过程。

第一轮后和最后可输入/goal status查看Shadow状态；它不调用模型，也不采纳Goal。若模型没提供可选Goal候选，记录未触发，不算接口失败或Goal生命周期通过。

## 你需要反馈什么

- [ARTIFACTS]会话目录，及大致哪些轮次存在误解/纠正。
- 用自己的话指出：真实意思是什么、模型哪项解释错误、后续是否又复用错误历史。
- 没有误解就如实说没有，不强造失败；无候选/无Compaction也如实说明。

其余JSON、真实Tool Call/Result、Observation、Goal事件与出站Context由Coding AI审计。不要仅以回答看起来连贯判PASS。
本次最多证明短会话语义/来源边界，不证明长期Goal形成、正式撤回或真实建议收益。

## 结束

Harness输入exit，保留整个新运行目录。External模式不会停止Bolt。
如果终端1模型是你为本次新启动的，测试结束后在终端1按Ctrl+C，等待保护启动器完成清理；不要终止别的任务服务。
