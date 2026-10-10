# 前端审查助手

版本：0.3.0-beta · 2026-10-10

一个面向 Vibe Coding 和原型前端的工程审查 Skill，逐页、逐状态、逐组件梳理问题，输出有证据、可追踪的修复与重构方案。

## 适合什么任务

- 快速体检：优先找核心流程的问题，产出一份简短报告。
- 完整审查：逐页逐组件建立证据台账、问题清单、重构方案和验收条件。
- 按明确授权修复：小批实施、复验并记录仍未解决的限制。

没有指定深度时默认快速体检；明确要求全站或完整审查时使用完整流程。截图只能支持所展示的视觉状态，源码审查不能证明交互已运行成功。

## 使用入口

源码目录名为 `review-frontend-production`，Skill ID 保持不变；专用上传 ZIP 将 SKILL.md 放在压缩包根目录。将整个目录交给支持本地 Skill 的宿主，按宿主的技能安装入口添加；也可让代理读取该目录的 SKILL.md。不同宿主的安装与工具能力可能不同，本包不保证所有平台都支持相同能力。

示例请求：

1. 使用 $review-frontend-production 快速体检这个前端项目，优先检查注册、登录和提交失败恢复，先输出主要问题，不修改源码。
2. 使用 $review-frontend-production 完整审查这个项目，逐页逐组件建立台账，输出修复计划和未验证范围。
3. 使用 $review-frontend-production 修复这份审查报告中已确认的 P1 问题，并复验受影响流程；保留现有设计。

附上项目路径或网址，以及已知的核心任务即可；有测试账号、设备范围和设计标准时一并提供。

## 环境与产物

两个辅助脚本只依赖 Python 3 标准库，建议 Python 3.9 或更高版本；已验证版本见 VALIDATION.md。rg 可选，缺少时发现脚本回退到目录遍历。实际页面检查需宿主具备浏览器或测试工具；项目构建工具沿用项目自身配置，不会随本包安装。

- quick：quick-review.md，以及必要证据。
- full：review.md、audit.json、coverage.md、页面报告、组件方案及任务计划。
- 示例：examples/source-only/，包含虚构输入、实际静态检查、台账、报告和复跑方法。

完整审查可能产生较多记录，规模取决于页面、组件契约和场景差异。台账校验只检查声明的结构与关联，不能认证证据真实性或保证没有漏洞。

## 验证脚本

在本技能目录运行：

```sh
python3 -B -m unittest discover -s tests -v
python3 -B examples/source-only/verify_fixture.py
python3 -B scripts/audit_ledger.py check examples/source-only/audit.json --require-plan
```

最后一条应返回 0；示例使用源码访问，--require-complete 和 --require-ready 应返回 2，表示未满足完整验证/发布条件。

## 分享与隐私

分享包应排除 .DS_Store、__pycache__、.pyc、系统扩展属性、真实项目证据与账号信息。脚本输出可能包含项目绝对路径、包名、路由和源码位置；分享运行结果前另做脱敏。本包的示例不包含真实业务数据。

发布状态为试用版，未完成多个真实框架项目的端到端兼容性评测。版本变化见 CHANGELOG.md；使用许可状态见 LICENSE-NOTICE.md。

## 分发与能力边界

小红书专用上传包省略宿主专有 agents/openai.yaml 与 SVG 图标，保留 Markdown、Python、JSON、HTML、TXT 文件。完整源码目录保留这些可选元数据。这个打包选择依据用户提供的格式清单，并非平台已验收证明。

输入可以是源码、网址或截图；脚本和浏览器均为可选宿主能力。只有截图时仅作视觉检查，没有 Python 时人工整理台账并明确未执行机械校验。无文件写入能力时在对话中交付，不伪造下载链接。
