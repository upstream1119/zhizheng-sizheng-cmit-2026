# 智证思政参赛工程指南

作品名称：智证思政——基于知识图谱与证据审查的可信AI交互式教育系统。

## 环境与运行

在仓库根目录执行。新成员首次配置：

```powershell
conda env create -f environment.yml
conda activate cmit_2026
cd web
npm ci
cd ..
```

已有 cmit_2026 环境的成员无需重复创建。
前端按 package-lock.json 安装；Python 直接依赖固定版本，
间接依赖尚未完整锁定。

终端一：启动已验收的演示检索与模板生成后端：

```powershell
conda activate cmit_2026
$env:DACHUANG_RETRIEVE_MODE="mock"
$env:DACHUANG_LOCAL_MOCK_ACK="1"
$env:DACHUANG_GENERATOR_MODE="template"
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

终端二：启动连接真实后端的前端：

```powershell
cd web
$env:VITE_RETRIEVE_MODE="api"
$env:VITE_API_BASE_URL="/api"
npm run dev -- --host 127.0.0.1
```

打开终端打印的前端地址；后端文档为 http://127.0.0.1:8000/docs。
以上开关仅作用于当前终端，不调用在线模型。
后端 mock 名称对应受控本地检索；前端 api 模式实际发送 HTTP 请求。
前端 mock 模式则使用预置响应，不能作为真实问答验收证据。

## 初始化验收记录：2026-10-08

- 后端104项测试、前端71项测试通过；类型检查和构建通过。
- 正式语料245条、三元组100条，格式与引用完整性检查通过。
- Edge真实请求返回HTTP 200，回答、证据和阻断状态显示正常。
- 尚待开发验收：主题检索相关性、在线生成、图谱及地图时间轴交互。

## B01合并与交接记录：2026-10-08

- PR #2已合并，代码基线main@179a634。
- 后端106项测试通过；三类完整响应与真实后端输出一致。
- 三类响应通过前端契约校验，样例已进入main。
- F01开始证据阅读与门控联调；D01开展资料复核与验收题单。
- 长征精神完整教学回答、在线生成和浏览器联调仍待验收。

## 开发目标与技术栈

主题：从遵义会议到长征精神：沿着证据理解历史。
目标：完成可连续演示的教学单元，支持提问、回答、引用核查、
关系探索、时空探索及依据证据完成一道综合解释题。
报名版至少包含一个图谱场景、3—5个有依据的事件、
至少10道端到端回归、运行说明和真实演示视频。
待复核或阻断内容不得作为正式回答播报。

沿用React 18、TypeScript、Vite、Leaflet、
Python 3.10、FastAPI、FAISS、NetworkX、JSON/JSONL、
pytest和Vitest；图谱先使用React与SVG完成主题场景。
在线生成优先使用现有通义千问适配，模型与预算在联调前确认。
数字人/TTS在核心验收后决定；完整XR、模型训练及大规模扩库不纳入报名版。

## 三人协作

首批操作步骤、交付文件与验收标准见
[开发任务看板](competition_task_board.md)。

- 彭意涵：src/后端、接口契约、证据质量及整体验收。
- 严欣浩：web/前端、证据下钻、图谱、地图与时间轴。
- 徐若诚：环境交付、事件资料整理、端到端测试及录制组织。
- 共享接口与data/资产先约定字段和样例，再开始并行实现。
- 顺序：主题证据与接口样例 → 问答溯源 → 图谱时空 → 验收冻结 → 材料提交。
- 初始化建立main基线；后续从最新main创建任务分支，通过PR合并。
- PR写明改动、验证结果和限制，由另一名成员复核。
- 完成状态须附PR、测试或正式交付证据。
- 保留原团队成果来源，本届三人新增工作单独留证。

## 回归命令

```powershell
python -m pip check
python -m pytest tests -q -p no:cacheprovider
cd web
npm test
npm run build
```
