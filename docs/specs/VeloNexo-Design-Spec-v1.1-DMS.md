# VeloNexo｜成人视频与兴趣社区 产品与技术设计文档

> **文档版本**：v1.1（分布式分块存储架构修订版）  
> **编制日期**：2026-11-05  
> **项目代号**：`velonexo`（工作名称，未完成域名与商标核验）  
> **总体路线**：视频优先、论坛后置；每个阶段独立可上线、可运营、可回退  
> **架构约束**：TikTok 风格；Zyncat UI；尽可能免费；不维护常驻服务器；**DMS 分块映射 + 多节点存储 + HLS 流式播放为 V0.1 核心**；站点、媒体存储、CDN 分离；管理员管理视频；未来支持成人论坛。

> **v1.1 修订摘要（相对 v1.0）**：把 HLS/CMAF 分块、站点分段映射、多个合规对象存储、分段放置、故障降级和供应商政策准入列为 V0.1 核心；删除“分块待 V1.0 再做”的旧决策。GitHub、Hugging Face 等全部列入候选评估，但不因技术可上传而被视为允许托管成人内容。

---

## 0. 文档说明与决策摘要

### 0.1 一句话产品定义

VeloNexo 是面向成年用户的短视频发现与兴趣讨论站：首期由管理员发布经过授权的合法内容，使用类似 TikTok 的竖屏信息流；随后逐步增加外链聚合、内容后台、内容发现和论坛，不在初期开放用户上传视频。

### 0.2 已确定的关键决策

| 编号 | 决策 | 原因 |
|---|---|---|
| ADR-01 | 用 React 19 + Vite + TypeScript 构建单体前端 | 适合静态托管与独立迭代 |
| ADR-02 | 以 Zyncat UI 的 TikTok 组件作为视觉起点 | 复用已实现的互动区和版式，但不继承视频业务 |
| ADR-03 | Zyncat 的响应式适配为 **M0 阶段门槛** | 其移动预设是固定 452×822px，不能直接假设全屏适配 |
| ADR-04 | 播放、数据来源、内容管理分别定义接口 | 避免绑定某个存储商或外链平台 |
| ADR-05 | V0.1 用静态 JSON 目录发布内容，不依赖数据库 | 便于最早发布且回退简单 |
| ADR-06 | V0.2 才引入 Supabase Auth/Postgres 和管理员后台 | 不让后台开发阻塞第一版视频站 |
| ADR-07 | 自有视频以 HLS + fMP4 分段为正式发布路径；MP4 仅作基准与降级 | 满足分块映射、跨存储分布与边下边播 |
| ADR-08 | 外部视频只用允许的官方 Embed；不抓取原始流 | 降低版权、平台政策和转码风险 |
| ADR-09 | V1.1 才开放普通用户账号、文字发帖、评论 | 降低初期社区治理负担 |
| ADR-10 | 成人内容的合法性、服务条款及适龄访问为首版上线门槛 | 技术可播放不代表可以合法公开运营 |
| ADR-11 | DMS 以静态 JSON 保存分段映射，按合规提供商编译 HLS 清单 | V0.1 无需数据库即可按段定位与迁移 |
| ADR-12 | 保证首段同源、连续片段组放置，关键片段副本与多源回退 | 不以极端分散牺牲首帧速度 |
| ADR-13 | GitHub/HF 等列入候选清单，但根据内容/用途政策不作为成人站正式视频源 | 分块不能改变平台允许的业务范围 |

### 0.3 关键非目标

- 不做直播、私信、算法级个性化推荐、用户视频上传、广告投放系统或支付系统。
- 不要求所有外部视频都能实现与原生 MP4 相同的自动播放和进度控制。
- 不通过任意拆分二进制文件来规避内容审核、版权审查或服务商条款。
- 不在第一阶段运行独立的 Laravel、Django、Redis、FFmpeg 转码服务器。

---

## 1. 品牌与产品边界

**候选品牌**：VeloNexo  
**西语副标题**：*Mira. Explora. Conversa.*  
**频道名称**：VeloNexo Play（视频）、VeloNexo Foro（论坛）、VeloNexo Studio（管理）。

“Velo”可让人联想到面纱、隐私；“Nexo”表示连接。名称仅作工作品牌，不能推断域名、商标、社交账号可注册。正式发布前完成名称检索、商标冲突检查和目标市场语言测试。

### 1.1 目标用户与内容模式

- **访客**：在具备合法访问资格的前提下，浏览竖屏短视频、分类和专题，不必为了看公共内容先创建论坛账号。
- **管理员**：自行准备视频，填写标题、分类、封面、来源、授权记录，进行审核与发布。
- **论坛用户（V1.1）**：注册后发文字帖子、回复、引用已有视频、举报内容。
- **审核人员（V1.1）**：处理举报、限制帖子、执行下架、审查合规材料。

### 1.2 允许与禁止内容的产品边界

必须建立书面内容政策，至少明确：仅允许合法且经授权的成年人内容；禁止未成年人性内容、未经同意的私密影像、冒用、侵权、胁迫等违法内容；建立举报、下架、申诉与记录保存机制。对第三方嵌入内容也应能隐藏、移除或阻断本站分发。

**上线前置决定**：确定目标国家/地区、内容属于教育/商品展示还是露骨作品、是否包含真人表演者、允许的访问国家、运营实体，以及相应的年龄保证与记录保存义务。未经法律和服务商核查，不能把公开 MP4 URL + “18+” 弹窗作为通用合规方案。

---

## 2. 阶段路线：每一阶段都能独立上线

| 阶段 | 独立产品 | 新增功能 | 必要服务 | 上线后即使停止开发是否可用 |
|---|---|---|---|---|
| **M0 技术验证** | 内部演示，不公开 | Zyncat 适配、HLS 分段、2个合规存储节点、滑动与内容策略核查 | 本地 React | 否，属于发布门槛 |
| **V0.1 视频站** | 可长期使用的视频展示站 | **HLS分块 + 静态分块映射 + 多节点路径**、基础外链、分类、详情页、举报/下架 | Cloudflare Pages + 合规视频存储/CDN | **是** |
| **V0.2 内容后台** | 可独立运营的视频 CMS 站 | 管理员登录、Web 发布、分块直传与映射管理、多平台导入、发布状态 | + Supabase + Serverless Functions | **是** |
| **V1.0 视频体验** | 完整短视频发现产品 | 分块/节点性能优化、稳定预加载、搜索、热门/专题、错误降级、指标 | 沿用 V0.2 | **是** |
| **V1.1 论坛社区** | 视频 + 成人兴趣论坛 | 普通用户账号、板块、文字帖子、回复、举报审核 | 沿用 Supabase | **是** |
| **V2.0 增强（可选）** | 轻社交社区 | 收藏、关注、通知、可解释推荐、站内专题 | 视实际需求 | **是** |

**独立上线原则**：每阶段必须包括当期必需的法律/安全控制、备份、故障降级、部署手册和独立验收。后续功能必须通过开关与接口增量接入，不得要求前一阶段迁移后才能继续使用。

### 2.1 M0｜技术与合规可行性门槛

**实现范围**：安装 Zyncat TikTok 组件，嵌入 HLS 分块视频、MP4 基准视频和 YouTube 测试视频；验证至少两个经许可的对象存储节点、跨域 HLS、Safari 与回退；用 CSS Scroll Snap 或 Embla 验证竖向滑动；对 360/390/430px 手机宽度与桌面进行真实设备测试；确认托管商可接受目标内容类型。

**退出标准**：① 当前视频独占播放；② 不裁切互动按钮；③ 不被 iframe 长期拦截滑动；④ 页面离开时停止音频；⑤ 有确定的内容政策和适龄访问方案；⑥ 合法托管商已确认。若 Zyncat 固定布局改造超过预定范围，改为“保留视觉设计、使用轻量响应式卡片”，不反复叠加缩放补丁。

### 2.2 V0.1｜独立视频站（首个公开版本）

**必须提供**：

