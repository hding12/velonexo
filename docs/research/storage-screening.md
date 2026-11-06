# 存储候选初筛（2026-11-05）

> 历史阶段记录：双存储与签名测试描述的是当时验收。当前只启用HF公开地址，Tigris暂停；当前能力以 docs/plans/2026-11-06-next-delivery.md 和最新运行手册为准。
约束：完全免费、不绑支付方式；首轮真实双供应商；优先汇集容量，不做均衡调度或全量镜像。尚未完成账号侧和播放实测，未确认两家全部达标。

| 候选 | 已核验结果 | 下一步 |
|---|---|---|
| Tigris | 官方价格页明确 No card to start；5GB Standard、1万 Class A、10万 Class B/月；免出站费用不等于免读取费用 | 确认目标内容/外站 HLS 分发是否允许，以及免卡额度耗尽的行为；官方条款链接本轮返回404 |
| Catbox | FAQ 允许 NSFW，但外站视频流需事先批准 | 联系管理方确认免费使用许可、HLS片段及CORS支持；未获批准不接入 |
| B2 | 可免支付方式起步；首次公开 Bucket 要求支付历史或信用卡小额付款 | 不作为当前直接公开源；私有桶签名读取仅保留为待验证方案 |
| R2 | 开通需订阅 checkout，计量服务涉及支付方式 | 不列当前免支付方式首选 |
| Oracle / GCS | 官方明确要求支付方式 | 排除当前路径 |

其余文档候选按其用途分类暂不投入集成；不将软件仓库、试用服务或官方嵌入平台当成已批准的对象存储。

## 官方证据

- https://www.tigrisdata.com/pricing/
- https://catbox.moe/faq.php
- https://catbox.moe/legal.php
- https://www.backblaze.com/docs/cloud-storage-create-and-manage-buckets
- https://developers.cloudflare.com/r2/get-started/
- https://developers.cloudflare.com/billing/get-started/update-billing-info/
- https://www.oracle.com/cloud/free/faq/
- https://docs.cloud.google.com/free/docs/free-cloud-features

## 最小实施原则

单一 providers 配置加逐视频 media-map；优先整条放在一个节点，容量不足时手动选择其他节点或连续段组。新增节点不修改已有视频ID。先离线生成清单，不做自动搬迁、健康评分和复杂放置引擎。真实供应商接入等待账号及用途确认，不伪报完成。
