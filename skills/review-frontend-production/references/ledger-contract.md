# 审查台账与覆盖协议

## 目录

1. 实体与覆盖单位
2. JSON 数据约定
3. 检查状态与证据
4. 问题、蓝图与重构任务
5. 完整性与发布门槛
6. 分批执行与续接

## 1. 实体与覆盖单位

把 audit.json 作为机器可检查的事实台账，Markdown 作为面向人的解释。不要维护互相矛盾的两套结论。增量更新台账后重生成索引，并编写专题分析。

使用稳定标识：

| 实体 | ID | 覆盖含义 |
|---|---|---|
| 项目 | PRJ-001 | 本次约定的目标、访问能力与基线 |
| 页面 | PAGE-001 | 路由模板、独立页面/子应用、具有独立任务的虚拟页面 |
| 组件定义 | DEF-001 | 一个实际实现；同名但实现不同应拆分 |
| 组件实例 | CMP-001 | 某一页面中具有独立位置、props、上下文的逻辑 UI 单元 |
| 场景 | SCN-001 | 明确身份、数据、环境和事件顺序的验证 |
| 检查 | CHK-001 | 某个目标在一个维度下的可回答问题 |
| 证据 | EV-001 | 实际读取/执行/观察的定位记录 |
| 问题 | FND-001 | 具有实际/预期差异、影响、证据与归因的发现 |
| 组件蓝图 | BP-001 | 一份当前与目标组件契约；允许多个实例复用 |
| 任务 | TASK-001 | 可单独实施、验证、恢复的变更或补证动作 |
| 门槛 | GATE-001 | 与产品目标相匹配的发布前条件 |

不要把所有 DOM 包装节点都假装成独立产品组件。登记每个有独立语义、交互、状态、布局或数据责任的单元，包括页壳、布局区域、文本信息、图标、按钮、菜单项、错误消息和条件出现的内容。纯装饰/包装节点纳入最近负责组件的 layout_content 检查，并在实例备注中交代归属。

对重复数据行，登记模板及所有不同 props/权限/状态/布局契约的实例类别，记录等价分组依据和代表数据。不要为无限记录建立无限页面，也不要以“都是同一个组件”为由跳过不同使用上下文。新增页、组件分支或参数类别时扩大分母，保留稳定 ID。

## 2. JSON 数据约定

使用 UTF-8、schema_version "1.0"。所有列表字段即使暂为空也保留。扩展字段允许；校验器检查下列契约，不检查真实世界是否确实如此。

所有规定的 reason 字段均保留字符串；不要求理由的状态可填空串，要求理由时必须是非空说明，不能用 null、数组或对象代替。引用 ID 的数组和普通说明数组只包含非空字符串。

### project

填写：

- id、name、target：实际项目标识和路径/网址；未提供时使用明确的待补说明。
- mode：audit_plan 或 implement，按用户授权选择。
- review_depth：quick 或 full；旧台账省略时按 full。quick 不要求台账，也不能获得完整覆盖、完整方案或发布就绪结论。
- access_mode：source_runtime、source_only、runtime_only、screenshots_only。
- baseline：记录 source_ref、runtime_ref、observed_at；不能伪造提交号或运行版本。审查者须核对 EV.baseline_ref 与源码、构建、运行环境及历史复验版本的对应关系；字符串相同不能证明基线一致，不同字符串也可能指向同一构建，脚本不认证这种真实对应关系。
- inventory_status：discovering、reconciled、limited。reconciled 只用于已核对可用发现渠道并解决差异。
- inventory_sources：对象数组，每项含非空字符串 kind、locator 及 evidence_ids 数组；记录路由代码、运行导航、配置/设计文档等。各发现阶段都须满足此结构；reconciled 时每项 evidence_ids 非空。
- scope：自然语言写明本次边界。
- out_of_scope：对象数组，每项必填非空字符串 surface、reason、authority；不要默默缩小用户要求。
- production_profile：记录用户、关键任务、支持环境、身份/租户、数据风险、规模、性能目标、发布机制、必须满足的标准；未知值明示 unknown。
- assumptions：尚未确认的假设说明数组，每项为非空字符串。

### pages

每项必填 id、route、title、source_locator、entry_conditions、variants、evidence_ids、scope_status。

