# 本地演示、发布与恢复

适用范围：本机开发演示。远程测试只使用合成非露骨视频。不代表已完成公开上线或真实手机验收。

## 一次性准备

在仓库根目录执行（需要本机 Node/npm、Python、FFmpeg/ffprobe 和 Chrome）：

```sh
npm ci
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-storage.txt
npm run demo:prepare
npm run dev
```

访问 `http://127.0.0.1:5174/` 和 `/explore`。`demo:prepare` 生成 50 个独立本地验收样例，并发布三个不同的本地视频到默认目录；不上传云端。它不会删除已存在的真实内容。媒体、原片备份、测试报告和临时签名均在 `.local/`，不入源码。

已有 `.env.local` 保留，不覆盖。首次验证当前启用的真实存储（当前仅HF）：

```sh
npm run demo:prepare -- --remote
```

这一命令会上传约 0.6 MB 的合成有声测试素材到配置中启用的存储（当前仅HF），生成 `native-audio`。不是公开部署。重复准备可能重新校验和上传，不适合作为每次启动命令。

## 任意本地文件的离线发布

先预估（转码和生成本地包，不上传、不改目录）：

```sh
npm run media -- publish --input '/absolute/path/video.mp4' --id sample-001 --title 'Video de prueba' --tag prueba --category vertical --dry-run
```

发布到本地，或不指定 provider 按配置把连续片段组分配给启用的存储节点（当前全部进入HF）：

```sh
npm run media -- publish --input '/absolute/path/video.mp4' --id sample-001 --title 'Video de prueba' --tag prueba --category vertical --provider local
npm run media -- publish --input '/absolute/path/video.mp4' --id sample-002 --title 'Video de prueba' --tag prueba --category vertical
```

也可使用 `--provider tigris` / `--provider hf` 放入指定节点。当前输出 H.264、可选 AAC、24fps、最长边不超过720、2秒 fMP4 分段、JPEG 封面。保持比例，不放大。JPEG 是为了兼容当前没有 WebP 编码器的 FFmpeg。

流程：备份原片 → 转码/封面 → 版本化映射 → 容量检查 → 上传 → GET哈希/HEAD/Range/CORS 校验 → 清单生成 → 备份旧目录 → 原子更新目录。任一步失败，旧目录继续工作。已成功上传但未发布的对象保守计入台账，不假称失败就自动删除。

## 文件位置与映射

- `.local/media/<id>/<revision>/map.json`：每个对象的 provider ID、key、SHA-256、大小；分段顺序、时长；编码和源文件哈希。
- 同目录 `play.m3u8`：临时可播放清单；不含上传密钥，但可能含有效期内的 GET 签名。
- 同目录 `verification.json`：远程对象校验结果。
- `.local/publisher/sources/<sha256>.source`：原片副本，可直接作为 `--input` 再发布。
- `.local/publisher/objects.json`：本工具创建的远程对象台账，包含版本和未完成尝试。
- `.local/publisher/backups/*.json`：每次变更前的目录快照。

本地 Vite 只对生成包中的允许文件提供 `/local-media/` GET/HEAD/Range。原片备份、密钥和整个 `.local/` 目录不会通过该路径开放。构建产物不包含本地媒体包；`dist` 单独部署不能完整播放，当前没有承诺生产发布能力。

## 播放清单校验与刷新（私有节点兼容）

当前HF公开链接无预设签名有效期，无需定时刷新。保留的Tigris私有节点适配采用约一小时签名；仅重新启用该节点时才需要以下操作：

```sh
npm run media -- refresh native-audio
```

只读取映射、重新校验和生成签名，不转码、不上传、不更改对象 key/hash。执行后点击播放器“Intentar de nuevo”。刷新不是常驻服务，也不是正式生产签名网关。

## 扩展节点与容量

编辑 `config/storage.json`，新增唯一 provider ID；`s3` 与 `hf` 类型通过环境变量名引用凭据。新 S3 兼容节点无需改发布业务代码，新协议需增加适配器。已有 provider ID 不应换指向其他 bucket/endpoint：已发布映射记录绑定，检测到变更会拒绝刷新，避免悄悄读错库。

`group_size` 默认3；按顺序分配连续片段组，init/封面放在首节点。`--provider` 可以覆盖默认放置。没有自动均衡或镜像；单片段所在源不可用时提示重试/跳过，不宣称无缝容灾。

`project_limit_bytes` 当前每节点100 MB，是本项目保守测试上限，**不是供应商免费额度**。达到上限就停止发布；可明确指定另一个节点或添加新节点。不可通过提高这个数字推断账号不会收费。

```sh
npm run media -- usage
```

统计仅覆盖此 CLI 台账；不包含历史 smoke 上传、其他项目对象、真实账户账单/月请求/出站流量。已删除对象排除；相同 provider/key 去重。新内容预估在每次 publish/dry-run 输出，失败尝试保守计数。

## 撤下、恢复、删除

```sh
npm run media -- withdraw sample-001
npm run media -- restore-entry sample-001
```

撤下只是目录不展示，原始媒体 URL 仍可能可访问。恢复会先验证媒体并刷新清单。删除当前版本的源对象需要先撤下：

```sh
npm run media -- purge sample-001
```

此操作删除当前映射对应的源对象/本地播放文件，保留原片备份和映射记录。旧版本和浏览器/CDN已缓存副本不在该命令撤销范围；不能当作完整生产撤权。已 purge 的条目不能直接恢复，需从原片重新 publish。

恢复目录快照：

```sh
npm run media -- restore-catalog .local/publisher/backups/<timestamp>.json
```

会检查结构、验证已发布包并重建播放地址，成功后备份当前目录再替换；不能恢复已删除的媒体。不要手动修改原片备份；没有用户原片时也可从合成样例重建演示。

## 验收

先保持 `npm run dev` 运行，然后：

```sh
npm test
npm run test:remote
.venv/bin/python scripts/acceptance_lifecycle.py
.venv/bin/python scripts/acceptance_lifecycle.py --remote
```

`npm test` 验证构建、目录、产物密钥扫描、搜索/筛选/路由、响应式、50条资源上限和故障场景；`test:remote` 另外验证真实两源有声播放，要求先准备并刷新 native-audio。生命周期脚本会临时发布/撤下/删除专用 `lifecycle-test`，最后恢复原目录；不要同时进行人工目录编辑。

可选桌面 WebKit（不是 iPhone）：

```sh
PLAYWRIGHT_BROWSERS_PATH=.local/playwright npx playwright install webkit
PLAYWRIGHT_BROWSERS_PATH=.local/playwright node tests/browser/webkit-check.cjs
```

报告写入 `.local/acceptance/`；截图仅含合成图案。正式验收结论见 `docs/research/local-acceptance-2026-11-06.md`。

当前静态导出见 static-export.md，完整备份见 full-backup.md，迁移与版本清理见 media-maintenance.md。历史两节点验收不表示当前仍在双节点分配。
