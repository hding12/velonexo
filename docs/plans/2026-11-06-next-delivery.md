# Remaining local delivery implementation plan

**Goal:** 完成用户指定的11项待办，逐项验收；不把局部完成视为整体完成。
**Architecture:** 保留 React/Zyncat、本地 Studio、Python 发布工具与 HF 单节点。复用原子目录和对象台账；不上公网、不新增付费服务。
**Tech Stack:** React/TypeScript/Vite、Python/FFmpeg、HF、Playwright/unittest。

| 工作 | 实施位置与验收 | 状态 |
|---|---|---|
| 播放统计 | NativePlayer、metrics服务、Studio；真实事件首帧/卡顿/失败/重试，汇总查看与清除 | 已验收：playback-metrics、metrics-fault、metrics-retry、metrics-stall-switch；实际503重试漏记已修复 |
| 预加载 | preload服务、Feed；只预热下一条，限字节、弱网禁用、切换取消，网络实测 | 已实现；preload-check验证复用/弱网，preload-budget验证额度；取消延迟清单专项通过（preload-cancel） |
| 加载优化 | main/App/Studio/NativePlayer；路由拆分、播放器延迟加载，构建与浏览器回归 | 已拆分并构建通过；Feed多尺寸回归通过，静态产物网络验收通过：探索页不加载播放器、播放时才加载；Studio产物不进入静态包 |
| 热门精选专题 | catalog、Feed、Studio；明确热门依据、排序、专题编辑与筛选 | 本地版已验收：editorial-check；精选/专题CRUD，热门取本浏览器7日有效播放，不是全站统计 |
| 分类标签管理 | 发布CLI、Studio；改名、合并、排序，引用同步与原子更新 | 已验收：studio-taxonomy + Python合并/拒绝非法排序 |
| 发布记录 | save_catalog、Studio；前后值、原因、时间、操作历史 | 已验收：studio-history + Python失败提交日志；本机操作者身份 |
| 完整备份 | 新备份CLI；目录、map、原片、无密钥配置，校验和与隔离恢复演练 | 已实现：901文件/109版本恢复、4条离线播放通过；损坏/路径穿越/覆盖拒绝测试通过 |
| 存储迁移 | 新迁移CLI；批量上传校验后切换、失败保留原引用 | 已验收：17项Python测试中的批量原子性；maintenance-remote.json 两条真实HF迁移 |
| 旧版本清理 | 台账CLI；预览引用保护、显式清理、部分失败续清 | 已验收：单元故障续清与真实HF删除HEAD404；未自动清理现有样例 |
| 静态部署 | 导出脚本；仅已发布目录/映射/清单、本地播放资产，独立HTTP服务器播放验收 | 已验收：static-site.cjs 独立服务器本地/HF播放、详情、草稿/Studio排除 |
| 文档同步 | roadmap、decisions、runbooks、验收报告；统一HF现状与实际边界 | 已更新README、roadmap、decisions和运行手册，旧验收标为历史；最终复核通过，详见 ../research/delivery-final-2026-11-06.md |

每项执行：读现有实现→实现最小完整闭环→针对失败路径和实际使用测试→填证据。最后逐条复核，不以构建成功替代功能验收。当前目录不是Git仓库，不声称已提交。涉及远程测试仅使用合成非露骨素材。

最终验收入口：`npm test`、`npm run test:delivery`；完整证据见 docs/research/delivery-final-2026-11-06.md。所有11项按本地可体验范围完成；不把本机热门/指标冒充全站服务。