1. TikTok 风格全屏视频流；上下滑动、暂停、默认静音、封面占位、加载失败处理。
2. **HLS + fMP4 分块播放为必需**：分块映射在站点、二进制块在外部存储，至少两种授权供应商适配，支持同源首段与连续片段组放置；MP4 只作为基准/后备。外链优先支持 YouTube。
3. 分类、标签、最新排序、静态基础搜索、独立视频分享地址 `/video/:id`。
4. **纯静态目录与分块映射**：`public/catalog/videos.json`、`public/media-maps/<id>.json`、预生成 `*.m3u8`；管理员离线分块、上传、校验后通过 Git 自动发布。
5. 管理员可随时撤下视频：更改目录状态、重新构建、必要时撤销媒体源访问并清理 CDN 缓存。
6. 投诉/侵权/隐私举报入口、联系渠道、版权和隐私声明；按目标市场采用实际有效的适龄访问措施。
7. 基础日志、容量监控、源文件备份和站点回滚说明。

**不需要**：Supabase、用户账户、点赞持久化、评论、论坛、内容推荐算法。

**单独上线标准**：30 条以上混合测试视频连续滑动；公开 URL 可访问；合法区域、权限、浏览器、暂停和下架流程通过；无需开发环境或运行时数据库即可持续运营。

### 2.3 V0.2｜内容管理与多来源聚合

**新增**：Supabase Auth 管理员、Postgres 视频目录、Studio 管理台、视频导入/编辑/发布状态机、**分块上传、节点状态、映射生成、校验及容量监控**、来源 URL 识别、YouTube/X/Instagram/TikTok 官方 Embed、内容批量下架。

**迁移**：保留 V0.1 原有 `id`；编写一次性 JSON→Postgres 导入脚本；保留 JSON 导出/只读回退，以免数据库故障导致视频目录全部不可用。

**独立上线标准**：非开发人员可在浏览器完成“添加→预览→发布→下架”；无 React 源码更改；匿名用户不能写表；服务端强制管理员权限；外链失效不阻断视频流。

### 2.4 V1.0｜完整视频体验

**新增**：虚拟化视频窗口、下一条适量预热、外部 iframe 懒加载、完善分类/标签搜索、热门/最新/精选、播放监控和错误分析、移动端专项优化；**依据 A/B 结果调整 HLS 分段时长、清晰度、跨节点分配与 Safari 备用清单**。

**独立上线标准**：弱网与移动设备可用；站点稳定可运营；可解释排序不会把只曝光的外部视频误判为“已完整观看”。

### 2.5 V1.1｜论坛产品

**新增**：普通用户注册、公开论坛板块、文字帖子、回复/楼中楼、帖子引用视频、点赞/举报、封禁/限流、审核队列、社区规则、数据导出。

**明确不做**：第一版论坛不允许普通用户上传视频/图片；不要求每个视频必须存在论坛帖子；不把论坛故障传播到视频流。

**独立上线标准**：板块/帖子/回复完整可用；用户只能编辑自己的内容；管理员能冻结、隐藏、下架；关闭论坛功能开关后视频继续正常运行。

### 2.6 V2.0｜可选增长模块

根据真实用户行为逐项决定：收藏、关注、通知、推荐权重优化、多语言、搜索增强、个性化发现。普通用户上传媒体需另立项目，先具备授权验证、投诉响应与有效审核能力后再考虑。

---

## 3. 系统架构与职责分离

```text
Browser (React 19 / Vite / Zyncat UI)
  ├─ Feed / Video Detail / Explore
  ├─ Official Embed adapters: YouTube / X / Instagram / TikTok
  ├─ Native Player: required HLS/fMP4 via Video.js / Safari; MP4 fallback
  ├─ Forum (V1.1)
  └─ Studio (V0.2)
       │
       ├── Cloudflare Pages (static UI / versioned deployment)
       ├── Supabase (V0.2+: Auth, Postgres, RLS, content APIs)
       ├── Pages Functions / Workers (admin auth, upload URL, publish, optional age gate)
       └── DMS Distributed Media Storage (no Supabase video proxy)
             ├── site media-maps/<id>.json → HLS playlist builder
             ├── compliant object stores (R2/B2/Tigris/...): init + *.m4s chunks
             ├── placement groups / primary + replicas / provider policy gate
             └── CDN or protected media gateway (only as legally required)
```

### 3.1 核心边界

- **ContentRepository**：`listVideos(cursor, filter)`、`getVideo(id)`；V0.1 读取静态 JSON，V0.2 后切到 Supabase。业务组件不关心存储格式。
- **MediaResolver + StorageRegistry + ManifestBuilder**：解析分块 Map 中的 `provider + object_key`，按供应商合规性与健康状况生成 HLS 清单；永久 CDN URL 不作为唯一主键。
- **PlayerAdapter**：`mount / play / pause / mute / destroy / capabilities`；各平台声明能力，不虚构未开放的播放事件。
- **PublicationService**：草稿、预览、发布、下架；只在可信服务端改变管理员内容状态。
- **ForumService**：独立命名空间与数据访问层，运行失败不得影响视频服务。

### 3.2 架构否决项

- 不能将 R2 私钥、Supabase `service_role` 或上传密钥编译进前端。
- 不能通过服务器函数转发大体积视频文件，除非是明确设计的受控访问网关。
- 不能将视频切成未知格式 `.bin` 后假设能绕过内容治理；公开播放仍然可被用户重建。
- 不能将第三方视频网站网页地址直接传给 `<video src>` 并期望播放。
- 不能假设公开 R2 文件被前端“18+”遮罩后就具有真实的访问限制。

---

## 4. 前端交互与 Zyncat 改造设计

### 4.1 Zyncat 的真实定位

Zyncat `@zyncat/ui/tiktok` 提供单条 Post 的 UI：`media: ReactNode`、`liked`/`onLikedChange`、`onAction`、`surface`、`ratio` 等。它**没有**数据加载、视频自动播放、登录和无限 Feed。其 `mobile` 预设固定为 452×822px，桌面为 1584×912px。必须把响应式布局作为第一验收门槛，而不是后续优化。

**原则**：优先保持上游包不改；如需改动固定尺寸，采用独立包装层并明确测试。若需要大量覆写绝对定位，应从其 MIT 许可的 UI 构造思想中抽取视觉样式，自行实现响应式 `VideoCardShell`，避免深度绑死上游版本。

### 4.2 页面与导航

| 路由 | 阶段 | 用途 |
|---|---|---|
| `/` | V0.1 | 视频流，默认最新/精选 |
| `/explore` | V0.1 | 分类、标签、简易搜索 |
| `/video/:id` | V0.1 | 单视频详情、分享与举报 |
| `/policies/*`、`/report` | V0.1 | 政策、投诉及下架渠道 |
| `/studio`、`/studio/media` | V0.2 | 管理员内容管理 |
| `/forum`、`/forum/:slug` | V1.1 | 论坛首页、板块列表 |
| `/post/:id` | V1.1 | 文字帖子、回复 |
| `/profile/:handle` | V1.1 | 公开资料与发帖记录 |

移动端：视频占可用视口，右侧互动列，底部导航；评论抽屉覆盖而非替换视频路由。桌面端：左导航、中央竖屏媒体、可选侧边详情。必须兼容安全区域、缩放、横屏、减少动画偏好和键盘操作。

### 4.3 视频流状态机

`DORMANT → PREFETCHED → MOUNTED → ACTIVE → PAUSED → DISPOSED`

- `ACTIVE`：最多一个，尽量只有当前视频持有解码器。
- `PREFETCHED`：最多下一条预热少量元数据/封面，按网络条件扩张。
- `MOUNTED`：保留当前及相邻卡片；其他只保留轻量数据。
- `DISPOSED`：页面切走时销毁原生播放器/HLS 句柄；对不能确保暂停的 X/Instagram iframe，直接卸载。
- 交互：点击暂停、上下导航、默认静音、自动播放被拒绝时展示手动播放控件。
- 有多个平台时不得假设所有播放器都支持 `seek/watchProgress`。

### 4.4 外部视频适配能力

| 来源 | 识别 | 播放 | 暂停能力 | 失败处理 |
|---|---|---|---|---|
| Native MP4 / HLS | 自己上传 | Video.js / HTMLVideoElement | 完整 | 重试、备用源、隐藏 |
| YouTube Shorts/Watch | 视频 ID | 官方 IFrame API | 可调用 API，受策略限制 | 原站链接 + 状态提示 |
| TikTok | Post ID | 官方 Embed Player | 通过官方消息接口 | 官方链接 + 跳过 |
| X | Post ID | 官方 Embedded Post/Video | 不保证可靠控制 | 离屏卸载 iframe |
| Instagram Reels | shortcode | 官方 Embed | 不保证可靠控制 | 封面占位或原站链接 |

