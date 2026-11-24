# BENCHMARK · 直播电商合规守卫 MCP（规则层 核心 v1.4 ＋ 行业插件（cosmetics v1.0、food v1.0））

- 生成日期：2026-11-24
- 评测对象：`lcg` 规则引擎（src/lcg；规则源为核心包 rules.v1.json ＋ rules/plugins/*.json 行业插件；根 server.py 为兼容 shim）
- 规则层用例：87 条（良性 37，对抗 50）
- **整体通过率：100.0%**（87/87）
- **高危样本检出率：100.0%**（46/46）
- **干净样本误报率：0.0%**（0/32，越低越好）
- LLM 层红队用例：12 条（注入/越狱，交由 DeepTeam·PyRIT 在 LLM 层裁决）
- 语义层待跑用例：8 条（谐音/拆字/emoji/暗示，规则层已确认漏检，配 key 后由 LLM 层裁决）

| ID | 类型 | 期望 | 实际 | 结果 | 命中数 | 备注 |
|---|---|---|---|---|---|---|
| b01 | benign | clean | clean | PASS | 0 | 普通工业品客观描述，应放行 |
| b02 | benign | low | low | PASS | 1 | 合规话术，A货术语仅low提示 |
| b03 | benign | clean | clean | PASS | 0 | 普通服装描述，应放行 |
| b04 | benign | low | low | PASS | 1 | 冰种术语low提示，整体合规 |
| b05 | benign | clean | clean | PASS | 0 | 正常客服话术，应放行 |
| b06 | benign | clean | clean | PASS | 0 | “第一款/第一步/第一遍”是次序不是排名，序数消歧后应放行 |
| b07 | benign | low | low | PASS | 1 | “第一期/第一件”序数消歧，仅冰种术语 low 提示，不应判绝对化 high |
| b08 | benign | clean | clean | PASS | 0 | 普通食品客观口感描述，“配料干净”非医疗，应放行 |
| b09 | benign | clean | clean | PASS | 0 | 合规保健功能（备案目录内）+法定声明“不能代替药物”，必须放行 |
| b10 | benign | clean | clean | PASS | 0 | 普通食品产地/口感描述，应放行 |
| b11 | benign | clean | clean | PASS | 0 | 普通食品饮用场景，“解腻”非医疗功效，应放行 |
| b12 | benign | clean | clean | PASS | 0 | 保湿/补水/滋润为普通化妆品合规功效，应放行 |
| b13 | benign | clean | clean | PASS | 0 | 美白/防晒为需注册的特殊化妆品合规功效，持特证宣称应放行 |
| b14 | benign | clean | clean | PASS | 0 | “敏感肌/温和清洁”为合规肤质与功效描述，不等同“抗敏”医疗宣称，应放行 |
| b15 | benign | clean | clean | PASS | 0 | 提亮肤色为合规妆效，非医疗作用，应放行 |
| b16 | benign | clean | clean | PASS | 0 | 普通家电客观参数，应放行 |
| b17 | benign | clean | clean | PASS | 0 | 普通服装客观描述，应放行 |
| b18 | benign | low | low | PASS | 1 | 冰种术语low提示，带证书复检合规 |
| b19 | benign | clean | clean | PASS | 0 | 普通食品食用场景，应放行 |
| b20 | benign | clean | clean | PASS | 0 | 普通妆效描述，应放行 |
| b21 | benign | clean | clean | PASS | 0 | 正常客服售后话术，应放行 |
| b22 | benign | clean | clean | PASS | 0 | 普通箱包客观材质/结构描述，应放行 |
| b23 | benign | clean | clean | PASS | 0 | 正常质保售后条款，非终身不坏承诺，应放行 |
| b24 | benign | clean | clean | PASS | 0 | 普通家电参数与使用场景，应放行 |
| b25 | benign | clean | clean | PASS | 0 | “第三款/上一周”为次序与时间，序数消歧后应放行 |
| b26 | benign | clean | clean | PASS | 0 | 普通食品原料/工艺/口感描述，应放行 |
| b27 | benign | clean | clean | PASS | 0 | 普通食品食用场景，应放行 |
| b28 | benign | clean | clean | PASS | 0 | 普通肤感描述，无医疗/速效宣称，应放行 |
| b29 | benign | clean | clean | PASS | 0 | 控油/柔顺为合规普通护发功效，应放行 |
| b30 | benign | clean | clean | PASS | 0 | 无种水品级词，仅圈口/证书/复检等客观信息，应放行 |
| b31 | benign | clean | clean | PASS | 0 | 斜杠为并列分隔而非词内阻断，剥离后不得拼成违规词，应放行 |
| b32 | benign | clean | clean | PASS | 0 | 合规活动价与库存描述，无虚构原价/紧迫感词，应放行 |
| b33 | benign | clean | clean | PASS | 0 | 普通食品口感/包装描述，应放行 |
| b34 | benign | clean | clean | PASS | 0 | 普通护手霜保湿滋润，合规肤感描述，应放行 |
| b35 | benign | clean | clean | PASS | 0 | 合规售后与运费险承诺，非终身不坏保证，应放行 |
| b36 | benign | low | low | PASS | 1 | 糯种术语 low 提示，带证书复检合规 |
| b37 | benign | clean | clean | PASS | 0 | “首批/第一款/第二步”为次序与步骤，序数消歧后应放行 |
| a01 | adversarial | high | high | PASS | 14 | 多重高危叠加 |
| a02 | adversarial | high | high | PASS | 9 | 绝对化用语+虚构紧迫感 |
| a03 | adversarial | high | high | PASS | 5 | 迷信伪科学+医疗功效 |
| a04 | adversarial | high | high | PASS | 7 | 投资收益承诺+误导 |
| a05 | adversarial | high | high | PASS | 3 | 变体联系方式站外导流 |
| a06 | adversarial | high | high | PASS | 7 | 绝对化+翡翠夸饰品相 |
| a07 | adversarial | medium | medium | PASS | 1 | 翡翠品级噱头，中风险 |
| a08 | adversarial | low | low | PASS | 4 | 诱导性叫卖，低风险提示 |
| a09 | adversarial | high | high | PASS | 1 | 全角字母数字冒号变体站外导流；归一化前漏报，等长归一化后命中导流正则判high（无中文高危词，专测归一化） |
| a10 | adversarial | high | high | PASS | 1 | 全角数字百分号变体；归一化前漏报，等长归一化后命中100%绝对化判high |
| a11 | adversarial | high | high | PASS | 7 | 排名/榜首用法的“第一”必须仍判 high，序数消歧不得放过；第一名亦同 |
| a12 | adversarial | high | high | PASS | 1 | 插空格拆分“最好”，等长层漏报，紧凑归一化剔除空格后规则层判 high |
| a13 | adversarial | high | high | PASS | 1 | 间隔号变体 NO·1，紧凑层剔除中点后命中绝对化符号判 high |
| a14 | adversarial | high | high | PASS | 1 | emoji+空格阻断“微”与号码，紧凑层剔除后命中严格导流正则判 high |
| a15 | adversarial | high | high | PASS | 3 | 食品宣称降血压/稳糖尿病/比药管用，违反广告法17条与食品安全法73条，食品包判 high |
| a16 | adversarial | high | high | PASS | 5 | 普通食品包治百病/根治胃病，疾病治疗宣称+核心消炎/根治/无效退款，判 high |
| a17 | adversarial | high | high | PASS | 9 | 保健食品医生患者代言+肿瘤疗效+无毒副作用+替代药物，违反广告法18条，判 high |
| a18 | adversarial | high | high | PASS | 4 | 安全性断言+绝对化+健康恐惧，食品包与核心规则判 high |
| a19 | adversarial | high | high | PASS | 10 | 药妆/抗敏/湿疹皮炎/根治痘痘均为医疗作用宣称，违反化妆品条例43条，判 high |
| a20 | adversarial | high | high | PASS | 12 | 医学护肤+安全断言+速效（一次/3天/永不反弹），违反广告审查标准100条，判 high |
| a21 | adversarial | high | high | PASS | 13 | 医用级/临床治愈/修复疤痕红血丝/立刻见效/100%不过敏，医疗作用+速效断言，判 high |
| a22 | adversarial | medium | medium | PASS | 4 | 贬低同类+无依据销量排名，化妆品包判 medium（无 high 词时不得升到 high） |
| a23 | adversarial | high | high | PASS | 3 | 站外导流：扫码/进群/私下转账变体 |
| a24 | adversarial | high | high | PASS | 3 | 虚构原价+紧迫感误导 |
| a25 | adversarial | high | high | PASS | 3 | 多绝对化用语叠加 |
| a26 | adversarial | high | high | PASS | 6 | 翡翠投资升值+传家宝诱导 |
| a27 | adversarial | high | high | PASS | 4 | 普通食品多项疾病/功效宣称 |
| a28 | adversarial | high | high | PASS | 2 | 化妆品消炎/药用医疗作用宣称 |
| a29 | adversarial | high | high | PASS | 1 | 薇信+号码变体站外导流，正则命中 |
| a30 | adversarial | high | high | PASS | 3 | 迷信伪科学功效叠加 |
| a31 | adversarial | high | high | PASS | 3 | 永久/终身不坏/零风险，虚假承诺与风险保证，判 high |
| a32 | adversarial | high | high | PASS | 4 | 投资首选+只涨不跌，收益承诺判 high |
| a33 | adversarial | high | high | PASS | 2 | 扫码/二维码/进群站外导流，判 high |
| a34 | adversarial | medium | medium | PASS | 3 | 贬低同类+无依据销量排名，化妆品包判 medium |
| a35 | adversarial | high | high | PASS | 2 | 食品安全性断言，插件规则判 high |
| a36 | adversarial | high | high | PASS | 3 | 食品疾病治疗宣称（失眠/便秘根治），判 high |
| a37 | adversarial | high | high | PASS | 4 | 速效+永不反弹+立刻见效，化妆品插件判 high |
| a38 | adversarial | high | high | PASS | 6 | 医用级/修复红血丝/祛疤医疗作用宣称，判 high |
| a39 | adversarial | high | high | PASS | 3 | 迷信伪科学功效叠加，判 high |
| a40 | adversarial | high | high | PASS | 6 | 夸饰品相叠加“之王”绝对化，升至 high |
| a41 | adversarial | high | high | PASS | 4 | 医疗代言+疗效暗示+无效退款，判 high |
| a42 | adversarial | high | high | PASS | 2 | 站外私下交易与支付宝直转，淘宝规则判 high |
| a43 | adversarial | high | high | PASS | 1 | 斜杠分隔阻断“最好”，紧凑层剥离斜杠后规则层判 high |
| a44 | adversarial | high | high | PASS | 1 | 斜杠分隔联系方式字母，紧凑层剥离后命中严格导流正则判 high |
| a45 | adversarial | high | high | PASS | 3 | 多绝对化用语叠加（极品/万能/史无前例），判 high |
| a46 | adversarial | high | high | PASS | 4 | 普通食品补肾壮阳/排毒/特效功效宣称，判 high |
| a47 | adversarial | high | high | PASS | 3 | 永久承诺+零风险保证+包过承诺，虚假承诺判 high |
| a48 | adversarial | high | high | PASS | 8 | 翡翠无依据货源/保真/收藏必涨诱导，判 high |
| a49 | adversarial | high | high | PASS | 5 | 化妆品医用级/镇痛/特效医疗作用宣称，判 high |
| a50 | adversarial | high | high | PASS | 2 | 加群/扫码站外导流，判 high |

> 复现：`python evals/run_evals.py`。本报告由脚本生成，规则或用例变更后在 CI 自动刷新。
> 仅为合规风险提示，不构成法律意见，以监管机关与平台最新规则为准。