- scope_status 为 in_scope 或 excluded；排除时填 exclusion_reason 和 exclusion_authority。
- 将详情不存在/无权限/删除后访问、功能开关、登录落点等登记在 variants 或独立页面中，并建立 SCN。
- 把无源码条件记为 source_locator "unavailable: 原因"，不要发明文件。

### definitions

每项必填 id、name、kind、source_locator、source_status。

- source_status：located、unavailable、inferred。
- 使用 unavailable/inferred 时，不得把推测当静态审查通过。

### instances

每项必填 id、page_id、definition_id、label、locator、variant、criticality。

- 可附 parent_instance_id、data_source、equivalence_group、notes。
- parent_instance_id 非空时引用同页已有 CMP；不得指向自身或形成任何间接祖先环，实例结构须能组成树。
- locator 同时提供可观察定位和可得的源码定位；不能只写“页面按钮”。
- criticality 为 high 或 normal；高风险写操作、身份、导航主入口、核心输入等按业务认定。
- 同一页面的顶部与底部两个保存按钮建立两个 CMP，底层 DEF 可以共享。

### scenarios

每项必填 id、title、page_ids、instance_ids、preconditions、steps、expected、context、risk、status、evidence_ids、finding_ids、reason。

- context 必须含 role、data、network、viewport、input、lifecycle 六项；每项为非空字符串或非空字符串数组。明确具体条件；不适用项写原因，不能仅填 N/A 或“不适用”。
- risk：high 或 normal。
- status：planned、passed、failed、blocked、not_applicable。
- steps 和 expected 必须是非空字符串数组，避免“测试一下是否正常”。
- passed/failed 均须关联实际 runtime 或 test EV；failed 还必须关联已确认问题。源码可确认的缺陷用 failed CHK 表达，未执行的场景不能因此写成 failed。blocked 写具体阻碍、所需证据和下一步。
- 失败与修复前证据不得被覆盖删除；复验时保留基线和时间。

### evidence

每项必填 id、kind、locator、observed_at、baseline_ref、summary。

- kind：source、runtime、test、measurement、artifact、specification。
- source：实际读过的文件与符号/行位置；指出关键控制流。
- runtime：实际观察到的 URL、操作与结果，可附截图/网络请求引用。
- test：实际执行命令、环境、退出状态与必要输出定位。
- measurement：实际设备/浏览器/构建模式、样本条件、指标和结果。
- artifact：明确来源的截图/录像/设计稿；不能据此验证异步、权限或后端。
- specification：用户约定、接口合同、标准条款；表示预期，不表示已经实现。
- 避免把访问令牌、真实个人数据、完整敏感响应写进 evidence；用脱敏摘要和受控原件位置。

### checks

每项必填 id、scope、target_id、dimension、question、status、evidence_ids、scenario_ids、finding_ids、reason。

scope 为 project、page、component。target_id 指向相应实体。

项目必评维度：

- reproducibility
- architecture
- security_boundaries
- delivery_observability

每个页面必评维度：

- routing_history
- state_coverage
- responsive_content
- journey_integration

每个组件实例必评维度：

- behavior
- states
- semantics_accessibility
- layout_content
- data_effects
- security_privacy
- performance_lifecycle
- maintainability_integration

同维度可有多个具体检查，不可只用一个含糊问题代替不同风险。sync 生成的是最低覆盖占位，必须继续拆出原子检查并关联场景。将静态与运行检查拆行，避免运行未验证却整行 passed。

## 3. 检查状态与证据

| 状态 | 使用条件 |
|---|---|
| not_checked | 已发现但尚未检查，不能计入完成 |
| passed | 所有列出的具体预期均有充分证据支持 |
| failed | 有证据证明实际违反明确预期，关联 FND |
| blocked | 缺环境、账号、工具、数据、源码或合同，写明缺口 |
| not_applicable | 明确说明此目标为什么不适用，不得用来代替无法验证 |

passed/failed 必须有 EV。failed 还须有 FND。blocked/not_applicable 必须有 reason；not_applicable 的依据应可追溯到已读实现或确认的业务范围。

行为、状态、键盘、异步、路由和完整用户旅程，需要运行或实际测试证据。源码能证明缺少某个已知处理，不能独自证明真实运行全通过。截图只支持该图所覆盖的视觉状态。性能结论需要测量条件；工具未执行时只能列计划。

每个 in_scope 页和实例至少关联一个 SCN；高风险实例关联高风险场景。尽量使用业务可观察断言，而不是只断言 class、loading 布尔值或 toast 出现。