不能覆写或遮挡第三方播放器的品牌和受保护控件；不能为了“统一外观”下载并重托管无授权视频。应尊重平台嵌入许可与浏览器自动播放限制。

---

## 5. 内容模型与数据版本演进

### 5.1 V0.1 静态 JSON 与 DMS Map（简化示例）

```json
{
  "schema_version": 1,
  "videos": [
    {
      "id": "vid_0001",
      "title": "Example title",
      "description": "Editorial description",
      "source": {"kind": "native", "format": "hls", "media_map": "/media-maps/vid_0001.json", "playlist": "/playlists/vid_0001/index.m3u8"},
      "poster_key": "media/vid_0001/poster.webp",
      "category": "featured",
      "tags": ["example"],
      "visibility": "published",
      "access_class": "age_restricted",
      "published_at": "2026-11-05T12:00:00Z"
    }
  ]
}
```

**注意**：媒体分块的完整 provider/location 映射见第6章，视频目录本身只保存 media_map/playlist 的稳定引用。`age_restricted` 内容如果需要真实访问限制，`MediaResolver` 必须走受保护的媒体网关，并在媒体请求层验证访问资格。不得把完整直链藏在前端 JSON 里却保持 Bucket 公开。

### 5.2 V0.2+ 关系模型

| 表 | 主要字段 | 上线阶段 |
|---|---|---|
| `media_assets` | `id`, `provider`, `source_type`, `external_id`, `object_key`, `format`, `poster_key`, `status`, `access_class` | V0.2 |
| `video_entries` | `id`, `media_id`, `title`, `summary`, `category_id`, `published_at`, `rank_override`, `status` | V0.2 |
| `categories` | `id`, `slug`, `name`, `sort_order` | V0.2 |
| `tags` / `video_tags` | 标签及关联 | V0.2 |
| `admin_memberships` | `user_id`, `role`, `enabled` | V0.2 |
| `publication_events` | `entry_id`, `action`, `actor_id`, `at`, `reason` | V0.2 |
| `profiles` | `id`, `handle`, `display_name`, `status` | V1.1 |
| `forum_topics` | `id`, `slug`, `name`, `moderation_policy` | V1.1 |
| `forum_posts` | `id`, `author_id`, `topic_id`, `title`, `body`, `quoted_media_id`, `status` | V1.1 |
| `forum_comments` | `id`, `post_id`, `parent_id`, `author_id`, `body`, `status` | V1.1 |
| `reactions` | `actor_id`, `target_type`, `target_id`, `reaction_type` | V1.1 |
| `reports` / `moderation_actions` | 被举报对象、理由、状态、决定与审计 | V1.1 |

**重要建模原则**：视频资产与论坛帖子分离。一个视频可被多个论坛帖子引用，但论坛回复围绕具体帖子；视频流的独立视频详情后期可映射到一个“主讨论帖”，不要混用多张评论表。V1.1 需选择视频评论与论坛回复是否统一到帖子对象上，并提供兼容的 API。

**索引建议**：`video_entries(status,published_at,id)`、`video_entries(category_id,published_at)`、`forum_posts(topic_id,created_at,id)`、`forum_comments(post_id,created_at,id)`；游标分页优于无限 OFFSET。主键稳定不可从 CDN URL 派生。

### 5.3 内容状态机

```text
DRAFT → READY_FOR_REVIEW → PUBLISHED → UNLISTED / REMOVED
                        ↘ REJECTED
```

`REMOVED` 不仅从 Feed 隐藏，还应停止可访问的媒体链接或执行撤权/缓存失效。公开外链被删除、改私有或禁止嵌入时，独立标记 `SOURCE_UNAVAILABLE`，不得误判为本站视频已删除。

---

## 6. DMS 分布式媒体存储：分块映射、多供应商分布与低延迟播放（V0.1 核心）

> **本章为 v1.1 的核心新增设计，并取代 v1.0 第 6 章。** DMS = Distributed Media Storage。必须在 M0 验证，V0.1 有可用的多节点映射和分段播放路径。所有候选存储服务均需通过内容政策、用途政策、技术与成本门槛；列入清单不代表获准托管成人露骨内容。

### 6.1 设计目标与不可违反的边界

| 要求 | 设计承诺 | 验收口径 |
|---|---|---|
| 分块 | 以 HLS + CMAF/fMP4 的**标准媒体分段**作为正式路径 | 播放器边下边播，无须下载完整文件后拼接 |
| 映射 | 站点保存**视频 → 清晰度 → 初始化片段/媒体片段 → 供应商对象**的完整索引 | 用 JSON 还原每个片段所在的存储位置 |
| 多平台 | 同一视频不同片段或多个副本可在不同的、已获准的存储节点 | R2/B2 等至少两个合规节点完成实测 |
| 低延迟 | 首段同源、少量预热、连续片段分组、缓存与主动降级 | 自有视频首帧 P75 ≤ 2 秒；已预热切换 P75 ≤ 0.5 秒（目标值，非承诺） |
| 独立上线 | V0.1 不依赖 Supabase、论坛、后台或常驻转码进程 | Git JSON + 静态播放清单 + 外部文件服务即可发布 |
| 容灾 | 每片段可声明多个 `locations`，读取失败可尝试**合规的**副本 | 断开备份源后正常播放；断开主源后可恢复 |
| 数据可迁移 | 分块源信息保存 `provider_id + object_key`，不以 CDN URL 为唯一主键 | 更换供应商后视频 ID、帖子引用均不变 |
| 合规 | 分块不用于绕过审核、滥用免费仓库或规避访问限制 | 不合规节点绝不进入正式播放映射 |

**重要区别**：一个媒体分段虽然不一定是独立可播放的完整视频，但仍可被识别为媒体数据。改扩展名、随机命名或碎片化不等于隐私保护，不能将其当成规避平台政策的策略。若需要隐私保护，应使用合法的加密与访问控制；对公开视频，客户端始终有机会恢复媒体内容。

### 6.2 播放架构：在浏览器中连续流式解码

```text
管理员本地视频
   │
   └─ FFmpeg 编码 + HLS/fMP4 分段 + 生成 SHA-256、封面
      │
      ├─ init.mp4             ───→ Provider A (授权主节点)
      ├─ seg_0000.m4s         ───→ Provider A；关键首段可复制到 B
      ├─ seg_0001.m4s         ───→ Provider A；关键首段可复制到 B
      ├─ seg_0002.m4s         ───→ Provider A
      ├─ seg_0003.m4s         ───→ Provider B
      ├─ seg_0004.m4s         ───→ Provider B
      ├─ seg_0005.m4s         ───→ Provider B
      └─ ...                  ───→ 合规 Provider A/C/... 按连续段组放置
             │
             ▼
  网站数据：catalog/videos.json + media-maps/<id>.json
             │
        Manifest Builder（发布阶段离线生成）
             │
             ▼
       /playlists/<id>/index.m3u8
             │
             ▼
      Video.js/HLS.js 或 Safari 原生 HLS
             │
             └─ 根据清单向各合规节点 GET 片段→缓冲→持续解码
```

浏览器**不负责把零散字节下载完、合并成最终 MP4**。标准 HLS 解码器读取 `m3u8`、`init.mp4` 和媒体片段即可边下边播。Apple HLS 官方规范要求 fMP4 使用 `EXT-X-MAP` 并保持片段时间戳连续；短视频可测试 2–4 秒分段，Apple 常规 VOD 作者规范仍以约 6 秒作为推荐目标。是否采用 2、4 或 6 秒必须根据短视频与真实网络数据决定。

### 6.3 为什么不能简单每段轮流放一个网站

每个来源都可能引入不同的 DNS/TLS 连接、RTT、缓存命中率、重定向与 CORS 策略。如果一条 30 秒视频有 15 个 2 秒片段，轮流访问 5 家文件服务，播放中途很容易遭遇慢节点；任何一个片段不能及时加载都可能造成卡顿。

**正式分配策略：**

