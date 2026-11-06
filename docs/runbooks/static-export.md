# 静态站点导出

> 目录迁移说明：当前命令从 `code/` 执行；旧 `.local/` 对应 `../local/runtime/`，旧根 `.env.local` 对应 `../local/secrets/.env.local`，实际目录在 `../local/catalog/videos.json`，实际存储配置在 `../local/config/storage.json`。新克隆默认布局及最新操作以 [工作区布局](workspace-layout.md) 为准。


运行 `npm run build:static`，输出 `.local/static-site`。这一步只生成本地文件，不部署、不注册账号。`dist` 是中间前端产物，完整交付目录是 `.local/static-site`。

导出只包含已发布目录、对应版本映射/播放清单、本地片段与封面及前端资源。远程HF片段继续使用公开URL，不复制原片、密钥、任务记录、草稿或Studio。旧包保存在 `.local/static-site.previous`；导出校验失败不替换现有包。运行期间通过发布锁避免与目录写入并发。

临时签名清单不能作为长期静态产物，导出检测到签名或有效期会拒绝。当前HF公开清单符合此要求。不会把公开播放误称为离线播放，HF仍需要网络和供应商可用性。

可用 `python3 -m http.server 5180 --bind 127.0.0.1 --directory .local/static-site` 本地预览。已生成 `/explore/index.html`、`/video/<id>/index.html`，普通静态服务器也可直接打开详情。支持SPA重写的托管商可以使用 `_redirects`；其他托管商需配置对应回退规则。管理后台只保留在本机开发服务。

验收命令：`node tests/browser/static-site.cjs`。测试自行启动独立静态HTTP服务，验证真实本地/HF播放、详情直达、草稿排除、Studio代码排除与播放器按需加载。

公开部署仍未执行；托管账号、域名及正式内容上线条件不由导出命令替代。
