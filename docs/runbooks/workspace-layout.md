# 代码仓与本地工作区

工作区根目录只保留 `code/` 和 `local/`。`code/.git` 是唯一 Git 仓库，远端为 `hding12/velonexo`；`local/` 不初始化 Git，也不上传 GitHub。

| 位置 | 内容 | GitHub |
| --- | --- | --- |
| `code/src`、`server`、`scripts`、`tests` | 程序与可复现测试 | 是 |
| `code/docs`、`config/*.example.json`、`.env.example` | 文档、无凭据模板 | 是 |
| `code/node_modules`、`.venv`、`dist` | 可再生依赖和构建产物 | 否 |
| `code/.workspace.local.json` | 本机路径选择 | 否 |
| `local/secrets/.env.local` | HF、Tigris 凭据 | 否 |
| `local/config/storage.json` | 实际存储配置 | 否 |
| `local/catalog/videos.json` | 实际内容目录 | 否 |
| `local/runtime` | 视频、原片、映射、任务、备份、验收记录、静态导出 | 否 |
| `local/experiments`、`local/corpus` | 个人实验与原始语料（如有） | 否 |
| `local/tools` | 本次迁移保留的旧虚拟环境 | 否 |

## 当前工作区启动

从工作区根目录执行：

```sh
cd code
npm run dev
```

本机 `.workspace.local.json` 选择 `../local`。Node 和 Python 使用同一套布局。`VELONEXO_LOCAL_ROOT` 可以临时覆盖；相对值始终相对于代码根目录，而非 shell 当前目录。浏览器播放 URL 不变。

## 新克隆初始化

需要 Node、Python 3.10+ 与 FFmpeg。在代码仓根目录执行：

```sh
npm ci
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements-storage.txt
npm run setup:local
npm run demo:prepare
npm run dev
```

默认数据在代码仓内忽略的 `.local-work/`，不同克隆相互隔离。若采用同级双目录，在生成数据前改为：

```sh
npm run setup:local -- --local-root ../local
```

初始化只创建缺失文件，不覆盖已有目录、配置或密钥。要切换已有本机标记，请显式编辑 `.workspace.local.json`；此操作不会自动搬迁数据。HF 凭据只填入所选本地目录的 `secrets/.env.local`。不配置远端也能生成本地合成演示。

## 验收、导出和备份

在 `code/` 运行 `npm test`、`npm run test:delivery`。输出位于所选本地目录的 `runtime/acceptance/`。静态导出命令不变：`npm run build:static`；当前工作区产物为 `../local/runtime/static-site/`。

```sh
.venv/bin/python scripts/backup_bundle.py create --output ../local/runtime/backups/my-backup.zip
.venv/bin/python scripts/backup_bundle.py restore --archive ../local/runtime/backups/my-backup.zip --destination ../local/runtime/recovery-new
```

恢复目标必须不存在。新备份恢复后将数据放入恢复项目自己的 `.local-work/`，不带密钥、不指向在线工作区；旧格式备份仍可验证和恢复。备份包内部保留原有逻辑路径以便校验，不表示线上工作目录仍采用旧布局。

历史设计与验收文档中的 `.local/`、根 `.env.local` 和 `public/catalog/videos.json` 指旧路径。当前操作路径以本页为准；媒体对象 key、播放 URL 和目录中的逻辑引用没有改变。

提交前先 `git add` 明确的源码文件，再运行 `npm run check:repo` 检查暂存快照中的禁传路径、密钥值、常见 token 格式及大文件；扫描失败不推送。