1. **同源首屏**：`index.m3u8`、初始化片段及首 2–3 个片段尽量由快速、已授权且有 CDN 的节点提供；优先保证第一帧，而不是极致分散。
2. **连续片段分组（Placement Group）**：其余片段按 3–6 个为一组，整组放在同一提供商，避免每 2 秒跨域切换。
3. **优先存储整条视频到单一可靠供应商，其次做跨供应商冷备**：当免费容量不足时才启用按片段组分摊；不能因为可分块就默认一定更快。
4. **重要片段冗余**：优先复制 `init` 和开头两个片段；关键内容可增加完整备用清单/全片镜像。
5. **严格合规筛选**：供应商不允许该内容、第三方视频热链或商用分发时，不参与放置或故障切换。

这区分三个模式：`single_origin`（单主源，基准）、`striped`（连续片段组横向分布）、`mirrored`（主源加副本，最可靠）。推荐 V0.1 默认 `single_origin` 或低比例 `mirrored`；`striped` 作为已验证合规供应商之间的可配置模式，而不是上线唯一可用路径。

### 6.4 元数据、分块索引和发布清单

**站点保存两个层次的映射：**

- `catalog/videos.json`：视频列表信息，只含 `video_id`、标题、封面、`media_map` 路径、发布状态。
- `media-maps/<video_id>.json`：媒体版本、编码参数、分块顺序、时长、大小、校验和、各存储位置与优先级。站点不保存原始视频二进制。

**DMS Map v1（字段示例，实际 SHA-256 使用真实值）**：

```json
{
  "schema_version": 2,
  "video_id": "vid_0001",
  "revision": 1,
  "mode": "striped",
  "access_class": "public_only_if_permitted",
  "renditions": [{
    "id": "480p",
    "codecs": "avc1.42e01e,mp4a.40.2",
    "width": 480,
    "height": 854,
    "bandwidth_bps": 900000,
    "init": {
      "object_id": "sha256:init-actual-hash",
      "locations": [
        {"provider_id": "r2_primary", "object_key": "v001/r1/480/init.mp4", "priority": 10},
        {"provider_id": "b2_backup", "object_key": "v001/r1/480/init.mp4", "priority": 20}
      ]
    },
    "segments": [
      {"seq": 0, "duration_ms": 2000, "size_bytes": 225000,
       "sha256": "REPLACE_WITH_REAL_SHA256",
       "locations": [
         {"provider_id": "r2_primary", "object_key": "v001/r1/480/0000.m4s", "priority": 10},
         {"provider_id": "b2_backup", "object_key": "v001/r1/480/0000.m4s", "priority": 20}
       ]},
      {"seq": 1, "duration_ms": 2000, "size_bytes": 220000,
       "sha256": "REPLACE_WITH_REAL_SHA256",
       "locations": [{"provider_id": "r2_primary", "object_key": "v001/r1/480/0001.m4s", "priority": 10}]},
      {"seq": 2, "duration_ms": 2000, "size_bytes": 230000,
       "sha256": "REPLACE_WITH_REAL_SHA256",
       "locations": [{"provider_id": "b2_backup", "object_key": "v001/r1/480/0002.m4s", "priority": 10}]}
    ]
  }]
}
```

**说明：** JSON 是技术结构示例，片段列表被截短，`sha256` 不是真实哈希，不可直接作为播放清单上线。生产环境的存储节点必须先经过视频内容、商业用途、直链、CORS 与流量授权核验；对于需要限制访问的视频，这份静态 JSON 仅可保存不泄露私有对象的逻辑标识，不能把任何可绕过适龄访问的公共资源 URL 编入页面。

**供应商配置**：`providers.json` 只保存公有配置（`provider_id`, `base_url`, `status`, `supports_cors`, `supports_range`, `policy_approved_for_content`, `max_storage_bytes`, `request_budget`）。密钥应在本地发布工具或 Serverless Secrets 中，不进入 Git。

**离线生成的 HLS 清单**可以包含属于不同、已授权视频源的绝对 URL：

```m3u8
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:2
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-MAP:URI="https://media.example.com/v001/r1/480/init.mp4"
#EXTINF:2.000,
https://media.example.com/v001/r1/480/0000.m4s
#EXTINF:2.000,
https://media.example.com/v001/r1/480/0001.m4s
#EXTINF:2.000,
https://media-backup.example.net/v001/r1/480/0002.m4s
#EXT-X-ENDLIST
```

`media.example.com` / `media-backup.example.net` 是结构示例，并非真实可访问地址。清单的 `EXTINF` 必须由实际分段时长生成，片段必须有正确的媒体类型和时间戳。若不同域名禁止跨域拉取，则不能直接进入播放清单。

### 6.5 多供应商清单：全部已讨论过的免费/低成本方案

本清单是**候选评估范围**，不是“免费资源站可随意放置成人视频”的授权。表中的“适配”仅说明通用二进制/视频技术能力；能否正式使用还取决于对具体成人内容的条款确认。

**A. 通用对象存储：优先验证（具备原生二进制能力）**

| 服务 | 当前免费资源或条件 | 分段/HLS 适配 | 正式用途判断 |
|---|---|---|---|
| **Cloudflare R2 Standard** | 10GB-month、100万次 Class A、1000万次 Class B/月；出站免费 | 高；自定义域名可接 Cloudflare 缓存 | **优先试验主源**；内容用途需确认，超额会计费 |
| **Backblaze B2** | 前10GB存储免费；一般出站免费额度为月平均存储量的3倍；合作伙伴另有规则 | 高；需验证 CDN/CORS/Range | **优先试验备份源**；成人内容与商业分发需确认 |
| **Oracle Object Storage** | Always Free only：20GB 总量、每月5万次 Object Storage API 请求 | 技术上可直接供文件访问 | **低请求备份/归档候选**；不适合大量连续分段 GET |
| **Google Cloud Storage** | 限定美国区域：5GB-month、5千次 A 操作、5万次 B 操作、条件性的100GB/月出站 | 高 | 小规模备用；地区、流量和用途限制需要验证 |
| **Tigris** | 5GB Standard、1万次 A 操作、10万次 B 操作/月；出站免费 | 高；S3兼容 | **第二/第三对象存储候选**；读请求额度相对较低 |
| **AWS S3** | 有新账户免费积分/试用等变化，不应假定长期永久免费 | 高 | 兼容适配器/付费迁移备选，不列入零月费承诺 |
| **Storj** | 30天免费试用，之后为付费服务 | 高；S3兼容、可加密存储 | 备份/隐私方案候选，不是长期 $0 正式节点 |
| **bunny Storage** | 14天试用；标准存储约 $0.01/GB/月，账户 $1/月最低消费 | 高，且可连接 bunny CDN | **低成本付费后备**；不是永久免费 |

来源：R2 官方计费、B2 官方计费、Oracle Always Free、Google Cloud Storage Pricing、Tigris Pricing、Storj Pricing、bunny Storage Pricing（详见文末本章官方链接）。

**B. Git、软件仓库和公共文件服务：保留在研究清单，但不作为成人站正式视频节点**

