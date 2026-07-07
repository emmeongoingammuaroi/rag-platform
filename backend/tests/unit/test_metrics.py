"""Unit tests for app.utils.metrics — thread safety, summary, percentile, reset."""

import threading

from app.utils.metrics import MetricsCollector, _percentile


class TestPercentile:
    def test_empty_data(self):
        assert _percentile([], 95) == 0.0

    def test_single_element(self):
        assert _percentile([5.0], 95) == 5.0

    def test_p95_sorted(self):
        data = list(range(1, 101))  # 1..100
        p95 = _percentile(data, 95)
        assert p95 == 96  # index 95 -> value 96

    def test_p50_median(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        p50 = _percentile(data, 50)
        assert p50 == 3.0

    def test_unsorted_input(self):
        data = [100.0, 1.0, 50.0, 25.0, 75.0]
        p50 = _percentile(data, 50)
        assert p50 == 50.0


class TestMetricsCollectorBasic:
    def test_initial_state(self):
        mc = MetricsCollector()
        summary = mc.summary()
        assert summary["total_requests"] == 0
        assert summary["error_count"] == 0
        assert summary["error_rate"] == 0.0
        assert summary["avg_latency_ms"] == 0.0
        assert summary["rag_requests"] == 0

    def test_record_request(self):
        mc = MetricsCollector()
        mc.record_request(200, 50.0)
        mc.record_request(200, 100.0)
        summary = mc.summary()
        assert summary["total_requests"] == 2
        assert summary["avg_latency_ms"] == 75.0
        assert summary["status_codes"] == {200: 2}

    def test_record_error(self):
        mc = MetricsCollector()
        mc.record_request(500, 100.0)
        mc.record_request(404, 20.0)
        mc.record_request(200, 10.0)
        summary = mc.summary()
        assert summary["error_count"] == 2
        assert summary["error_rate"] == round(2 / 3, 4)

    def test_record_rag_latency(self):
        mc = MetricsCollector()
        mc.record_rag_latency(150.0)
        mc.record_rag_latency(250.0)
        summary = mc.summary()
        assert summary["rag_requests"] == 2
        assert summary["avg_rag_latency_ms"] == 200.0

    def test_record_retrieval_scores(self):
        mc = MetricsCollector()
        mc.record_retrieval_scores([0.8, 0.9, 0.7])
        summary = mc.summary()
        assert summary["avg_retrieval_score"] == round((0.8 + 0.9 + 0.7) / 3, 4)


class TestMetricsCollectorReset:
    def test_reset_clears_all(self):
        mc = MetricsCollector()
        mc.record_request(200, 50.0)
        mc.record_rag_latency(100.0)
        mc.record_retrieval_scores([0.8])
        mc.reset()
        summary = mc.summary()
        assert summary["total_requests"] == 0
        assert summary["rag_requests"] == 0
        assert summary["avg_retrieval_score"] == 0.0


class TestMetricsCollectorP95:
    def test_p95_latency(self):
        mc = MetricsCollector()
        for i in range(1, 101):
            mc.record_request(200, float(i))
        summary = mc.summary()
        assert summary["p95_latency_ms"] == 96.0


class TestMetricsCollectorThreadSafety:
    def test_concurrent_record(self):
        mc = MetricsCollector()
        n_threads = 10
        n_per_thread = 100

        def writer():
            for i in range(n_per_thread):
                mc.record_request(200, float(i))

        threads = [threading.Thread(target=writer) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        summary = mc.summary()
        assert summary["total_requests"] == n_threads * n_per_thread

    def test_concurrent_rag_recording(self):
        mc = MetricsCollector()
        n_threads = 10
        n_per_thread = 50

        def rag_writer():
            for i in range(n_per_thread):
                mc.record_rag_latency(float(i))
                mc.record_retrieval_scores([0.5])

        threads = [threading.Thread(target=rag_writer) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        summary = mc.summary()
        assert summary["rag_requests"] == n_threads * n_per_thread

    def test_concurrent_read_write(self):
        mc = MetricsCollector()
        errors: list[Exception] = []

        def writer():
            for i in range(100):
                mc.record_request(200, float(i))

        def reader():
            for _ in range(100):
                try:
                    mc.summary()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        threads += [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
