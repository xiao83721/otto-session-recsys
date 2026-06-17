# 002 covisitation

## 核心思想
在已有的数据中，商品以对出现的情况（商品aid1，商品aid2），统计这种共现对在整个数据的分数，形成一个covis的共现查询表，对需要预测的session，给出n个相关的商品aid，在covis统计表中计算前k个共现商品，即预测的答案

## 代码实现
对于iter前缀的function一般要考虑生成以yield 返回的循环迭代器

## 注意事项
整个covis的表构成需要删除长尾部分，top-neighbors是限制covis表的长度；time window和n trunc控制了covis的生成质量，一般而言time-window和n trunc放宽会把最后的recall指标升高（需要结合实际的数据）

预测时不需要对ts进行限制，时间限制已经在构建covis表时实现了，查询covis共现表的商品本身带有时间限制


## 参数
n_trunc=30, time_window=1h(3600000ms), top_neighbors=40, n_recent=20, top_k=20

## 结果（官方口径 Recall@20，同一份 Plan A 验证集）

| 方法 | clicks | carts | orders | 加权分 |
|---|---|---|---|---|
| 热门(per_type) | 0.008175 | 0.007298 | 0.007812 | 0.007694 |
| 共现 covis     | 0.099856 | 0.080743 | 0.106187 | 0.097921 |
| 提升           | 12.2×    | 11.1×    | 13.6×    | **12.7×** |

评估结果以stage0的统一分割方案，covis矩阵隔离val_labels，整体recall较高是由于order的gt本身在数据集中集合大小较小（labels为191w，clicks为3000W+，carts为447w+），从共现的推荐来看，比较容易覆盖到对应的GT，且order在整个recall的权重占比为0.6