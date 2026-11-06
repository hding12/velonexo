# 本地独立任务验收记录

> 历史阶段记录：双存储与签名测试描述的是当时验收。当前只启用HF公开地址，Tigris暂停；当前能力以 docs/plans/2026-11-06-next-delivery.md 和最新运行手册为准。
日期：2026-11-06（Asia/Shanghai）。范围来自用户确认的可独立推进清单，不把本地技术验证写成公开运营验收。下列独立任务已逐项完成，并通过本地验收；不包含文末列明的外部条件。

## 实现与验收对应

| 项 | 实现 | 验收证据 |
|---|---|---|
| A1 离线发布 | scripts/media_publish.py：输入文件、编码、JPEG封面、上传后发布 | tests/python/test_media_publish.py；实际 native-audio 发布与 verification.json |
| A2 映射/清单 | 版本目录、顺序/时长/字节/哈希、provider/key，map编译清单 | 映射无效顺序/哈希/路径/时长拒绝；生成与重建测试 |
| A3 提供商扩展 | config/storage.json + s3/hf适配器；按组或手选 | 两家真实源 GET/HEAD/Range/CORS；不同放置生成独立版本；禁止重指向既有provider |
| A4 签名刷新 | refresh仅验证对象并重建URL | .local/publisher/refresh-evidence.json：禁止调用upload仍成功，keys/hash/台账不变 |
| A5 播放器 | 声音、暂停、进度、加载、手动播放、路由/离屏销毁 | native-check.cjs、acceptance.cjs、webkit-check.cjs |
| A6 有界故障 | 超时、错误稳定状态、手动重试/跳过 | faults-check.cjs：manifest404、segment404、timeout、offline |
| A7 内容发现 | /explore，分类/标签/搜索组合、排序、详情和历史 | acceptance.cjs + filters-check.cjs |
| A8 生命周期 | 原片/目录备份、撤下、恢复、删除当前版 | acceptance_lifecycle.py --remote；远程删除后HEAD404；本地副本删除；原目录恢复 |
| A9 容量 | 按provider/key去重的项目台账、发布前新增容量估算 | 单元测试重复对象、容量超限拒绝；usage实测 |
| A10 批量 | 50个独立合成片段，横/竖/方，有声/无声 | acceptance.cjs：50条逐条播放、活动源/挂载数量、GC后堆观察 |
| A11 UI/文案 | es-CL操作文案；保留Zyncat；隐藏未开放社交入口；键盘操作 | 360/390/430/844横屏/1440布局与控制；截图人工查看；路由/分享测试 |
| A12 交付 | 本地命令、运行/恢复手册、构建检查 | run_checks.cjs；check_artifacts.py；docs/runbooks/local-demo.md |

## 测试资产说明

- `.local/acceptance/catalog.json`：50条不同合成样例；仅用于测试拦截目录，不作为50条真实内容发布。
- 默认目录有三个不同本地样例，以及跨Tigris/HF的8秒有声样例 native-audio。
- 真实存储测试只使用合成非露骨素材。没有公开发布，没有使用真实成人素材。
- 举报按用户决定移除；外链播放暂停。external-check仅检查安全URL与通用降级卡片，不代表第三方播放通过。

## 实测中修复的问题

1. FFmpeg缺WebP编码器：使用JPEG封面，避免附加转换服务。
2. 活动切换后旧video节点保留currentSrc：非活动卡片只保留封面，销毁播放器。
3. 媒体异步事件覆盖error：失败状态锁定，只有用户重试才创建新播放器。
4. Chrome声明支持原生HLS但远程fMP4解码失败：Chromium走hls.js，Safari/WebKit优先原生HLS。
5. 远程删除后本地生成副本仍存在：purge同步删除本地播放文件，开发服务拒绝purged版本。

## 范围和限制

- Playwright桌面WebKit不是实际iPhone/Safari；隐藏事件测试是模拟事件，不声称真实后台/锁屏验证。
- 50条短合成片段验证了当前规模下的单源播放和资源边界，不等于长时间真实用户性能或内存无泄漏证明。
- 无镜像副本，不承诺单存储失效后无缝播放；有错误提示、有限重试和跳过。
- 每节点100MB是项目测试上限，不是免费额度。台账不是账户请求/出站/账单监控。
- Tigris临时签名需手动refresh；dist不包含本地生成媒体服务，不是可直接公开部署的完整播放包。
- purge针对当前版本源对象及本地生成文件；旧版本、浏览器和CDN缓存需另行处理，不等于生产全链路撤权。
- 构建仍有上游use client指令忽略及单JS包约852KB的提示；未把本地通过写成生产性能达标。

## 最终结果

- `npm run demo:prepare` 实跑成功：重新生成50个独立本地样例并发布三个默认本地视频。
- `npm run test:remote`：13个检查步骤全部退出0，包括9个Python测试、构建、目录/映射校验、构建产物扫描，以及浏览器回归。
- 50条连续滑动全部成功；每次只有一个活动媒体源；最多挂载当前和相邻3张卡片，视频节点为Zyncat的可见实例及隐藏副本2个，隐藏副本不加载源。
- 第11条到第50条回收后JS堆：7.90 MB → 8.11 MB。浏览器JS错误0。
- 故障请求计数：manifest-404=1；segment-404=3；timeout=2；offline=0；错误提示后停止自动请求。
- Chrome/hls.js与桌面WebKit/原生HLS均实际播放跨过第7秒，覆盖Tigris前半段和HF后半段。
- 本地及真实两源发布/撤下/恢复/purge演练通过；实际源删除后HEAD404，本地副本删除，目录恢复到演练前。
- 本工具当前有效远程台账：Tigris 449,013 bytes，HF 157,584 bytes；测试删除对象已排除。
- 构建产物5个文件扫描通过，无配置中的凭据值或临时GET签名。

机器报告：`.local/acceptance/checks-report.json`、`browser-report.json`、`fault-report.json`、`webkit-report.json`；生命周期及刷新报告在`.local/publisher/`。这些文件是本地生成证据，不提交凭据或原片。
