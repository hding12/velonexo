# VeloNexo

本地短视频演示：React、TypeScript、Vite、Zyncat TikTok、HLS；首版界面为 es-CL。当前没有公开部署。

## 已可体验

- 竖屏信息流、详情分享、独立探索页、分类/标签/搜索与时间排序。
- 原生有声/无声播放、暂停、声音、进度、重试/跳过；仅活动条目播放，下一条按预算预热。
- 离线视频发布、封面、分块、完整映射、Tigris/HF 适配和校验后发布。
- 项目容量台账、目录/完整备份、撤下/恢复/删除；Tigris签名适配保留但当前暂停。
- 本地三个不同合成视频；另有HF单节点的合成有声样例。

外链测试暂停并从默认信息流隐藏；举报能力按用户要求移除。未开放的点赞/评论/关注入口不展示。新增 `/studio` 本地媒体管理页，支持上传草稿、预览编辑、发布/撤下、失败重试与清理、批量管理、存储连接/启停及刷新播放地址。尚无公网管理员认证、用户账号、论坛或推荐系统。

## 启动与验收

当前工作区从 `code/` 执行命令，本地数据单独存放于同级 `local/`。新克隆初始化、路径配置与上传边界见 [工作区布局](docs/runbooks/workspace-layout.md)。

完整说明：[本地运行与发布手册](docs/runbooks/local-demo.md)。

已安装依赖并准备媒体后：

```sh
npm run dev
```

访问 http://127.0.0.1:5174/ 或 /explore 。`npm test` 执行本地验收；`npm run test:remote` 包含真实存储播放。测试要求开发服务器运行。

当前仅启用HF公开地址，不需要续签。`npm run build:static` 生成可独立运行的 `../local/runtime/static-site`（独立克隆默认 `.local-work/runtime/static-site`）；`dist` 只是中间前端产物。

## 文档

- [本地管理页操作](docs/runbooks/local-studio.md)

- [v1.1 设计原文](docs/specs/VeloNexo-Design-Spec-v1.1-DMS.md)
- [后续决定](docs/plans/decisions.md)：优先于原始文档中已被用户修改的范围。
- [独立交付任务与验收矩阵](docs/plans/2026-11-06-autonomous-delivery.md)
- [验收结果](docs/research/local-acceptance-2026-11-06.md)
- [视觉规范](DESIGN.md)

技术验证使用合成非露骨样例。真实手机、真实内容、正式托管/运营条件和公开部署不包含在本地验收结论中。密钥位于所选本地目录的 `secrets/.env.local`；原片、映射和生成包位于 `runtime/`，均不提交到源码仓库。

静态交付：`npm run build:static` 生成 `../local/runtime/static-site`（独立克隆默认 `.local-work/runtime/static-site`），包含已发布目录与所需媒体文件，可脱离Vite运行。说明见 [静态导出手册](docs/runbooks/static-export.md)。

新增管理能力：分类标签改名/合并/排序、精选与专题、操作历史、本机播放统计。热门仅根据本浏览器有效观看计算。完整备份见 [恢复手册](docs/runbooks/full-backup.md)，批量迁移与旧版本清理见 [维护手册](docs/runbooks/media-maintenance.md)。

## GitHub 源码与本机数据边界

`code/` 是唯一公开代码仓；同级 `local/` 在 Git 边界之外。仓库保存源码、测试、文档、依赖锁和无密钥配置模板。密钥、真实存储配置、实际目录、视频、备份、原始语料和个人外链实验不上传。依赖、构建产物及本机路径标记也不跟踪。

新克隆先安装依赖，运行 `npm run setup:local` 和 `npm run demo:prepare` 生成本地合成样例。默认使用忽略的 `.local-work/`，已有目录记录不会被初始化覆盖。详细命令见 [工作区布局](docs/runbooks/workspace-layout.md)。