## 4. 问题、蓝图与重构任务

### findings

每项必填：

- id、title、category、severity、confidence、status、owner。
- page_ids、instance_ids、definition_ids、check_ids、scenario_ids、evidence_ids。
- actual、expected、impact、root_cause、root_cause_confidence、remediation、regression_test。
- reproduction：preconditions、steps。
- resolution_evidence_ids：即使暂无也保留数组。

severity：P0、P1、P2、P3。用影响、可达条件、波及范围和可恢复性解释级别，不用代码行数或厂商统计推算。

confidence：confirmed、probable、needs_validation。源码上能确认的缺陷可 confirmed，但运行影响未复现要单独说清。没有证据的风险进入待验证发现，禁止伪装成确定漏洞。

status：open、in_progress、fixed_unverified、resolved、accepted_risk、dismissed。

- resolved 必须有 resolution_evidence_ids，且至少一项为 source、runtime、test 或 measurement；specification/artifact 本身不能作为修复已验证的充分证据。能由源码确认的静态修复允许使用 source EV，不强迫执行浏览器交互。
- resolved FND 关联的当前 CHK/SCN 必须为 passed 或有理由的 not_applicable；正向 check_ids/scenario_ids 与反向 finding_ids 均需一致。blocked、failed、planned、not_checked 不能与已解决结论并存。保留失败与修复前 EV 及版本、时间，复验后更新当前检查/场景判定，不能删除历史证据来消除矛盾。
- accepted_risk/dismissed 必须有 decision.reason 和 decision.authority；接受风险不能由审查代理自行代替用户决定。
- 归并共享根因，列全受影响 CMP/PAGE；保留各实例的独立实际表现。
- failed 检查只能链接已确认发现；待验证风险对应 blocked/not_checked 检查。

### component_blueprints

每项必填 id、definition_id、current_contract、target_contract、change_locations。

每个已登记 DEF 至少有一份 BP，包括尚无 CMP 引用但仍保留在正式台账中的定义；缺少时进入 definitions_without_blueprints，方案覆盖不能完成。

target_contract 必须逐项说明：

1. responsibility：职责和边界。
2. interface：props/events/slots/输出，兼容策略。
3. states：有效状态、转移、反向与中断。
4. data_effects：权威数据、缓存、请求、取消、清理。
5. semantics_accessibility：语义、名称、焦点、键盘、动态反馈。
6. styling_layout：token、布局、内容边界、响应式、层级、动效。
7. performance_lifecycle：渲染、资源、生命周期与预算。
8. security_privacy：信任边界、授权依赖、数据最小化。
9. observability：必要错误、事件、诊断与脱敏。
10. integration：父子契约、其他页面与服务依赖。

对静态叶子组件可简短填写适用范围和不适用理由，不要强迫它实现请求或埋点。源码不可得时标待确认；不得假造函数签名。

### component_plans

每个实例必须有且只有一个条目，必填 instance_id、blueprint_id、disposition、rationale、instance_changes、finding_ids、task_ids、acceptance_criteria、regression_scenario_ids。

- disposition：retain、configure、refactor、replace、remove、investigate。
- 复用 BP 避免逐实例复制整份契约，但 instance_changes 和验收必须说明该位置的独有条件。
- retain 也需要基于本实例的理由和复验场景，不能以“共享组件已通过”代替。
- investigate 用于证据阻塞；建立补证任务，不能据此宣称已形成确定实现。
- configure/refactor/replace/remove/investigate 必须链接 TASK。
- acceptance_criteria、regression_scenario_ids 非空。

### tasks

每项必填 id、title、phase、owner、scope_ids、finding_ids、depends_on、change_locations、implementation_steps、acceptance_criteria、verification_scenario_ids、rollback、risk、status、evidence_ids。

