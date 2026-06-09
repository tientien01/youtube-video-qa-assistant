import unittest

from evaluation.metrics import average_metrics, compute_retrieval_metrics


class EvaluationMetricsTest(unittest.TestCase):
    def test_compute_retrieval_metrics(self):
        metrics = compute_retrieval_metrics(
            retrieved_chunk_ids=["chunk-a", "chunk-b", "chunk-c"],
            expected_chunk_ids=["chunk-b", "chunk-d"],
        )

        self.assertEqual(metrics.precision_at_k, 0.3333)
        self.assertEqual(metrics.recall_at_k, 0.5)
        self.assertEqual(metrics.mrr, 0.5)

    def test_average_metrics(self):
        first = compute_retrieval_metrics(
            retrieved_chunk_ids=["chunk-a"],
            expected_chunk_ids=["chunk-a"],
        )
        second = compute_retrieval_metrics(
            retrieved_chunk_ids=["chunk-b"],
            expected_chunk_ids=["chunk-a"],
        )

        metrics = average_metrics([first, second])

        self.assertEqual(metrics.precision_at_k, 0.5)
        self.assertEqual(metrics.recall_at_k, 0.5)
        self.assertEqual(metrics.mrr, 0.5)


if __name__ == "__main__":
    unittest.main()
