# 完整备份与独立恢复

> 目录迁移说明：当前命令从 `code/` 执行；旧 `.local/` 对应 `../local/runtime/`，旧根 `.env.local` 对应 `../local/secrets/.env.local`，实际目录在 `../local/catalog/videos.json`，实际存储配置在 `../local/config/storage.json`。新克隆默认布局及最新操作以 [工作区布局](workspace-layout.md) 为准。


创建新备份（输出不能已存在）：

```sh
.venv/bin/python scripts/backup_bundle.py create --output .local/backups/full-YYYYMMDD.zip
```

包内包含项目代码与依赖锁、配置中的环境变量引用、整个目录、原片备份、所有未清除媒体版本的文件和映射、对象台账、目录历史备份和操作记录。已清除版本仅保留映射墓碑；不把已删除内容称为可恢复。当前本机播放副本缺失或哈希不符会拒绝生成，避免交付不完整备份。备份不包含 `.env.local`、密钥、node_modules、虚拟环境、临时上传任务和浏览器内的互动/性能数据。

每个文件有SHA256和字节数；生成时扫描实际配置中的凭据值。播放清单重建为本地片段地址，映射标记 `recovery_playback=local-copy`，保留原远程放置信息。恢复后先用本地副本验证，不需要立即访问HF或Tigris。

恢复到尚不存在的目录：

```sh
.venv/bin/python scripts/backup_bundle.py restore --archive .local/backups/full-YYYYMMDD.zip --destination .local/recovery-YYYYMMDD
```

恢复会拒绝覆盖现有目录、路径穿越、重复成员、超过10GiB的解压总量、文件哈希不符。完整检查通过后才将临时目录切换为目标目录。换机器需按 README 安装 npm/Python 依赖及FFmpeg；运行 `npm run dev` 可先使用本地播放。继续上传时单独配置 `.env.local`，不通过备份包分发密钥。若以后调用 refresh，播放地址会按当前供应商配置恢复为远程地址。

2026-11-06 演练：首次包901文件、109个未清除版本；恢复到 `.local/recovery-demo`。恢复项目使用本机已有node_modules构建成功；`tests/browser/backup-recovery.cjs` 屏蔽全部外部请求，4条已发布演示（含原HF视频）均播放通过。`tests/python/test_backup_bundle.py` 验证损坏包、路径穿越和覆盖已存在目录被拒绝。后续包新增包含测试文件和已清除版本墓碑，文件数会变化。