| 服务 | 免费能力/限制 | 关键问题 | 成人站采用结论 |
|---|---|---|---|
| **GitHub 普通 Git Repo** | 可保存小文件；Git 历史、大小与过量使用有限制 | 不是媒体 CDN；GitHub 明确禁止色情内容 | **排除** |
| **GitHub Releases Assets** | 每个资源 <2GiB，单 Release 最多1,000个 Assets；没有规定该功能的固定总带宽限额 | 下载链接、重定向、MIME/Range 不稳定；过量带宽政策；色情内容被禁止 | **排除**，仅可对合法非色情软件资产做实验 |
| **GitHub Git LFS** | Free 10GiB 存储 + 10GiB/月下载带宽 | 播放带宽非常有限；色情内容被禁止 | **排除** |
| **GitHub Container Registry (GHCR)** | 容器镜像存储/带宽当前免费 | OCI Registry 不是 HLS CDN；媒体分发不符用途预期；GitHub 内容政策仍适用 | **排除** |
| **GitHub Packages** | 公共包免费；私有套餐另有限额 | 软件包分发用途，不适合高频短视频流 | **排除** |
| **GitLab Git Repo / LFS** | GitLab.com Free 项目仓库 + LFS 约10GiB | Git/软件仓库并非视频 CDN；具体成人内容政策另核实 | **不入生产** |
| **GitLab Generic Package Registry** | 可分发二进制软件包；平台另有限速/项目和注册表约束 | 不提供视频流 SLA/播放器能力 | **不入生产** |
| **Hugging Face Datasets / Models** | 免费公开空间 best-effort，免费私有空间100GB | 公共空间旨在可复用的 ML 资产，明确反对无关数据滥用；私有库不支持匿名直链；内容政策仍有效 | **不用于成人商业视频 CDN**；仅真正有 ML 价值且获准的独立数据集适用 |
| **npm Registry** | 公共 npm 包 | 包注册表，非任意媒体托管和视频 CDN | **排除** |
| **jsDelivr** | 免费开源资源 CDN | 官方明确禁止大量视频/通用媒体托管，并禁止露骨性内容 | **排除** |
| **Cloudflare Pages Static Assets** | 单文件 25MiB、免费版20,000文件、500构建/月；静态请求不计费 | 当前 Range 返回200而非规范206；频繁发布会反复部署；内容/用途政策仍适用 | **仅放少量公开清单、封面或合法静态素材**，不做主媒体节点 |
| **Internet Archive** | 公共档案上传免费，无一般性固定总容量保证 | 公共归档服务，不保证流媒体 SLA/敏感内容许可 | 仅对确有公共保存价值、拥有权利且符合政策的材料考虑 |
| **Catbox** | 免费文件上传；允许一定 NSFW 内容 | FAQ 明确要求商业服务、第三方站点视频流先获得批准 | **未获批准不得接入**；有书面许可才可能试验 |
| **Google Drive** | 个人账户共享 15GB（含 Gmail/Photos） | 分享/直链/配额、过期和 CORS 不适合稳定 HLS | 不作为生产视频源 |
| **Telegram** | 文件/媒体云存储能力 | 非公开 CDN；媒体链接/访问接口不适合稳定浏览器分段 | 不作为生产视频源 |
| **IPFS 公共网关** | 开放协议，不等于免费永久托管服务 | 需要独立 Pinning；网关限速与可用性不可保证 | 仅探索归档/内容寻址，必须另选正式存储服务 |

**C. 专业视频网站与媒体平台：通常应使用官方播放器，不是通用分块对象仓库**

| 服务 | 免费层（2026-11核实/沿官方定价口径） | 主要局限 | 使用方式 |
|---|---|---|---|
| **YouTube** | 官方上传和嵌入可免费使用，未承诺无限固定配额 | 播放器受平台规则控制；色情露骨内容禁止 | **仅经许可的合规外链嵌入**，不作为自有 HLS 块存储 |
| **Wistia Developer** | 25GB存储、200GB带宽门槛前免费；超额后按其 Developer 计划计费 | 视频营销服务，内容政策、嵌入与计费需确认 | 正规非限制内容的托管替代，不做二进制分块节点 |
| **Gumlet Free** | 60分钟存储、100GB/月带宽 | 存储时长限制，完整 API 等功能在付费计划 | 正规视频整托管替代；内容政策另核实 |
| **Cloudinary Free** | 25 Credits/月共享给存储、带宽、转换 | Credits 消耗难按普通 GB 比；内容政策限制 | 非敏感素材处理或符合政策的视频服务 |
| **ImageKit Free** | 3GB存储、20GB/月带宽、500视频处理单位/月 | 新视频处理/带宽不足支撑长期增长 | 图片、封面或合规小规模视频 |
| **Vimeo Free** | 可嵌入/非公开媒体使用3GB Managed storage 和1TB/月 Managed bandwidth | 公共但不可嵌入的视频不限量并不能用来托管本站视频 | 官方嵌入且符合政策时考虑 |
| **Mux Free** | 最多10条视频，100,000分钟/月播放 | 存储资产条数限制 | 视频处理/播放器实验，不适合作为规模化自有库 |
| **bunny Stream** | 试用后付费；视频转码/存储/CDN整体服务 | 不是永久免费 | 当分块系统成本/延迟得不偿失时的可替换付费方案 |

**正式接入规则**：成人内容的合法性、表演者成年及同意记录、托管商内容政策、商业热链允许度、年龄访问机制必须独立核实。**不得因文件被拆块、命名为无扩展名或存放在多个免费账户，就把明确不允许的内容分发给该供应商。**

### 6.6 存储提供商适配器与放置引擎

存储 API 分成写端与读端两种能力：

```ts
type ProviderId = string;
type ObjectKey = string;

type ProviderCapabilities = {
  upload: boolean;
  directHttps: boolean;
  cors: boolean;
  range206: boolean;
  stableUrls: boolean;
  contentTypeSupport: boolean;
  permittedContentAndUse: boolean;
};

interface StorageWriter {
  put(key: ObjectKey, file: Uint8Array, contentType: string): Promise<void>;
  head(key: ObjectKey): Promise<{size: number; etag?: string}>;
  delete(key: ObjectKey): Promise<void>;
}

interface StorageRegistry {
  resolvePublicLocation(provider: ProviderId, key: ObjectKey): URL | null;
  eligibleProviders(accessClass: string): ProviderId[];
}
```

V0.1 只需要实现对象存储适配器 `R2Storage` 和 `B2Storage`（或 `TigrisStorage`），通过同一个离线发布工具上传，生成 JSON。GitHub/HF 等不合规或不适合服务被赋予 `eligible=false`，不能通过配置误加到成人片段播放清单。

**离线 Placement Planner** 根据：内容政策、可用免费容量、月读取额度、离用户距离、CORS/Range 能力、健康检查结果、现有副本，选择每个片段所在节点；优先 `single_origin`，其次整组分布。所有上传先校验 SHA-256，成功后再发布 manifest（**先文件后清单**，避免对不存在文件的引用）。

### 6.7 播放器容错、Safari 降级与存储故障

**V0.1 基本线路**：离线生成完全可用的、直接指向已验证服务的 `m3u8`。浏览器不经过 Supabase 拼接。`hls.js` 可通过加载器扩展对**暂时性网络故障**使用 Map 中的下一合规镜像，但应限制重试次数和超时。对于明确的政策拒绝、非法访问或年龄限制 403，不得切换其他供应商来规避限制。

**Safari 原生 HLS** 不能假设支持 JS 自定义 segment loader。V0.1 建议整条视频提供一个同源备用清单；播放中故障时暂停、切换清单，尽可能恢复 `currentTime`。如果没有完整副本，只能提示重试/跳过；不要宣传为无缝故障切换。

**可选统一 Media Gateway**：V1.0 可加入轻量边缘路由，提供固定的 `https://media.example.com/...` 路径，按映射获取合规存储。公开内容可优先生成重定向，但每次重定向会增加请求/缓存开销；受限内容需真正的服务端授权与受控媒体访问，而且 Workers 免费请求额度可能很快耗尽。不得把 Edge Gateway 视为没有成本的无限量视频代理。

### 6.8 低延迟工程预算与监控

以 **30秒、2Mbps 总码率** 为例，源视频理论容量约7.5MB；2秒分段约15个、每段约0.5MB（不计额外封装与波动）。初始缓冲如果选0.7–0.9Mbps的480p清晰度，2秒片段约175–225KB，通常更适合作为首屏加载候选，但需要额外存储。此为理论估算，不代表实际网络成绩。

**性能链路**：`T_first_frame ≈ DNS/TLS + playlist + init + first segment transfer + decode`；若 playlist/初始化/首段跨三个不同节点，会增加连接与首帧不确定性。

| 指标 | 验收目标 | 获取方式 |
|---|---|---|
| 首帧时间 | P75 ≤ 2秒（目标） | 浏览器 Performance + player 首帧事件 |
| 已预热下一条切换 | P75 ≤ 0.5秒（目标） | 滑动触发到首帧 |
| 播放卡顿比例 | P95 用户 session ≤ 1% 卡顿时长（待可行性验证） | waiting/stalled 事件与播放时长 |
| 片段出错 | <0.5% GET 请求（初期目标） | 分段状态码、错误上报 |
| 源站切换 | 连续可用段不中断，临时故障尽量 <1秒切换（目标） | 主源 5xx / 超时故障注入 |
| CORS/Content-Type | 100%候选节点达标 | 自动化上传后 HEAD/GET 校验 |
| 免费额度 | 发布前余量充分且具备预算报警 | 月存储、A/B 请求与出站计数 |

