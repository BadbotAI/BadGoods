# 一手来源与版本核对

把本表作为规则溯源和版本查询入口，不把它当作固定版本实现手册。仅打开当前问题需要的来源；优先读取项目内已安装版本、配置和官方文档，再对版本敏感行为进行在线核实。不要把历史 AI 质量研究或某个厂商产品承诺用作项目的缺陷率、严重性或验收阈值。

## 目录

- [先区分来源性质](#先区分来源性质)
- [执行版本核对](#执行版本核对)
- [规范与浏览器](#规范与浏览器)
- [无障碍与性能](#无障碍与性能)
- [框架、构建与测试](#框架构建与测试)
- [安全与数据权限](#安全与数据权限)
- [交付与运维](#交付与运维)
- [在报告中引用](#在报告中引用)

## 先区分来源性质

- 对正式规范，记录适用的版本、章节、成功准则或协议上下文；区分规范性要求与信息性示例。不要把某项浏览器规范直接说成该产品的全部验收要求。
- 对官方实践指南，把建议与项目约束对照；不要把推荐架构、工具或示例实现提升为唯一正确方案。
- 对框架／平台文档，先匹配实际版本、路由模式、运行环境和部署产品；不要把一种框架的行为推广到另一种框架。
- 对性能参考值，区分行业推荐、合同指标和当前项目预算；附测量设备、网络、构建方式、样本、分位数和时间。
- 对法规／合规结论，另核适用地区、合同和用户指定标准；不要从技术指南自行推出法律义务。
- 对来源冲突，优先核对版本、条件与原文；保留无法解决的差异，不为形成统一结论而删除限定条件。

## 执行版本核对

1. 读取 package.json、实际锁文件、packageManager 字段、Node／运行时配置、框架配置与 CI；优先使用已安装依赖的包元数据确认解析版本。
2. 同时记录声明范围和解析版本；不要把 ^ 或 ~ 范围当成实际安装版本，不为查版本而自动升级或联网安装 latest。
3. 区分 dev、build、preview、生产服务器与 SSR／Edge 运行时；读真实脚本链，确认 typecheck、lint、测试是否独立执行或由 build 包含。
4. 打开官方文档的对应 major／版本页面、迁移指南或 release notes；若只有滚动文档，记录查询日期和已确认适用于项目的条件。
5. 对浏览器行为记录目标浏览器、版本、操作系统、输入方式和必要真机结果；把模拟器、单一引擎结果和真实设备证据分开。
6. 对配置可由网关／托管平台补充的能力读取实际响应或部署配置；没有访问权限时标 blocked，不把源码缺失当作部署能力缺失。
7. 对具体漏洞，查询维护者公告及受影响／修复范围，再检查项目可达路径；不要仅凭扫描器级别确定实际风险。
8. 对结论记录来源标题、URL、适用版本／章节、访问日期和项目证据；持久文件使用稳定 URL，不保存仅当前会话有效的搜索引用编号。

## 规范与浏览器

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| HTML | [WHATWG HTML Living Standard](https://html.spec.whatwg.org/multipage/) | 浏览器平台规范。核对原生语义、表单、导航、iframe 和消息机制；按目标浏览器验证实现，勿把语义正确等同于完整可用性。 |
| FETCH | [WHATWG Fetch Standard](https://fetch.spec.whatwg.org/) | 网络与跨源协议规范。核对 credentials、请求、响应、重定向和 CORS；区分请求发出、服务器执行与响应可读。 |
| RFC9110 | [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) | HTTP 语义标准。按第 9.2.2 节等对应内容核对幂等与重试；不要把方法名称直接当成业务幂等证据。 |
| RFC9111 | [RFC 9111 — HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) | HTTP 缓存标准。核对响应可缓存性、认证、指令与验证器；不要把 HTTP 缓存规则直接套到应用自己管理的缓存。 |
| MDN-CACHE | [MDN — Cache](https://developer.mozilla.org/en-US/docs/Web/API/Cache) | Web API 实现说明。核对 Cache API 的应用管理责任、兼容性和限制；特别区分 HTTP 缓存头与 Cache API 条目管理。 |

## 无障碍与性能

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| WCAG22 | [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) | W3C Recommendation。按用户指定等级和适用成功准则审查；区分标准符合性与法律适用性，不声称一次扫描证明全部符合。 |
| ARIA-APG | [W3C WAI — ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/) | 官方实践指南。参考 dialog、tabs、menu、combobox 等模式的语义与键盘行为；示例不是覆盖全部场景的强制实现。 |
| VITALS | [web.dev — Web Vitals](https://web.dev/articles/vitals) | Google 官方指标与体验建议。使用时复核当期指标、推荐阈值和测量口径；区分实验室观察与真实用户分位数，不把单次 Lighthouse 分数当线上表现。 |

需要默认性能参照时，查当期 Web Vitals 文档。若采用 LCP、INP、CLS 推荐范围，明确它们是体验目标，记录移动／桌面样本与第 75 百分位口径；没有真实样本时不要声称达到现场指标。

## 框架、构建与测试

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| REACT-BOUNDARY | [React — Component / Error Boundary](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary) | React 实现文档。核对渲染异常、生产上报和捕获范围；按版本核查事件、异步、SSR、自身错误及 transition 例外。 |
| TS-BASICS | [TypeScript — The Basics](https://www.typescriptlang.org/docs/handbook/2/basic-types.html) | 语言工具文档。核对静态检查、输出与类型擦除；不要把类型标注当成运行时 API 数据校验。 |
| VITE-FEAT | [Vite — Features / TypeScript](https://vite.dev/guide/features#typescript) | 构建器文档。区分 TypeScript 转译与完整类型检查；先查看项目 build 脚本是否另行执行 tsc 或其他 checker。 |
| VITE-ENV | [Vite — Env Variables and Modes](https://vite.dev/guide/env-and-mode) | 配置与模式文档。核对暴露前缀、构建时替换和环境优先级；不能以 .env 文件存在就认定秘密未进入客户端。 |
| VITE-BUILD | [Vite — Building for Production](https://vite.dev/guide/build) | 生产构建文档。核对目标浏览器、资源 base、懒加载与构建选项；默认值随 major 变化，使用时匹配项目版本。 |
| PLAYWRIGHT-BP | [Playwright — Best Practices](https://playwright.dev/docs/best-practices) | 官方测试实践。参考用户可见行为、隔离、断言等待、trace 与浏览器矩阵；不要把已测用例的成功泛化为未测路径正确。 |
| PLAYWRIGHT-A11Y | [Playwright — Accessibility Testing](https://playwright.dev/docs/accessibility-testing) | 官方测试范围说明。核对自动检查覆盖、状态扫描和人工评估要求；区分 WCAG 规则与工具额外 best-practice 规则。 |

遇到 Vue、Angular、Next.js、Svelte、组件库、路由器或数据请求库时，补查其官方对应版本文档。不要为了统一输出将项目迁移到本表列举的工具，也不要从 Vite 的行为推断所有框架的 build 均不做类型检查。

## 安全与数据权限

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| OWASP-FE | [OWASP — Web Frontend Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Web_Frontend_Security_Cheat_Sheet.html) | 安全实践指南，旧名 AJAX Security。核对客户端信任边界、秘密、文本与 HTML 渲染；不将缺少示例库视为必然漏洞。 |
| OWASP-AUTH | [OWASP — Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 授权实践指南。核对每请求、对象、字段、静态资源和默认拒绝；把检查落实到可信服务层，不以 UI guard 替代。 |
| OWASP-HTML5 | [OWASP — HTML5 Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html) | 浏览器安全实践指南。核对 Web Storage、消息来源、跨域、嵌入与离线存储；需要浏览器细节时继续查其链接的规范或实现文档。 |
| OWASP-CSRF | [OWASP — CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) | 按架构选择防护的指南。核对身份携带、服务器校验和等效机制；禁止以无 token 判定必然可利用。 |
| OWASP-LOG | [OWASP — Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | 日志与隐私实践指南。核对事件关联、敏感数据排除、日志失败、访问和告警；不把前端埋点等同于可信业务审计。 |
| SUPABASE-RLS | [Supabase — Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) | 产品与数据库授权文档。核对 grants、policy、角色、操作、视图／函数及测试；公开 anon／publishable key 与服务端私密 key 分开判断。 |

需要 XSS、CSP、上传、会话、OAuth 或供应链细节时，从相关 OWASP 条目进入其对应专题与项目采用框架的官方防护文档。先建立适用威胁与执行路径，再引用建议；不要凭关键词搜索命中给出漏洞结论。

## 交付与运维

| 标识 | 一手来源 | 性质与使用边界 |
|---|---|---|
| NPM-CI | [npm — npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/) | 包管理器版本文档。核对锁文件一致性与干净安装；链接固定 v11，项目使用其他版本时切换对应版本，不机械照抄选项。 |
| GHA-SECURE | [GitHub Actions — Secure Use Reference](https://docs.github.com/en/actions/reference/security/secure-use) | 平台安全实践。核对最小权限、第三方 action 引用、不可信输入与 secrets；平台默认值和功能变化需使用时复核。 |
| VERCEL-ROLLBACK | [Vercel — Instant Rollback](https://vercel.com/docs/instant-rollback) | 托管平台实现文档。用于核查部署与配置恢复边界，不证明数据库、外部 API 和旧客户端天然兼容；其他平台查其自身文档。 |

接入 Sentry 或其他监控／回放 SDK 时，查实际版本的事件捕获、默认采集、脱敏、source map 和 release 文档，并用合成标记验证；不要根据产品名称臆测默认设置。

## 在报告中引用

- 给硬性不符合项列出适用规范和具体条款；给建议项说明参考依据、收益和适用条件。
- 把外部规则与项目观察证据分别写明；来源只能证明规则存在，不能替代项目已复现证据。
- 对诊断给出文件／配置／脱敏运行证据，再给原始文档 URL；需要截图或测量时记录采样条件。
- 对版本差异写出“项目版本 + 文档版本 + 已验证行为”；无法匹配时降低确定性并列出下一步。
- 不将工具营销、媒体转述、历史生成代码漏洞比例或其他项目事故作为本项目通过／失败依据。
- 在每次有必要更新规则时修改具体条目；不要为一次审查无差别抓取所有来源或生成大批无关引用。
