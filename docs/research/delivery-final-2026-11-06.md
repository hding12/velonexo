# 11项本地增强最终验收

范围：用户指定的11项本地能力，HF单节点，免费、不绑卡、不公开部署。实现与证据逐项复核如下。

| 项目 | 实现与证据 |
|---|---|
| 播放统计 | NativePlayer + metrics + Studio；真实首帧、切换、分段延迟卡顿、404、503自动重试和手动重试；playback-metrics / metrics-fault / metrics-retry / metrics-stall-switch均通过 |
| 下一条预热 | 1.2秒延迟、下一条清单/初始化/首段；512KiB单次、4MiB单页，弱网/省流量/Safari原生跳过；preload-check / budget / cancel通过，首段实际无重复请求 |
| 加载优化 | 路由和播放器拆包；静态探索页不加载播放器，播放时才加载；Studio不进入静态站点包。核心入口约224KB，播放器仍约600KB但延后加载；没有声称达到生产首帧SLA |
| 热门精选专题 | Studio精选排序、专题CRUD、前台筛选；editorial-check及Python生命周期测试通过。热门依据本浏览器7天内至少3秒的有效观看；不是全站人气 |
| 分类标签 | 改名、合并去重、排序、同步引用和探索页；studio-taxonomy及Python拒绝非法排序通过 |
| 发布记录 | 原子目录提交前后日志、原因、时间、前后值、元数据与本机身份；studio-history和Python提交失败测试通过。没有追造旧历史或虚构登录身份 |
| 完整备份恢复 | 目录、原片、未清除媒体版本、映射、配置引用、台账、历史和运行代码；SHA256、凭据扫描、独立目录恢复、损坏/越界/覆盖拒绝；4条恢复视频屏蔽全部外网仍可播 |
| 批量迁移 | 最多50条，容量检查、上传校验全部成功才原子换引用，保留元数据；Python第二条校验失败不修改目录；真实两条HF迁移通过 |
| 旧版本清理 | 当前目录与目录备份引用保护、显式候选、逐对象删除台账、purged墓碑、原片保留；整批第一版完成第二版中断可继续；真实HF删除HEAD404 |
| 静态产物 | npm run build:static → .local/static-site；4条已发布目录、地图、清单与本地文件；排除草稿与Studio；独立HTTP服务器本地/HF播放及直达详情通过 |
| 文档同步 | README、roadmap、decisions、运行手册统一HF现状；双存储测试和旧计划标记历史。原用户设计文档保留原文 |

## 汇总证据

- `npm test`：17项Python测试、构建、目录校验、凭据扫描及基础浏览器回归全部通过；50条不同合成片段连续浏览通过。
- `npm run test:delivery`：15项新增交付检查全部通过。测试最初暴露Playwright异步predicate过早返回问题，改为直接查询任务终态后重跑受影响管理测试；最终报告确认目录和存储配置哈希不变。
- `.local/acceptance/checks-report.json`、`delivery-checks.json` 是机器结果。
- `.local/acceptance/maintenance-remote.json` 是真实HF迁移与删除证据。所有远程测试仅使用微小合成非露骨素材，未迁移或删除用户真实内容。
- `.local/acceptance/studio-editorial-mobile.png` 验证新增面板390px无横向溢出。
- 完整备份最新交付路径 `.local/backups/delivery-final-20261106.zip`；恢复只写全新目录，依赖和FFmpeg需在目标机器安装，密钥单独配置。

## 明确边界

没有公开部署、真实手机或正式内容验收，没有数据库、正式账号或全站统计服务。预热按收到的字节与Content-Length限额，无法撤回已经在途的网络字节。Safari原生HLS不能观察全部内部请求。清理不清空供应商所有对象或CDN缓存；受备份引用保护的版本不会自动删除。当前保留全部原片和现有测试样例。

最终备份复验：delivery-final-20261106.zip 包含994文件、109媒体版本；恢复到 recovery-final 后构建成功，4条视频禁用全部外部网络仍播放通过。最终默认目录4条原生已发布、仅HF启用、Studio运行任务0。