播放器要记录：视频 ID、媒体版本、片段序号、逻辑供应商、HTTP 状态、TTFB、首字节与完整下载时间、失败重试、卡顿、首帧时间、当前网络状态。避免记录用户不必要的敏感身份或浏览历史。

**请求数不是可以忽略的成本**：若30秒视频为15段，再加清单/初始化共约17个 GET；每月完整播放1万次，理论产生约17万次对象读取（缓存命中则减少源请求）。Oracle 的5万 API 免费请求与 Tigris 的10万 Class B 免费请求都可能先于存储容量用完；R2 的1,000万 Class B 免费次数更适合高频短视频分段。数字是简化模型，未计额外画质、重试、页面预加载及 CDN 缓存。

### 6.9 V0.1 分块工作流（不依赖数据库）

```text
1) ffmpeg → 480p或720p HLS/fMP4 分段 + poster.webp
2) publish-cli → 计算每段 SHA256、时长、大小，生成 media-map
3) provider-probe → 验证业务/内容许可、HTTPS、MIME、CORS、请求/对象限制
4) placement-plan → 选择主源、连续分段组和必要副本
5) upload → 将片段上传 R2/B2 等已授权节点
6) verify → HEAD/GET + 校验哈希（上传端） + 首段 Range/跨域可播测试
7) manifest-build → 由 map 生成 master.m3u8 / index.m3u8
8) catalog-build → 将 video_id、封面、manifest 路径写入 videos.json
9) Git push → Pages 自动部署元数据和小型清单；视频块仍存放在外部节点
10) smoke-test → 手机 Safari/Chrome 连刷、断网、失效节点、下架测试
```

**发布顺序：** 上传完整、校验全部成功后才能把条目设置为 `published`。撤下时先把目录设为下架，再对存储与 CDN 进行访问撤销/清缓存，不能只从 Feed 移除链接。对于需要年龄限制的内容，所有播放清单和分段资源在公开前就必须走有效访问控制。

### 6.10 阶段依赖与上线门槛（DMS 专项）

| 阶段 | DMS 功能 | 独立验收 |
|---|---|---|
| **M0** | 10条合法测试视频分段，2个已许可来源验证直链、跨域及 iOS Safari | 至少 2 种存储适配器、首帧/跨域测试报告；若某服务不允许内容则不上传 |
| **V0.1** | 静态分块映射、离线清单生成、合规主节点 + 备用节点、可发布/撤下 | 没有 Supabase 仍可上线，至少30条可播，主源故障有可解释降级 |
| **V0.2** | Studio 管理分块上传、异步状态、供应商余量、元数据入库 | 无需改 React 源码发布视频，支持导出静态清单回退 |
| **V1.0** | 自动优选节点、更多清晰度、动态健康评分、Safari 完整备用清单/边缘路由 | 真实设备 P75、故障注入、成本监控通过 |
| **V1.1** | 论坛引用稳定 `video_id`，与分块存储完全解耦 | 论坛关闭/故障不影响播放，内容下架全站一致 |

### 6.11 官方依据与复核链接

- Apple HLS Authoring：https://developer.apple.com/documentation/http-live-streaming/hls-authoring-specification-for-apple-devices/
- Apple HLS Overview：https://developer.apple.com/documentation/http-live-streaming
- hls.js：https://github.com/video-dev/hls.js
- Cloudflare R2 Pricing：https://developers.cloudflare.com/r2/pricing/
- Cloudflare R2 Public Buckets：https://developers.cloudflare.com/r2/buckets/public-buckets/
- Cloudflare Pages Limits：https://developers.cloudflare.com/pages/platform/limits/
- Cloudflare Pages Range：https://developers.cloudflare.com/pages/configuration/serving-pages/
- Backblaze B2 Pricing：https://help.backblaze.com/hc/en-us/articles/217667478-Understanding-B2-Pricing-Structure
- Oracle Always Free：https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- GCS Pricing：https://cloud.google.com/storage/pricing
- Tigris Pricing：https://site.tigrisdata.com/pricing
- GitHub Releases：https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- GitHub LFS：https://docs.github.com/en/billing/concepts/product-billing/git-lfs
- GitHub Policies：https://docs.github.com/en/site-policy/acceptable-use-policies/github-sexually-obscene-content
- GitHub Packages：https://docs.github.com/en/billing/concepts/product-billing/github-packages
- GitLab Storage：https://docs.gitlab.com/user/storage_usage_quotas/
- HF Storage：https://huggingface.co/docs/hub/storage-limits
- HF Content Policy：https://huggingface.co/content-policy
- jsDelivr Terms：https://www.jsdelivr.com/terms
- Catbox FAQ：https://catbox.moe/faq.php
- Internet Archive：https://archive.org/
- IPFS：https://docs.ipfs.tech/concepts/what-is-ipfs/
- Cloudinary Pricing：https://cloudinary.com/pricing
- ImageKit Pricing：https://imagekit.io/plans/
- Gumlet Pricing：https://www.gumlet.com/pricing/
- Wistia Developer：https://wistia.com/pricing/developer-plan
- Vimeo Managed Storage：https://help.vimeo.com/hc/en-us/articles/51688797787281-About-managed-storage-on-Vimeo/
- Mux Pricing：https://www.mux.com/pricing
- Storj Pricing：https://www.storj.io/pricing/
- bunny Storage：https://bunny.net/pricing/storage/

---

## 7. 账号、权限与安全

### 7.1 分阶段角色

- V0.1：公众/经验证访客与仓库维护者。网站无普通业务账号，但适龄访问控制可能需要第三方验证或边缘短期会话。
- V0.2：增加 `admin`、`editor`，仅管理媒体。
- V1.1：增加 `member`、`moderator`，允许文字发帖与回复。

### 7.2 Supabase 安全基线

1. 对所有暴露的业务表启用 RLS，并正确设置 SQL GRANT；不要只添加 RLS Policy 而忘记默认权限。
2. 管理员权限来源于服务端可信表/受控 Claims，不能放在用户可自行修改的 metadata 中。
3. `service_role` / R2 Key 仅放在 Pages Functions/Worker 的环境 Secret，不进入浏览器。
4. Studio 的所有写操作必须在服务端再次校验权限，不把前端路由当访问控制。
5. 登录、发帖、评论、举报和外链导入增加速率限制、长度上限和审计。
6. 对 URL 进行白名单解析，不允许任意 URL 被服务器请求，避免 SSRF；第三方嵌入执行来源限制和 CSP。
7. 年龄验证结果与敏感身份信息最小化存储，制定保留与删除周期。
8. 使用备份恢复演练验证数据库和存储可迁移，而非仅相信服务商会自动备份。

### 7.3 成人社区治理流程

`REPORT_RECEIVED → TRIAGED → REMOVED/RETAINED → APPEALABLE → CLOSED`

明确紧急举报渠道；发现疑似未成年人性内容、非自愿私密影像或违法材料时立即限制传播并依法响应。管理员操作必须记录执行人、时间、原因和受影响对象。论坛开放前制定社区规则、服务条款、隐私政策与数据删除流程。

---

## 8. 管理后台与发布流程（V0.2）

**页面**：媒体列表、外链导入、上传视频、编辑详情、草稿队列、发布记录、分类标签、下架与举报处理。

### 8.1 管理员上传时序

1. 浏览器登录 Supabase Auth，获取用户会话。
2. 调用可信的 `POST /api/admin/uploads/authorize`；服务端验证管理员权限与允许 MIME/大小。
3. 服务端签发 **短期预签名 PUT URL**，浏览器直接上传 R2（不经过函数转发文件）。
4. 完成后调用 `POST /api/admin/uploads/complete`；服务端核验对象存在、大小、类型，必要时进行人工内容检查。
5. 写入 `media_assets` 和 `video_entries`，状态为 `DRAFT`。
6. 管理员预览并发布，记录 `publication_events`；发布对象变为可发现/可访问。

R2 预签名 URL 面向 S3 API 域名，不可直接当成自定义域名下的签名 URL；若要在自定义媒体域名实现受限访问，采用独立的边缘授权逻辑。

### 8.2 外链导入

