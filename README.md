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

完整说明：[本地运行与发布手册](docs/runbooks/local-demo.md)。

已安装依赖并准备媒体后：

```sh
npm run dev
```

访问 http://127.0.0.1:5174/ 或 /explore 。`npm test` 执行本地验收；`npm run test:remote` 包含真实存储播放。测试要求开发服务器运行。

当前仅启用HF公开地址，不需要续签。`npm run build:static` 生成可独立运行的 `.local/static-site`；`dist` 只是中间前端产物。

## 文档

- [本地管理页操作](docs/runbooks/local-studio.md)

- [v1.1 设计原文](docs/specs/VeloNexo-Design-Spec-v1.1-DMS.md)
- [后续决定](docs/plans/decisions.md)：优先于原始文档中已被用户修改的范围。
- [独立交付任务与验收矩阵](docs/plans/2026-11-06-autonomous-delivery.md)
- [验收结果](docs/research/local-acceptance-2026-11-06.md)
- [视觉规范](DESIGN.md)

技术验证使用合成非露骨样例。真实手机、真实内容、正式托管/运营条件和公开部署不包含在本地验收结论中。密钥放 `.env.local`；原片、临时签名和生成包放 `.local/`，不得提交到源码仓库。

静态交付：`npm run build:static` 生成 `.local/static-site`，包含已发布目录与所需媒体文件，可脱离Vite运行。说明见 [静态导出手册](docs/runbooks/static-export.md)。

新增管理能力：分类标签改名/合并/排序、精选与专题、操作历史、本机播放统计。热门仅根据本浏览器有效观看计算。完整备份见 [恢复手册](docs/runbooks/full-backup.md)，批量迁移与旧版本清理见 [维护手册](docs/runbooks/media-maintenance.md)。

## GitHub 源码与本机数据边界

仓库只保存源码、测试、文档、依赖锁和无密钥配置模板。不提交 `.env.local`、`.local/`、视频/片段/播放清单、备份压缩包、原始语料、个人外链实验、node_modules、dist 或本机运行目录 `public/catalog/videos.json`。当前媒体和内容记录保留在本机。

新克隆后按本地运行手册安装依赖，执行 `npm run demo:prepare`，会从 `config/catalog.example.json` 初始化空目录并生成本地合成样例；不会覆盖已有目录。需要远程上传时复制 `.env.example` 为 `.env.local` 并在本机填写凭据。
