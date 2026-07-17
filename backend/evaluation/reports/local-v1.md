# Local V1 Retrieval Evaluation

Dataset: `local-v1-bilingual-retrieval@1.0.0` (12 reviewed questions).

No release threshold was chosen before this baseline. The recommendation follows the committed selection policy.

| Variant | Recall@K | Hit@K | MRR | nDCG@K | Citation accuracy | Index ms | p95 query ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed_word|none|lexical | 1.0000 | 1.0000 | 0.9583 | 0.9745 | 0.3646 | 0.00 | 0.8954 |
| fixed_word|ollama/qwen3-embedding:0.6b|dense | 1.0000 | 1.0000 | 0.9583 | 0.9692 | 0.3646 | 7205.44 | 367.1805 |
| fixed_word|ollama/qwen3-embedding:0.6b|rrf | 1.0000 | 1.0000 | 0.9583 | 0.9626 | 0.3646 | 7205.44 | 367.8988 |
| fixed_word|ollama/qwen3-embedding:0.6b|reranked | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3687 | 7205.44 | 5070.3218 |
| fixed_word|BAAI/bge-m3|dense | 1.0000 | 1.0000 | 1.0000 | 0.9866 | 0.3687 | 4000.09 | 190.4975 |
| fixed_word|BAAI/bge-m3|rrf | 1.0000 | 1.0000 | 1.0000 | 0.9933 | 0.3687 | 4000.09 | 191.4174 |
| fixed_word|BAAI/bge-m3|reranked | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3687 | 4000.09 | 4870.3339 |
| hierarchical_sentence|none|lexical | 0.4722 | 0.5000 | 0.5000 | 0.5000 | 0.3056 | 0.00 | 1.3248 |
| hierarchical_sentence|ollama/qwen3-embedding:0.6b|dense | 0.5833 | 0.5833 | 0.5833 | 0.5833 | 0.3611 | 6189.66 | 402.1650 |
| hierarchical_sentence|ollama/qwen3-embedding:0.6b|rrf | 0.4722 | 0.5000 | 0.5000 | 0.5000 | 0.3056 | 6189.66 | 402.9818 |
| hierarchical_sentence|ollama/qwen3-embedding:0.6b|reranked | 0.5833 | 0.5833 | 0.5833 | 0.5833 | 0.3611 | 6189.66 | 4517.2731 |
| hierarchical_sentence|BAAI/bge-m3|dense | 0.5833 | 0.5833 | 0.5833 | 0.5833 | 0.3611 | 2991.75 | 183.1121 |
| hierarchical_sentence|BAAI/bge-m3|rrf | 0.5833 | 0.5833 | 0.5417 | 0.5526 | 0.3611 | 2991.75 | 184.4587 |
| hierarchical_sentence|BAAI/bge-m3|reranked | 0.5833 | 0.5833 | 0.5833 | 0.5833 | 0.3611 | 2991.75 | 4326.9270 |

## Recommendation

`fixed_word|BAAI/bge-m3|rrf`

Policy: within the post-baseline 0.01 citation/nDCG equivalence margin, choose lower p95 latency; then Recall@K and MRR.

## Hardware/config fingerprint

- Config SHA-256: `ce7dff5a781d24b224c3e06b1ced81608e3de31834fa4d359b64a3c4b3e3808f`
- Platform: `Windows-11-10.0.26200-SP0`
- Processor: `Intel64 Family 6 Model 170 Stepping 4, GenuineIntel`
- Logical CPUs: `14`
- Python peak memory: `276.42 MB`