管理员粘贴 URL → 校验域名/路径 → 提取合法外部 ID → 获取官方嵌入预览（在政策许可范围内） → 人工设置本站标题、分类、封面权限与来源说明 → 保存 → 发布。拒绝任意 iframe HTML 注入；外部服务可能删除视频或改变策略，因此必须能降级为“访问原站”。

---

## 9. 论坛设计（V1.1）

### 9.1 页面与最小功能

`/forum`（板块）→ `/forum/:slug`（主题列表）→ `/post/:id`（帖子与楼中楼）。支持注册、发帖、文本编辑、评论、点赞、举报、管理下架及仅引用已发布媒体 ID。

### 9.2 视频与论坛关系

- `media_assets` 是视频源信息；`video_entries` 是网站上的视频展示条目。
- `forum_posts.quoted_media_id` 可引用视频资产或展示条目 ID，需选定一种并全局一致；建议引用稳定 `video_entries.id`。
- 同一视频可被多个帖子引用，帖子有独立评论；视频主页可显示关联讨论入口。
- 论坛组件完全禁用时，不影响 `/`、`/video/:id`、`/explore`。

### 9.3 论坛第一阶段不引入的能力

无用户视频/图片上传、私信、复杂声望积分、付费群、直播、自动抓取外部媒体。若将来增加这些能力，单独评估内容治理、存储成本与隐私合规。

---

## 10. 免费托管、容量与费用模型

**以下是公开定价页截至 2026-11-05 的参考额度；服务商可更新规则，上线前应复核。**

| 服务 | 免费层 / 费用条件 | 适用阶段 | 主要风险 |
|---|---|---|---|
| Cloudflare Pages | 静态资源请求免费；免费计划构建配额 | V0.1+ | 构建限额；受平台条款约束 |
| Cloudflare Workers / Pages Functions | Free 计划约 100,000 请求/天（共享额度） | 按需 | 成人受限媒体每片段鉴权可能吃掉请求配额 |
| Cloudflare R2 Standard | 10GB-month、100万次 Class A、1000万次 Class B/月，出站不计 GB 费 | V0.1+ DMS | 计费资料、超额操作/存储、内容政策 |
| Supabase Free | 500MB 数据库、5GB egress、50,000 MAU 等 | V0.2+ | 一周低活动可暂停；无自动备份保障 |
| GitHub | **只用于源码、JSON 映射与小型清单** | 全阶段 | **色情/露骨视频与分块禁止作为上传内容；不能将 Releases/LFS 当 CDN** |
| 成人合规年龄保证供应商 | 通常需要单独报价或按量计费 | 若内容和法域要求 | 可能使基础月费无法维持 $0 |
| 自定义域名 | 按注册商实际价格 | 正式上线 | 可不是免费 |

**成本原则**：视频文件绝不经 Supabase 代理；视频流量由合法 CDN/媒体网关承担；管理员本地 FFmpeg 转码以节省转码服务器成本；对**每个**存储商分别跟踪容量、请求次数、出站流量及账单，不将各家免费额度简单相加后视为可持续容量；设置账单报警和消费上限（如有）。

容量估算（示例而非承诺）：每条视频约 8MB，10GB 约 1,250 条（未考虑封面、HLS 多版本、计费单位与其他文件）。即使存储费用接近零，年龄验证、治理和售后成本仍需预算。

---

## 11. 质量目标、测试与上线验收

### 11.1 非功能目标（待实测）

| 指标 | 建议验收目标 |
|---|---|
| 自有视频首帧时间 | 4G 模拟网络 P75 ≤ 2 秒（参考目标，非现有成绩） |
| 下一条已预热视频切换 | P75 ≤ 0.5 秒 |
| 同时播放的音源 | ≤ 1（任何离屏内容必须停止） |
| 视频流内存 | 连续滑动 50 条无持续失控增长 |
| 响应式布局 | 360、390、430px 手机、桌面无互动遮挡 |
| 浏览器 | iOS Safari、Android Chrome、桌面 Chrome/Safari/Firefox |
| 外部嵌入不可用 | 不阻断 Feed；可跳转原站或跳过 |
| 下架生效 | 主站不再推荐；CDN/受控媒体源按策略阻断 |

### 11.2 核心测试矩阵

1. **跨浏览器播放**：HLS/fMP4 分块、跨域绝对 URL、初始化片段、分段 MIME、HLS 原生 Safari、MP4 Range 降级、横/竖屏、静音自动播放、手动播放、暂停、屏幕锁定、后台切换。
2. **外链兼容**：公开视频、删除、私有、禁止嵌入、地域限制、年龄限制、第三方 Cookie 限制。
3. **移动交互**：快刷、慢刷、评论抽屉、滚动手势冲突、iOS 地址栏收缩、回退恢复位置。
4. **权限**：匿名读、普通用户不能管理视频、管理员可以下架、用户只能改自己帖子、RLS 拒绝访问。
5. **异常**：存储 404、CDN 超时、Supabase 暂停、上传中断、JSON 错误、数据库迁移失败。
6. **合规**：年龄限制绕过测试、受限视频链接绕过、举报响应、授权资料分级保存、内容删除后的缓存失效。
7. **回滚**：Pages 回滚、JSON 目录恢复、数据库迁移回滚脚本、媒体跨供应商备份恢复。

### 11.3 阶段发布门禁

- **M0 → V0.1**：Zyncat 移动适配可接受，**HLS 映射+两个合规节点跨域实测与 Safari 验证通过**，媒体托管与目标市场访问条件通过核验。
- **V0.1 上线**：30 条以上分块 HLS 可播放内容、JSON 映射完整、合法主源/备用源可用、无数据库依赖、合法访问、下架/报告可用。
- **V0.2 上线**：管理后台全流程、权限测试、JSON→DB 迁移与导出可恢复。
- **V1.0 上线**：性能监控、来源降级与关键错误处理通过，内容发现结果可解释。
- **V1.1 上线**：论坛 RBAC/RLS/举报/删除/封禁/限流及数据导出通过，论坛关闭视频仍可用。

---

## 12. 可执行开发任务与预估工作量

以下为熟悉 React/TypeScript 的单人开发者的粗略工程预算；不是完成承诺或严格工期。

| 任务包 | 工作内容 | 估算 |
|---|---|---|
| M0 | Zyncat 集成、响应式、HLS分块/跨节点播放验证、Safari/延迟测试、政策门槛 | 4–8 人日 |
| V0.1 | 静态内容目录与**分块映射、离线上传/清单编译、两类合规存储适配器、容灾**、导航/部署/举报 | 10–18 人日（合规实现另计） |
| V0.2 | Supabase、Studio、**分块直传与供应商余量管理**、官方外链适配、迁移和权限 | 10–20 人日 |
| V1.0 | 搜索、播放预热、数据指标、**跨节点性能/容错优化**、移动端优化 | 8–15 人日 |
| V1.1 | 论坛、回复、权限、举报、审核、文档与测试 | 10–20 人日 |
| V2.0 | 按真实数据决定，不预先承诺 | 待定 |

**建议优先 backlog**：

- `P0-001` 真实手机尺寸验证 Zyncat；同时验证两个合法供应商上的 HLS/fMP4 分块与 CORS、Safari 兼容；记录 ADR。
- `P0-002` 建立 `ContentRepository`、`MediaMap`、`StorageRegistry` 和 JSON Schema 校验（包括 ID 唯一、媒体片段连续、位置与合规状态）。
- `P0-003` HLS 原生播放器与单视频激活控制；处理跨节点加载、iframe 切换与错误。
- `P0-004` 确定合法内容、托管商和访问验证要求，严格禁止 GitHub/HF 等不合规节点进入成人媒体分块路径。
- `P0-005` 站点政策、举报入口、下架手册、备份与 CDN 访问测试。
- `P0-006` 部署 GitHub→Cloudflare Pages；上线 JSON分块映射与静态 HLS 清单；开展 V0.1 UAT。

---

## 13. 仓库建议结构

