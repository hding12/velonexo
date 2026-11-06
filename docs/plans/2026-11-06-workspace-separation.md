# Workspace Separation Implementation Plan

**Goal:** 将当前工作区拆为可公开的代码仓和不上传的本地工作区，保留本地演示与 HF 上传能力。

**Architecture:** 根目录只作工作区容器。code/ 是唯一 Git 仓库；local/ 不初始化 Git。通过统一路径模块访问本地数据，不用散落的软链接或重复源码。

**Tech Stack:** Git, Node.js, Vite, Python, React。

## 目标布局

```text
velonexo/
├── code/                         # 唯一 Git 仓库，关联 hding12/velonexo
│   ├── .git/
│   ├── src/ server/ scripts/ tests/
│   ├── public/embeds/            # 静态公共资源
│   ├── config/                   # 无账号信息的默认配置与模板
│   ├── docs/ DESIGN.md README.md
│   ├── .env.example .gitignore
│   ├── package.json package-lock.json
│   └── node_modules/ .venv/ dist/ # 可再生，不跟踪；虚拟环境迁移后重建
└── local/                        # 不建 Git 仓库，不上传 GitHub
    ├── secrets/.env.local
    ├── config/storage.json       # 实际存储启停和配额配置
    ├── catalog/videos.json       # 实际内容目录
    ├── runtime/                  # 原 .local 的完整内容，保持内部结构
    │   ├── media/ publisher/ studio/
    │   ├── backups/ recovery-final/
    │   ├── acceptance/ fixtures/
    │   └── static-site/
    ├── experiments/              # 个人外链实验
    └── corpus/                   # 如以后复制语料，放这里；不搬动其他项目的原始语料
```

本地目录不等于第二个版本仓库：用现有备份能力保护业务数据，避免把密钥或大视频放入 Git 历史。源码中无敏感信息的设计、运行手册、测试保留；个人证据、日志、实际目录仅存本地。

## 1. 统一路径与独立克隆默认值

新增 scripts/workspace_paths.py 和 server/workspace-paths.js：分别导出 CODE_ROOT、LOCAL_ROOT、RUNTIME、CATALOG、STORAGE_CONFIG、ENV_FILE。

LOCAL_ROOT 优先读取 VELONEXO_LOCAL_ROOT；当前工作区设为 ../local。独立克隆未配置时用代码目录内 .local-work（必须忽略），避免多个独立克隆误共享同一个数据目录。前端不接触绝对路径和密钥。

新增 scripts/setup_local.py，以独占创建方式从模板生成缺失目录、空目录数据和存储配置；已有文件绝不覆盖。默认配置不得带真实账号标识。启动缺配置时提示初始化命令。

修改 scripts/storage_probe.py、media_storage.py、media_publish.py：源码相对路径继续使用 CODE_ROOT；业务状态改为上述本地路径。存储映射中的逻辑视频 ID、版本、对象 key 不变，不复制远端媒体。

## 2. 开发服务与构建

修改 server/studio.js 和 vite.config.js：Studio 状态写 RUNTIME，目录从 CATALOG 读取；/catalog/videos.json 与媒体路由从本地目录提供并保持浏览器 URL 不变。禁止向客户端暴露 secrets、备份目录和任意文件读取。

修改 scripts/export_static.py、check_artifacts.py：静态发布包在 LOCAL_ROOT/runtime/static-site 生成；构建秘密扫描读取 ENV_FILE。静态导出仍仅包含已发布内容及必要播放资产。

## 3. 维护、备份与测试兼容

修改 scripts/backup_bundle.py、media_maintenance.py、prepare_demo.py、hls_smoke.py、generate_acceptance.py 及 acceptance 脚本，消除旧根目录假设。

备份仍使用现有逻辑归档布局，明确源码和数据路径映射；恢复读取旧备份时保留兼容，不能直接对跨根目录路径调用 relative_to(CODE_ROOT)。恢复不能带入凭据。

修改 scripts/run_checks.cjs、run_delivery_checks.cjs、tests/browser 与 tests/server 中直接使用 .local、public/catalog 的地方，复用路径模块。增加临时目录测试：不同 LOCAL_ROOT 相互隔离、初始化不覆盖、目录可读但密钥不可经 HTTP 读取。

## 4. 实际迁移顺序

1. 记录当前目录与映射校验和，保存迁移清单和可恢复备份；检查 Studio 无活动任务。
2. 停止当前开发服务，避免迁移中写入目录。
3. 建立 local，将 .env.local、运行目录、实际内容目录、实际存储配置与个人实验移入对应位置；保持密钥文件权限 0600。
4. 将源码与 .git 移入 code；工作区根不保留 .git。不递归复制 code 到自身，不修改 Git 历史。
5. 重建 code/.venv，安装 scripts/requirements.txt 中依赖；不能假定移动后的虚拟环境入口仍有效。node_modules 按需重新 npm ci。
6. 从 code 启动开发服务，配置 VELONEXO_LOCAL_ROOT=../local；更新 README 中启动与初始化方式。
7. 核对迁移前后目录记录、媒体映射与原始媒体校验和，无内容丢失或远端重新上传。

迁移失败先停写，再依迁移清单反向移动并恢复旧代码；不删除 local 或回收备份以强行通过测试。

## 5. 验收与上传边界

- npm run build、npm test、npm run test:delivery 通过；测试结果落在本地工作区。
- 首页播放、Studio 读取与一次可逆元数据编辑正常；既有媒体逻辑 URL 不变。
- 本地备份、恢复到新目录、静态导出各检查一次。
- 在独立临时目录模拟新克隆，无私有文件也能初始化并生成本地演示。
- git ls-files 不包含任何 local 数据、密钥、真实目录、个人测试链接、依赖或构建产物；再次扫描实际密钥值及常见 token 格式。
- 只从 code 推送公开仓库，核对远端 main 与本地提交一致。

## 实施状态（2026-11-06）

目录迁移已完成，code 是唯一 Git 根，local 在仓库外。Node 共用模块实际为 server/workspace-paths.cjs，便于 Vite、ESM Studio 与 CommonJS 验收脚本复用；Python 使用 scripts/workspace_paths.py。本机标记 .workspace.local.json 指向 ../local 并被忽略。独立克隆默认 .local-work。

备份保持逻辑归档路径，恢复新代码时自动布局到恢复目录内 .local-work；旧归档保持原布局。Python 虚拟环境已重新创建，并离线复用已有锁定依赖、重建 CLI 入口；旧环境保留在 local/tools，未上传。

验收与上传边界见 docs/research/workspace-separation-2026-11-06.md。GitHub 可见性已确认 PUBLIC，上传状态以远端提交核对结果为准。
