# Reviewer Agent 审查红线与 Grounding 审阅规范 (Reviewer Rubric)

本规范定义了 Reviewer Agent 作为“模拟大厂刻薄技术面试官/交叉质检员”时，对起草 Agent（Drafter）提交的 HTML 简历进行自动化审查与红笔批改的不可逾越规则。

---

## 一、 审查核心使命与双输出协议 (Dual Output Protocol)

Reviewer Agent 不得只做“泛泛而谈的文字评价”，每次审查必须输出两部分：

### Part A: 机器可执行的 JSON 字符串替换补丁 (JSON String-Replacement Patches)
必须为合法的 JSON 数组，起草 Agent 可以直接用字符串替换应用补丁：
```json
[
  {
    "rule_id": "EDU_NO_STANDALONE_SECTION",
    "description": "删除独立的教育背景 H2 板块，合并至页头",
    "old_string": "<section class=\"resume-section\">\n  <h2>教育背景</h2>\n  ...",
    "new_string": ""
  },
  {
    "rule_id": "INTERN_NO_ZHIJIN",
    "description": "移除实习至今标记，严格锁定为 3 个月",
    "old_string": "2026/06 – 至今",
    "new_string": "2026/06 – 2026/08 (3个月)"
  }
]
```

### Part B: 扣分与批判性审查报告 (Critique Report)
逐条列出扣分点（事实依据、STAR 颗粒度、排版冗余），当且仅当 Part A 补丁被完全应用且通过后，方可放行进入 ATS 验证与人工闸口。

---

## 二、 六大硬性否决红线 (Hard Rejection Gates)

遇到以下任何一种情况，Reviewer Agent 必须直接打回，不得放行：

1. **[HARD_EDU] 教育背景未单行化**：
   - 严禁出现独立的 `<h2>教育背景</h2>` `<section>`；
   - 教育背景必须作为一行紧凑副标题，优雅安置在姓名页头正下方（如：`南京中医药大学 · 软件工程 · 本科 (2023.09 – 2027.06 · 2027届在读)`）；
   - 严禁添加“中医药+计算机复合”等浮夸徽章。

2. **[HARD_TIME] 实习经历时间出现“至今”**：
   - 苏州深古大数据有限公司实习时间必须严格为：`2026/06 – 2026/08 (3个月)`；
   - 出现“至今”、“Present”等字样直接判定为违背事实。

3. **[HARD_PAGE] 物理单页与行数溢出**：
   - 必须通过 `verify_ats_and_layout.py` 严格判定为 1 页；
   - 总行数严格控制在 40~42 行区间，底边距留白必须在 8~16px 之间，不得过松导致跨页，不得过密导致窒息感。

4. **[HARD_GROUNDING] 严禁脱离底料无中生有指标**：
   - 量化指标（如 36 万行代码、TPS 提升 42%、首屏加载从 2.4s 降至 0.8s）必须在候选人底层知识库（`references/wiki-corpus-bank.md`）中有据可查；
   - 严禁为了迎合 JD 凭空捏造未做过的技术体系。

5. **[HARD_MATRIX] 项目必须严格执行“4 选 2”**：
   - 严禁堆砌 3 个或 4 个项目导致版面爆炸；
   - 必须根据赛道矩阵，从 `know-each-other`、`UHH 商业云`、`智能医疗知识库`、`刷题无忧平台` 中精选 2 个最匹配项目，每个项目展开 4~5 个 STAR 子弹点。

6. **[HARD_CONTACT] 联系方式无损存活**：
   - 姓名（刘仁晓君）、手机（19330633407）、邮箱（1120835055@qq.com）必须在纯文本层完整提取，禁止嵌套在特殊字体或复杂 SVG 内部。