```text
velonexo/
├── src/
│   ├── app/                  # Router / provider / feature flags
│   ├── features/
│   │   ├── feed/             # V0.1
│   │   ├── player/           # V0.1 native + embeds
│   │   ├── discovery/        # V0.1
│   │   ├── studio/           # V0.2
│   │   ├── forum/            # V1.1
│   │   └── auth/             # V0.2 admin + V1.1 users
│   ├── domain/               # Stable media/content contracts
│   ├── services/
│   │   ├── content/          # JSON or Supabase adapter
│   │   ├── media/            # Storage and access resolver
│   │   └── telemetry/
│   ├── components/
│   └── styles/
├── public/catalog/videos.json
├── public/media-maps/      # V0.1: per-video segment/provider mapping
├── public/playlists/       # V0.1: compiled HLS VOD manifests
├── functions/               # V0.2 or age-gated media boundary
├── supabase/migrations/     # V0.2+
├── scripts/                 # FFmpeg / split / placement / verify / manifest build
├── docs/                    # ADR / runbooks / provider policy records
│   └── media-storage.md     # 供应商政策、位置、容量和故障演练
├── tests/                   # unit / browser / policy tests
└── package.json
```

**依赖规则**：`domain/` 不依赖 Supabase 和 React；`player/` 不直接读数据库；`forum/` 不直接操作媒体 Bucket；`studio/` 调用权限受控的发布服务；媒体 URL 的拼接只存在于 `media/` 服务。

---

## 14. 风险登记表与处理策略

| 风险 | 严重性 | 触发信号 | 预防 / 应对 |
|---|---|---|---|
| Zyncat 固定尺寸导致手机交互错位 | 高 | 360–430px 测试失败 | M0 限时验证；超阈值改响应式外壳 |
| 免费服务商拒绝成人内容 | 极高 | AUP 或人工核验不通过 | 先问清允许的内容类别；更换合法支持的商用方案，不依赖隐藏文件 |
| 年龄保证不充分 | 极高 | 目标法域不接受自我声明 | 发布前法律审查；有效验证 + 媒体层受控访问 |
| 受限视频文件通过直链绕过 | 极高 | 复制 URL 无需会话也能播放 | 私有存储+授权网关；全链路 Range/HLS 段校验 |
| Supabase Free 被暂停 | 中高 | 低活跃触发邮件 | V0.1 静态回退、导出目录；正式依赖时考虑付费 |
| 外部播放器政策变化 | 中 | YouTube/X/Instagram 嵌入失败率升高 | Provider Adapter、原站链接、可停用来源 |
| 视频缓存与播放请求激增 | 中 | R2/Worker 费用和请求峰值 | 监控、缓存策略、预加载限制、费用预警 |
| 论坛出现违规文字和骚扰 | 高 | 举报量增加 | 文字优先、速率限制、审核队列、封禁、记录保存 |
| 上游 UI / Player API 升级破坏 | 中 | 依赖更新后构建失败 | 锁版本、自动化冒烟测试、独立适配层 |
| 分块跨多个异构免费节点造成频繁卡顿 | 高 | P75 首帧或 stalled 增加 | 首片段同源+连续段组+主源镜像、分段实测 |
| 软件仓库被误当作成人视频 CDN | 极高 | 平台违规通知、封禁或删除 | GitHub/HF/npm 等默认排除成人媒体存储；合规节点才可加入 |
| 单个片段缺失导致整条视频无法播放 | 高 | 片段 404 / Hash 校验失败 | 发布前全量校验、关键分块副本、恢复/下架流程 |
| 单人运营缺少审核响应能力 | 高 | 投诉处理超时 | 明确服务等级、紧急暂停机制、最初仅管理员媒体 |

---

## 15. 上线运营手册（最小版）

### 15.1 每次发布前

- 核验来源、版权和必要同意/成年记录；检查内容政策、适用受众及地区。
- 转码成标准 HLS/fMP4 分块、计算哈希、映射合规存储节点，生成封面并手机预览；检查是否含不应公开的元数据。
- 逐块检查目标节点的政策资格、CORS、HTTPS/MIME、访问、哈希及跨域 HLS 播放，且媒体 URL 没有绕过访问策略。
- 发布后在真实手机逐条抽样播放，观察错误率、带宽和账单。

### 15.2 接到投诉/紧急下架时

1. 记录受影响视频/帖子 ID、举报类型、收到时间；优先限制公开传播。
2. 将内容标记 `REMOVED` 并立即从列表移除；如需阻断文件，撤销媒体访问并按需清理缓存。
3. 保存符合法律和隐私要求的最低限度审计记录；不再通过无保护 URL 扩散内容。
4. 按政策和法律要求通知相关人员、处理申诉、改进流程。

### 15.3 故障时

- JSON 目录失败：恢复上一个 Git 提交 / Pages 部署，同时确认分块映射与对应片段版本一致。
- Supabase 暂停：触发只读静态 Feed 回退或维护页；管理员操作暂停，不能假装写入成功。
- 媒体存储 5xx：显示封面与“暂不可用”，提供重试；勿重复无上限请求。
- 任意外部嵌入失效：跳过该视频并显示“查看来源”。
- 发现超额费用或严重违规：暂停上传/预加载/相关来源，按预案切换服务。

---

## 16. 发布前必须完成的决策清单

**GATE-A｜业务与法律**：运营主体、目标国家、内容尺度、是否真人、版权证明、同意/成年记录、地域和年龄限制、投诉渠道及数据保护义务。

**GATE-B｜托管政策**：站点托管、媒体存储、CDN、数据库、邮件/验证码供应商分别确认允许的业务类型。不能从“不会主动扫描”推断“任何内容都允许”。

**GATE-C｜技术**：Zyncat 手机适配、视频交互、HTTP Range、外链降级、访问控制、日志和成本上限。

**GATE-D｜运营**：至少一名责任人能在规定窗口内处理投诉/下架；有备份、恢复、供应商迁移和停站预案。

**未通过任一强制 Gate，不公开上线露骨内容。** 可先以内部分发或合法非露骨内容完成技术验证。

---

## 17. 参考资料（官方文档与源码）

以下链接为技术依据，**费用与政策应于实际发布日前复查**。

1. Zyncat TikTok 组件与 Props：https://ui.zyncat.app/tiktok
2. Zyncat 官方源码：https://github.com/zyncat/ui
3. Zyncat TikTok 源码：https://github.com/zyncat/ui/blob/main/src/components/expressive/tiktok/TikTok.tsx
4. Cloudflare Pages Functions 免费层：https://developers.cloudflare.com/pages/functions/pricing/
5. Cloudflare R2 费用：https://developers.cloudflare.com/r2/pricing/
6. Cloudflare R2 公共 Bucket / 自定义域名：https://developers.cloudflare.com/r2/buckets/public-buckets/
7. Cloudflare R2 Presigned URL：https://developers.cloudflare.com/r2/api/s3/presigned-urls/
8. Supabase 免费层与费用：https://supabase.com/docs/guides/platform/billing-on-supabase
9. Supabase Free 自动暂停：https://supabase.com/kb/faqs/platform/free-project-pausing
10. Supabase Row Level Security：https://supabase.com/docs/guides/database/postgres/row-level-security
11. YouTube IFrame Player API：https://developers.google.com/youtube/iframe_api_reference
12. YouTube 嵌入规则：https://developers.google.com/youtube/terms/required-minimum-functionality
13. X 官方嵌入说明：https://help.x.com/en/using-x/how-to-embed-a-post
14. TikTok Embed Player：https://developers.tiktok.com/docs/en/embed-player
15. bunny.net AUP（成人内容政策仅作可选供应商参考）：https://bunny.net/acceptable-use/
16. Backblaze B2 AUP：https://www.backblaze.com/company/policy/acceptable-use-policy

---

## 18. 最终建议与首轮执行边界

**启动阶段只交付 M0 + V0.1。** 不要求提前建设论坛、用户数据库、推荐系统、图片上传或复杂 HLS。先验证 Zyncat 是否能在真实手机上形成可用的 TikTok 体验，同时在**已确认内容许可的存储节点**之间完成 HLS 分块映射、预加载与故障降级；在合规访问和托管问题解决后，将带静态目录+分块清单的视频站作为第一个可独立运营版本。

**V0.1 完成即允许停止开发并长期运营。** V0.2 主要改善内容发布效率；V1.0 改善浏览体验；V1.1 才成为论坛社区。所有后续阶段均应向后兼容 `video_id` 和媒体访问接口，并保留独立关闭论坛的能力。

> **项目定义的底线**：便宜不等于可用，能播放不等于合规，开源 UI 不等于完整站点。真正减少维护成本的是“简单、清晰、可回退的边界”。
