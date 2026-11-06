# VeloNexo｜成人视频与兴趣社区 产品与技术设计文档

> **文档版本**：v1.0（方案基线）  
> **编制日期**：2026-11-05  
> **项目代号**：`velonexo`（工作名称，未完成域名与商标核验）  
> **总体路线**：视频优先、论坛后置；每个阶段独立可上线、可运营、可回退  
> **架构约束**：TikTok 风格；Zyncat UI；尽可能免费；不维护常驻服务器；视频存储/CDN 与站点分离；管理员管理视频；未来支持成人论坛。

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
| ADR-07 | 自有视频先用压缩 MP4 + HTTP Range，HLS 延后按证据启用 | 降低上传、转码、对象数与浏览器兼容成本 |
| ADR-08 | 外部视频只用允许的官方 Embed；不抓取原始流 | 降低版权、平台政策和转码风险 |
| ADR-09 | V1.1 才开放普通用户账号、文字发帖、评论 | 降低初期社区治理负担 |
| ADR-10 | 成人内容的合法性、服务条款及适龄访问为首版上线门槛 | 技术可播放不代表可以合法公开运营 |

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
| **M0 技术验证** | 内部演示，不公开 | Zyncat 适配、播放器、滑动、内容策略核查 | 本地 React | 否，属于发布门槛 |
| **V0.1 视频站** | 可长期使用的视频展示站 | 自有 MP4、基础外链、分类、详情页、举报/下架 | Cloudflare Pages + 合规视频存储/CDN | **是** |
| **V0.2 内容后台** | 可独立运营的视频 CMS 站 | 管理员登录、Web 发布、自有上传、多平台导入、发布状态 | + Supabase + Serverless Functions | **是** |
| **V1.0 视频体验** | 完整短视频发现产品 | 稳定预加载、搜索、热门/专题、错误降级、指标 | 沿用 V0.2 | **是** |
| **V1.1 论坛社区** | 视频 + 成人兴趣论坛 | 普通用户账号、板块、文字帖子、回复、举报审核 | 沿用 Supabase | **是** |
| **V2.0 增强（可选）** | 轻社交社区 | 收藏、关注、通知、可解释推荐、站内专题 | 视实际需求 | **是** |

**独立上线原则**：每阶段必须包括当期必需的法律/安全控制、备份、故障降级、部署手册和独立验收。后续功能必须通过开关与接口增量接入，不得要求前一阶段迁移后才能继续使用。

### 2.1 M0｜技术与合规可行性门槛

**实现范围**：安装 Zyncat TikTok 组件，嵌入原生 MP4、YouTube 测试视频；用 CSS Scroll Snap 或 Embla 验证竖向滑动；对 360/390/430px 手机宽度与桌面进行真实设备测试；确认托管商可接受目标内容类型。

**退出标准**：① 当前视频独占播放；② 不裁切互动按钮；③ 不被 iframe 长期拦截滑动；④ 页面离开时停止音频；⑤ 有确定的内容政策和适龄访问方案；⑥ 合法托管商已确认。若 Zyncat 固定布局改造超过预定范围，改为“保留视觉设计、使用轻量响应式卡片”，不反复叠加缩放补丁。

### 2.2 V0.1｜独立视频站（首个公开版本）

**必须提供**：

1. TikTok 风格全屏视频流；上下滑动、暂停、默认静音、封面占位、加载失败处理。
2. 至少一种合规自有视频播放路径（首选 MP4 + Range）；外链优先支持 YouTube，其它来源可以显示原站链接，不阻塞上线。
3. 分类、标签、最新排序、静态基础搜索、独立视频分享地址 `/video/:id`。
4. **纯静态内容目录** `public/catalog/videos.json`；管理员通过 Git 更新数据、自动部署。
5. 管理员可随时撤下视频：更改目录状态、重新构建、必要时撤销媒体源访问并清理 CDN 缓存。
6. 投诉/侵权/隐私举报入口、联系渠道、版权和隐私声明；按目标市场采用实际有效的适龄访问措施。
7. 基础日志、容量监控、源文件备份和站点回滚说明。