- scope_ids 引用 PRJ/PAGE/DEF/CMP；change_locations 使用真实文件/符号/配置，未知时明确待定位步骤。
- 将前端、后端、平台与产品确认任务分清；必须有明确负责人角色。
- depends_on 引用 TASK，不能有环，阶段顺序不能违反依赖。
- status：planned、in_progress、implemented、verified、blocked、deferred。
- verified 至少有一项 runtime、test 或 measurement EV；source/specification/artifact 本身不能表示任务已实际验证。纯文档或确认任务可提供实际检查相应产物的 test EV。implemented 不能当 verified。
- verified 的 verification_scenario_ids 全部为 passed 或有理由的 not_applicable，且至少一个为 passed；不能把计划或阻塞场景当已完成验收。
- verified 的 depends_on 所列任务均须 verified。若某依赖已不再必要，先调整 depends_on，并在 implementation_steps 保留移除理由；不得新增状态或伪造依赖完成。
- 有条件才附 estimate；写区间、假设、置信度，禁止凭空承诺工时。
- 除正式接受/排除的风险外，每个问题都必须有任务负责解决或确认；resolved FND 也保留对应 TASK 以追溯实际实施与复验。历史任务据实际发生的动作和证据记录，不凭空补造已执行工作。

### release_gates

每项必填 id、name、required、status、evidence_ids、reason。status 与 checks 相同。

按 production_profile 明确必要门槛：核心流程和异常恢复、对象/租户权限、关键可访问性、数据一致性、生产构建、性能预算、可观测性、发布与恢复。门槛不适用须说明原因；不能删掉失败项使结果变绿。

## 5. 完整性与发布门槛

分别报告，禁止合成一个模糊百分比：

1. 发现完整度：各渠道已核对/未核对，路由与运行入口差异，外部子应用/动态分支限制。
2. 页面覆盖：in_scope 页面分母，已访问、静态已读、运行已验证、blocked。
3. 组件覆盖：DEF 和 CMP 分开，必评维度及实例场景是否齐全。
4. 场景覆盖：计划、实际通过、实际失败、阻塞、高风险场景数量。
5. 方案覆盖：每个已登记 DEF 有 BP、每个 CMP 有处置；每个 FND（含 resolved）有 TASK/经授权决定；依赖无环。
6. 发布门槛：哪些已满足，哪些未满足，证据基线是否一致。

audit_coverage_closed 表示台账发现范围已核对且必需检查与场景均已判定；允许存在已确认失败，因此它不表示产品可发布。

definitions_without_blueprints、instances_without_plans、findings_without_tasks 均为方案缺口，阻止 plan_complete / --require-plan，但不单独否定已完成的审查覆盖。新增定义、实例和问题时同时扩大相应分母。

production_gates_satisfied 仅表示本次声明的门槛在台账中满足：完整覆盖、无失败检查/场景、必要门槛通过、无未解决 P0/P1、具备运行与源码证据。不要把机械校验称为安全认证或“保证没有遗漏/bug”。

not_applicable 不增加通过项；blocked 不进入完成项。报告分母如何产生，披露未能发现的范围。审查代理不能穷举无限数据与事件序列；使用有依据的等价类和边界值，逐个登记结构与行为不同的页面/组件。

## 6. 分批执行与续接

progress 必须为对象并保留 current_page、completed_batches、next_actions、unresolved_access、last_updated。current_page 为已有 PAGE ID 或 null；completed_batches、next_actions、unresolved_access 为说明数组，每项是非空字符串，可暂为空数组；last_updated 为非空时间字符串。不要将缺少下一步写成 next_actions: null，以免破坏交接报告。

先将全量 PAGE/DEF/CMP 清单、最低检查占位与 progress 写入台账，再分批深入；每完成一页或一批共享组件立即保存增量结果，不把唯一副本留在工作记忆里，不等全部报告写完才落盘。时间或上下文不足时保留所有未检查项，继续执行后续批次，不缩成“抽几个代表页”而不说明。

并行任务按页、组件定义或领域划分；分配稳定 ID 空间或由主代理统一分配。不要让多个代理同时写同一 audit.json。各代理提交带来源的局部记录，主代理去重、核对边界、合并后执行校验。

使用脚本：

    python3 <skill-dir>/scripts/audit_ledger.py init <output-dir>/audit.json --name "<project>"
    python3 <skill-dir>/scripts/audit_ledger.py sync <output-dir>/audit.json
    python3 <skill-dir>/scripts/audit_ledger.py check <output-dir>/audit.json --require-plan
    python3 <skill-dir>/scripts/audit_ledger.py check <output-dir>/audit.json --require-complete
    python3 <skill-dir>/scripts/audit_ledger.py render <output-dir>/audit.json --out <output-dir>/coverage.md

sync 只添加缺少的最低检查行，绝不填写通过或证据。不要把它当作审查执行。check 只做结构/关联/覆盖校验，不自动识别页面，不验证证据真实性。
