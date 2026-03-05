# Retrieval Benchmark v1

Deterministic offline benchmark dataset for Task 10.2 memory recall validation.

## Metric Definitions
- Precision@k = relevant hits in top-k / k
- Recall@k = relevant hits in top-k / total relevant docs
- MRR = reciprocal rank of first relevant hit
- NDCG@10 = DCG@10 / IDCG@10 using graded relevance (0..3)
