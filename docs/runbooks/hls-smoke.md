# 双节点 HLS 技术验证

> 目录迁移说明：当前命令从 `code/` 执行；旧 `.local/` 对应 `../local/runtime/`，旧根 `.env.local` 对应 `../local/secrets/.env.local`，实际目录在 `../local/catalog/videos.json`，实际存储配置在 `../local/config/storage.json`。新克隆默认布局及最新操作以 [工作区布局](workspace-layout.md) 为准。


> 历史阶段记录：双存储与签名测试描述的是当时验收。当前只启用HF公开地址，Tigris暂停；当前能力以 docs/plans/2026-11-06-next-delivery.md 和最新运行手册为准。
生成12秒无音轨测试图案，2秒一个 fMP4 分段；前三段在 Tigris，后三段在 HF。只上传测试素材。节点中保留 demo/synthetic/<内容版本>/ 对象供复测，不删除用户文件。

## 运行

安装 scripts/requirements-storage.txt 到隔离 Python 环境，然后执行：

```sh
python scripts/hls_smoke.py
npm --cache /tmp/velonexo-npm-cache install --prefix .local/browser hls.js playwright
cp tests/browser/hls-smoke.html .local/hls-smoke/index.html
cp tests/browser/hls-smoke.cjs .local/browser/check.cjs
python3 -m http.server 5173 --bind 127.0.0.1 --directory .local
```

另一个终端运行 `node .local/browser/check.cjs`（需要 Chrome）。

浏览器访问 http://127.0.0.1:5173/hls-smoke/ 。此页仅用于技术验证，不是产品 UI；产品继续使用 Zyncat。

Tigris 保持现有私有访问配置，清单使用1小时有效的签名URL；到期重新执行脚本。密钥不进入页面。HF使用公开Bucket的 resolve 地址，S3网关匿名访问测试返回403，因此不采用该网关直链。

.local 已被忽略，其中包含临时签名清单，不应提交或公开部署。media-map 保存稳定对象键和SHA256。HTTP校验报告位于 .local/hls-smoke/report.json。

当前没有运行Safari/iOS验收；生产访问方案、内容许可与长期发布仍未完成。测试视频无音轨，不能代表已验证音频生命周期。

## 2026-11-06 实测

- 7个清单引用对象：HTTP 200、SHA256一致、CORS `*`。
- Chrome无头浏览器播放到结束：11.999999秒；Tigris与HF均产生分段加载事件；无致命HLS错误。
- HF S3匿名直链403，改为官方SDK使用的 `/buckets/<id>/resolve/<encoded-path>` 后通过。
