# 001 Popluar Baseline

## 目标

实现全局热门商品推荐。验证数据读取、验证集构造和Recall@20评估流程

## 方法

统计训练集中出现频率最高的商品，对所有session推荐相同的 Top-20 商品

## 指标

- Recall@20:
- MRR@20:

## 问题
- 短 session 和冷启动 session 表现如何?
- 热门商品是否过度集中?

## 下一步

实现基于 session 共现矩阵的召回

## 结论

全局 orders 热门商品能够提升 orders 任务的 Recall@20，但会明显损失 clicks 和 carts 的召回效果。  
per-type popularity baseline 在 clicks、carts 和 overall 指标上表现最好，同时 orders 指标与 orders-only baseline 持平，因此后续将 per-type popularity 作为第一个正式 baseline。