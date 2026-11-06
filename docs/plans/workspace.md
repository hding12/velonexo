> 本文是早期目录规划，不代表当前实际文件位置。当前Studio位于 src/components/Studio.tsx，运行与交付状态见 docs/plans/2026-11-06-next-delivery.md；存储仅启用HF。

# 工作区规划

采用单仓库、单前端应用，不提前拆 monorepo。现在建立文档目录，应用目录随对应任务创建，避免空壳被误认为已实现模块。

| 路径 | 职责 | 创建阶段 |
|---|---|---|
| docs/specs/ | 保留原始需求基线 | 已建立 |
| docs/plans/ | 工作范围、任务依赖、决策问题 | 已建立 |
| docs/adr/ | 记录关键决策、证据、替代方案与影响 | 已建立 |
| docs/research/ | 上游组件、供应商能力与政策核验记录 | 已建立 |
| docs/runbooks/ | 发布、下架、备份、回滚操作手册 | 已建立 |
| src/app/ | 路由、应用组合、功能开关 | M0 |
| src/domain/ | 内容类型与播放器能力契约 | M0 |
| src/features/player/ | 原生播放器、官方嵌入适配 | M0 |
| src/features/feed/ | 滑动、激活控制、卡片生命周期 | M0 |
| src/components/、src/styles/ | 响应式外壳、通用组件与样式 | M0 |
| src/services/content/ | 静态目录读取，后续数据库适配 | M0–V0.1 |
| src/services/media/ | 媒体定位与访问地址解析 | M0–V0.1 |
| src/features/discovery/ | 分类、标签、静态搜索 | V0.1 |
| public/catalog/videos.json | 仅可公开的已发布条目 | V0.1 |
| scripts/ | 目录校验、媒体准备、后续迁移工具 | 按任务创建 |
| tests/ | 契约、播放生命周期、浏览器验收 | M0 起 |
| functions/ | 必要访问控制，后续管理员接口 | 按访问方案决定 |
| src/features/studio/、src/features/auth/ | 管理后台与管理员身份 | V0.2 |
| supabase/migrations/ | 数据表、权限与迁移 | V0.2 |
| src/services/telemetry/ | 最小化观测与性能指标 | 按阶段需求 |
| src/features/forum/ | 独立论坛模块 | V1.1 |

## 依赖方向

app 组合 features；features 依赖 domain 与 services 提供的契约；具体数据适配器在应用入口装配。domain 不导入 React 或 Supabase；播放器不查询数据库；媒体地址解析集中于 services/media。

不提前创建 package.json、锁文件或部署配置；初始化时统一选择包管理器、核验依赖并生成锁文件。

## 公开与私有边界

public 中任何文件都应视为公开。草稿、审核备注、授权材料不得写入公开 JSON；仅前端过滤 visibility 不能保密。私有资料存放位置待确定，不在仓库建立假私有目录。

静态站点不等于所有媒体必须公开；若访问方案需要边缘验证，functions 可在 V0.1 引入，但不因此提前引入 CMS 数据库。
