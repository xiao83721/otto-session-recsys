# 001 Popular Baseline（热门召回基线）

> 实验记录模板。带 `<填:…>` 的是你要补的内容；`> 写什么：` 是每节的提示。
> 数字尽量贴**真实跑出来的**，别用估的。写完把提示行删掉即可。

| 元信息      |                                                     |
| ----------- | --------------------------------------------------- |
| 日期        | <2026-06-15>                                        |
| 阶段        | Stage 1（依赖 Stage 0 的验证集与官方评估口径）      |
| 分支/commit | <填:baseline-popular / commit hash>                 |
| 相关记录    | [[000_eval_setup]]（验证集与官方 Recall@20 的搭建） |

------

## 1. 目标

> 写什么：用这个实验要确立什么。一句话即可。

用全局热门商品做最简单的召回，在**无泄漏 + 官方加权 Recall@20** 口径下拿到第一个**可信的基线分**，作为后续 co-visitation / 排序模型的对照地板。

用全局最热门的商品，对三种行为“点击”，“加购”，“下单“行为推荐热门商品，使用官网的Recall@20作为一个评估，得到基本的baseline

## 2. 数据与验证集

> 写什么：简述 Stage 0 怎么切的、为什么不泄漏。细节可只引用 000，不重复。

- 验证集构造：Plan A —— level1 按时间（holdout 最后7天）划分 train/val；level2 对每个 val session **随机断点** `k∈[1,len-1]`，断点前=输入段、断点后=答案段。
- 防泄漏：热门统计只读 `local_train.jsonl`（🟢 训练段），预测在 `local_val_input.jsonl`（🟢 输入段），**绝不碰答案段**。
- 评估口径：官方微平均 Recall@20，加权 `0.1·clicks + 0.3·carts + 0.6·orders`。
- 规模：train sessions=`<填>`，val sessions=`<填>`。

## 3. 方法

> 写什么：热门是怎么"训练"和预测的；三种 popular-by 的区别。

- "训练" = 在训练段统计每个商品的交互次数（`Counter`），取 Top-20。无迭代式训练。
- 预测 = 给**所有** session 推同一份 Top-20（不个性化）。
- 三种先验口径：
  - `orders`：只数下单，三类共用一份
  - `clicks,carts,orders`：合并计数，三类共用一份
  - `per_type`：点击/加购/下单各数各的，三类各用各的（任务相关的先验）

## 4. 实验设置

> 写什么：可复现的命令 + 关键参数（seed、top-k）。

```bash
# 1) 生成验证集（Stage 0）
python scripts/000_manual_dataset_time_cut.py --holdout-days 7 --seed 42

# 2) 在 val 上预测（统计读 local_train，预测在 local_val_input）
python scripts/001_manual_popular_baseline.py \
    --train data/processed/local_train.jsonl \
    --test  data/processed/local_val_input.jsonl \
    --output scripts/preds_val.csv --popular-by per_type

# 3) 官方打分
python scripts/000_manual_eval_recall.py \
    --labels data/processed/local_val_labels.jsonl --pred scripts/preds_val.csv
```

参数：`top_k=20`，`seed=42`，`holdout_days=<填>`。

## 5. 结果

> 写什么：把真实数字填进去。主表是 per_type（你已有）。建议把另外两种 popular-by
> 也在官方口径下补跑，凑成三配置对比（同一把尺子才有意义）。

### 5.1 官方口径下三种 popular-by 对比（Recall@20）

| 配置                | clicks     | carts      | orders     | **加权分** |
| ------------------- | ---------- | ---------- | ---------- | ---------- |
| per_type            | <0.008175> | <0.007298> | <0.007812> | <0.007694> |
| orders              | <0.005193> | <0.005911> | <0.007812> | <0.006979> |
| clicks,carts,orders | <0.008231> | <0.006061> | <0.005125> | <0.005716> |

> 命中/分母（per_type，供核对）：clicks `<填:246277/30124006>`、carts `<填:32687/4479178>`、orders `<填:14997/1919860>`。

### 5.2 GT 结构诊断（解释为什么分低）

| 类型   | 平均 GT | 中位 GT | 有命中的 session 占比 |
| ------ | ------- | ------- | --------------------- |
| clicks | <填>    | <填>    | <填:~10%>             |
| carts  | <填>    | <填>    | <填>                  |
| orders | <填>    | <填>    | <填>                  |

## 6. 分析

> 写什么：用你自己的话解释现象。下面是几个该回答的问题，逐条写。

- **哪种 popular-by 最好？为什么？** <填:per_type，因为任务相关的先验……>
- **为什么绝对分这么低（~0.008）？** <填:>
  - 提示要点：Plan A 的 GT = 长 session 随机截断后的"剩余"，以该用户私人长尾浏览为主；全局 Top-20 是大众爆款，很少撞上 → 多数 session 0 命中。这是热门作为"地板"的正常表现。
- **这个分能和谁比、不能和谁比？** <填:>
  - 提示：无泄漏 + 口径一致 → 可与自己后续方法（covis/lgbm）横比；但 Plan A 的 GT 构造 ≠ 官方，**绝对值不可对标 Kaggle 排行榜**。

## 7. 结论

> 写什么：一两句收口。

建立了无泄漏、官方口径的评估闭环，并拿到热门基线地板 weighted=0.1*clicks + 0.3*carts + 0.6*orders；后续方法以此为对照

## 8. 局限与注意

> 写什么：诚实记录已知问题，方便以后回看。

- Plan A 的随机断点与 split_ts 解耦，存在"用未来统计预测过去"的轻微时间松弛；绝对值不对标排行榜。
- 热门完全不个性化，对长尾/冷启动 session 几乎无效。
- 评估只实现了官方 Recall@20；未做 MRR（OTTO 官方口径本身不含 MRR，可选补充）。

## 9. 下一步

> 写什么：指向下一个实验。

实现 co-visitation 共现召回（[[002_covisitation]]）：用 session 最近交互的商品查共现，预期在**同一套验证集**上相对热门有明显跳升——这也是对本套 harness 的第一次真正检验。

------

## 附录：踩过的坑（可选但推荐）

> 写什么：这次调试里"能跑但悄悄错"的坑，列出来对自己最有价值。

- <填:例如 `clikcs` 拼写让 clicks 被静默丢弃、`.strip()`/`.split()`、`hits` 未初始化、`* MS_PER_DAY` 单位、set 不可 JSON 序列化……>