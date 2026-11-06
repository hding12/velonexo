# 媒体迁移与旧版本清理

所有命令在项目根目录执行，复用发布锁。当前启用的远程目标是 `hf`，也可用 `local`；其他节点必须已配置并启用。

先预览批量迁移（最多50个稳定视频ID）：

```sh
npm run media -- migrate --provider hf video-a video-b
```

预览会从已校验原片生成目标版本，并检查整批容量，但不上传或改目录。执行：

```sh
npm run media -- --reason '迁移到HF' migrate --provider hf --apply video-a video-b
```

所有目标文件先上传和GET/HEAD/Range/CORS校验，全部成功后一次性切换目录引用。保留标题、日期、发布状态、标签、精选和专题引用；原版本不自动删除。任何一条失败，目录保持原引用；已上传部分保留台账，可重试或清理。目标不变的重试复用已上传对象，但仍重新校验。原片缺失或损坏时拒绝迁移，不从不明来源重建。

查看旧版本：

```sh
npm run media -- versions
```

返回版本、字节数与 protected 标记。当前目录的所有状态以及历史目录备份引用均受保护；不会为了释放容量自动删除备份。显式清理未引用版本：

```sh
npm run media -- clean-versions VIDEO_ID/REVISION
```

先验证整批候选，未知或受保护版本拒绝；远程删除逐对象登记，失败后可再次运行同一命令。只删除台账确认属于此版本的远程对象，本地播放副本同步移除，保留原片及purged墓碑。不会清理整个Bucket或自动清空CDN缓存。已经完全清理的版本不再出现在候选列表。

单元验收：`tests/python/test_maintenance.py` 覆盖整批失败原子性、原片校验、引用保护、删除中断续清及成功迁移保留元数据。真实HF验收：`.venv/bin/python scripts/acceptance_maintenance.py`，两条微小合成视频，隔离目录和台账，测试对象最终删除并检查HEAD404；不修改生产目录。