**不需要**：Supabase、用户账户、点赞持久化、评论、论坛、内容推荐算法。

**单独上线标准**：30 条以上混合测试视频连续滑动；公开 URL 可访问；合法区域、权限、浏览器、暂停和下架流程通过；无需开发环境或运行时数据库即可持续运营。

### 2.3 V0.2｜内容管理与多来源聚合

**新增**：Supabase Auth 管理员、Postgres 视频目录、Studio 管理台、视频导入/编辑/发布状态机、R2 直传与校验、来源 URL 识别、YouTube/X/Instagram/TikTok 官方 Embed、内容批量下架。

**迁移**：保留 V0.1 原有 `id`；编写一次性 JSON→Postgres 导入脚本；保留 JSON 导出/只读回退，以免数据库故障导致视频目录全部不可用。

**独立上线标准**：非开发人员可在浏览器完成“添加→预览→发布→下架”；无 React 源码更改；匿名用户不能写表；服务端强制管理员权限；外链失效不阻断视频流。

### 2.4 V1.0｜完整视频体验

**新增**：虚拟化视频窗口、下一条适量预热、外部 iframe 懒加载、完善分类/标签搜索、热门/最新/精选、播放监控和错误分析、移动端专项优化；依据 A/B 结果决定是否提供 HLS 多清晰度。

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
  ├─ Native Player: MP4; optional HLS via Video.js
  ├─ Forum (V1.1)
  └─ Studio (V0.2)
       │
       ├── Cloudflare Pages (static UI / versioned deployment)
       ├── Supabase (V0.2+: Auth, Postgres, RLS, content APIs)
       ├── Pages Functions / Workers (admin auth, upload URL, publish, optional age gate)
       └── Media delivery (never proxied through Supabase)
             ├── R2 / eligible object storage (binary files)
             └── CDN or protected media gateway (policy-dependent)
```

### 3.1 核心边界

- **ContentRepository**：`listVideos(cursor, filter)`、`getVideo(id)`；V0.1 读取静态 JSON，V0.2 后切到 Supabase。业务组件不关心存储格式。
- **MediaResolver**：从 `provider + object_key` 解析播放地址；禁止数据库存储难迁移的永久 CDN 完整 URL。
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

### 5.1 V0.1 静态 JSON（简化示例）

```json
{
  "schema_version": 1,
  "videos": [
    {
      "id": "vid_0001",
      "title": "Example title",
      "description": "Editorial description",
      "source": {"kind": "native", "format": "mp4", "provider": "r2", "object_key": "media/vid_0001/video.mp4"},
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

**注意**：示例 JSON 的媒体键不等于公开可访问的 URL。`age_restricted` 内容如果需要真实访问限制，`MediaResolver` 必须走受保护的媒体网关，并在媒体请求层验证访问资格。不得把完整直链藏在前端 JSON 里却保持 Bucket 公开。

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

## 6. 自有视频、文件分段与 CDN

### 6.1 第一版视频格式

- 默认：720p 或源比例等比缩放、H.264 + AAC、`MP4`、`+faststart`；按真实设备和成本测试调整参数。
- 浏览器直接访问合规的 CDN/媒体网关，检查 `Content-Type: video/mp4`、Range/206、缓存与 CORS。
- 对横屏视频不强制拉伸为 9:16；可选择黑边、模糊背景或运营裁剪版本。
- 原始视频、授权文件、发布用 MP4、封面分开保存；授权材料不要放在公开 Bucket。

**参考 FFmpeg 命令**（仅作为处理样例，不保证对所有输入都可用）：

```bash
ffmpeg -i input.mp4 \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease:force_divisible_by=2" \
  -c:v libx264 -preset medium -crf 25 -pix_fmt yuv420p \
  -c:a aac -b:a 96k -movflags +faststart output.mp4
```

### 6.2 HLS 的触发条件

HLS 仅在 MP4 的首帧、跳转、弱网或多清晰度测试证明存在收益时增加。HLS 用 `index.m3u8 + init.mp4 + *.m4s` 标准分段，不在数据库逐块保存映射；播放器按清单请求分段。所有分段、初始化文件与清单必须遵循相同访问控制；分段多可能增加请求开销。

**不采用**任意二进制乱序切块 + JS 拼接作为首版播放协议。该方案引入不可预测的延迟和维护成本，也不能提供可靠的内容保密或审核规避能力。

### 6.3 存储路径与可迁移性

```text
media/
  vid_0001/
    master-original.mp4   # 私有备份；不对外公开
    poster.webp
    v1/video.mp4
  vid_0002/
    poster.webp
    v1/hls/index.m3u8
    v1/hls/init.mp4
    v1/hls/seg_0000.m4s
```

`MediaResolver` 负责 `provider + object_key -> 可访问地址`；更换 CDN 不修改帖子 ID。正式使用 R2 自定义域名，不使用 `r2.dev` 作为生产播放地址。

### 6.4 成人受限媒体的访问决策

| 内容类别 | 推荐方式 | 关键前置条件 |
|---|---|---|
| 合法且不要求额外年龄限制的普通宣传/教育媒体 | 可采用公开 CDN URL | 明确版权、平台条款与目标法域 |
| 依法需要年龄保证的露骨内容 | 私有 Bucket + 边缘授权网关 + 合格的年龄保证流程 | 无法靠前端弹窗解决；需适用法律评估 |
| 尚未取得授权/待审核视频 | 私有存储，管理员专用预览 | 严禁公开直链 |

受限媒体网关的实现重点：校验有效年龄保证凭据或会话、限制访问地域（如法律要求）、支持 `GET/HEAD/Range`、不暴露原始 Bucket、授权到期、日志最小化、阻断缓存绕过。对 HLS 还需覆盖清单和**每一个分段**。免费 Workers 配额、认证服务费用和缓存方式可能使“零月费”目标无法成立，应先核算。

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
| Cloudflare R2 Standard | 10GB-month、100万次 Class A、1000万次 Class B/月，出站不计 GB 费 | V0.1+ | 计费资料、超额操作/存储、内容政策 |
| Supabase Free | 500MB 数据库、5GB egress、50,000 MAU 等 | V0.2+ | 一周低活动可暂停；无自动备份保障 |
| GitHub | 源码和静态 JSON | 全阶段 | 不能把 Releases/LFS 当作不限量视频 CDN |
| 成人合规年龄保证供应商 | 通常需要单独报价或按量计费 | 若内容和法域要求 | 可能使基础月费无法维持 $0 |
| 自定义域名 | 按注册商实际价格 | 正式上线 | 可不是免费 |

**成本原则**：视频文件绝不经 Supabase 代理；视频流量由合法 CDN/媒体网关承担；管理员本地 FFmpeg 转码以节省转码服务器成本；对存储用量、请求次数设置账单报警和消费上限（如有）。

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

1. **跨浏览器播放**：MP4 Range、横/竖屏、静音自动播放、手动播放、暂停、屏幕锁定、后台切换。
2. **外链兼容**：公开视频、删除、私有、禁止嵌入、地域限制、年龄限制、第三方 Cookie 限制。
3. **移动交互**：快刷、慢刷、评论抽屉、滚动手势冲突、iOS 地址栏收缩、回退恢复位置。
4. **权限**：匿名读、普通用户不能管理视频、管理员可以下架、用户只能改自己帖子、RLS 拒绝访问。
5. **异常**：存储 404、CDN 超时、Supabase 暂停、上传中断、JSON 错误、数据库迁移失败。
6. **合规**：年龄限制绕过测试、受限视频链接绕过、举报响应、授权资料分级保存、内容删除后的缓存失效。
7. **回滚**：Pages 回滚、JSON 目录恢复、数据库迁移回滚脚本、媒体跨供应商备份恢复。

### 11.3 阶段发布门禁

- **M0 → V0.1**：Zyncat 移动适配可接受，媒体托管与目标市场访问条件通过核验。
- **V0.1 上线**：30 条以上可播放内容、无后端依赖、合法访问、下架/报告可用。
- **V0.2 上线**：管理后台全流程、权限测试、JSON→DB 迁移与导出可恢复。
- **V1.0 上线**：性能监控、来源降级与关键错误处理通过，内容发现结果可解释。
- **V1.1 上线**：论坛 RBAC/RLS/举报/删除/封禁/限流及数据导出通过，论坛关闭视频仍可用。

---

## 12. 可执行开发任务与预估工作量

以下为熟悉 React/TypeScript 的单人开发者的粗略工程预算；不是完成承诺或严格工期。

| 任务包 | 工作内容 | 估算 |
|---|---|---|
| M0 | Zyncat 集成、响应式、原生与 YouTube 播放、政策门槛梳理 | 2–5 人日 |
| V0.1 | 静态内容目录、导航、详情、分类、部署、受限访问与举报 | 6–12 人日（合规实现另计） |
| V0.2 | Supabase、Studio、R2 直传、官方外链适配、迁移和权限 | 8–16 人日 |
| V1.0 | 搜索、播放预热、数据指标、错误恢复、移动端优化 | 6–12 人日 |
| V1.1 | 论坛、回复、权限、举报、审核、文档与测试 | 10–20 人日 |
| V2.0 | 按真实数据决定，不预先承诺 | 待定 |

**建议优先 backlog**：

- `P0-001` 真实手机尺寸验证 Zyncat；记录选择继续/改响应式外壳的 ADR。
- `P0-002` 建立 `ContentRepository` 和 JSON Schema 校验（包括 ID 唯一、状态、日期、合法来源）。
- `P0-003` 原生播放器与单视频激活控制；处理 iframe 切换与错误。
- `P0-004` 确定合法内容、托管商和访问验证要求，构建必要的限制路径。
- `P0-005` 站点政策、举报入口、下架手册、备份与 CDN 访问测试。
- `P0-006` 部署 GitHub→Cloudflare Pages，开展 V0.1 UAT。

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
├── functions/               # V0.2 or age-gated media boundary
├── supabase/migrations/     # V0.2+
├── scripts/                 # FFmpeg / catalog validation / migration
├── docs/                    # ADR / runbooks / provider policy records
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
| 单人运营缺少审核响应能力 | 高 | 投诉处理超时 | 明确服务等级、紧急暂停机制、最初仅管理员媒体 |

---

## 15. 上线运营手册（最小版）

### 15.1 每次发布前

- 核验来源、版权和必要同意/成年记录；检查内容政策、适用受众及地区。
- 压缩视频、生成封面、手机预览，检查是否含不应公开的元数据。
- 确认 CDN/受控网关地址正常、Range/HTTPS/MIME 正确，且媒体 URL 没有绕过访问策略。
- 发布后在真实手机逐条抽样播放，观察错误率、带宽和账单。

### 15.2 接到投诉/紧急下架时

1. 记录受影响视频/帖子 ID、举报类型、收到时间；优先限制公开传播。
2. 将内容标记 `REMOVED` 并立即从列表移除；如需阻断文件，撤销媒体访问并按需清理缓存。
3. 保存符合法律和隐私要求的最低限度审计记录；不再通过无保护 URL 扩散内容。
4. 按政策和法律要求通知相关人员、处理申诉、改进流程。

### 15.3 故障时

- JSON 目录失败：恢复上一个 Git 提交 / Pages 部署。
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

**启动阶段只交付 M0 + V0.1。** 不要求提前建设论坛、用户数据库、推荐系统、图片上传或复杂 HLS。先验证 Zyncat 是否能在真实手机上形成可用的 TikTok 体验；在合规访问和托管问题解决后，将带静态目录的视频站作为第一个可独立运营版本。

**V0.1 完成即允许停止开发并长期运营。** V0.2 主要改善内容发布效率；V1.0 改善浏览体验；V1.1 才成为论坛社区。所有后续阶段均应向后兼容 `video_id` 和媒体访问接口，并保留独立关闭论坛的能力。

> **项目定义的底线**：便宜不等于可用，能播放不等于合规，开源 UI 不等于完整站点。真正减少维护成本的是“简单、清晰、可回退的边界”。
