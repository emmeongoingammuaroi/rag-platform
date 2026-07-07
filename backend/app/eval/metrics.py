"""Retrieval and generation evaluation metrics."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetrievalMetrics:
    """Computed retrieval quality metrics."""

    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    hit_rate: float = 0.0


@dataclass
class GenerationMetrics:
    """Computed generation quality metrics (LLM-as-judge)."""

    faithfulness: float = 0.0
    answer_relevance: float = 0.0


@dataclass
class LatencyMetrics:
    """Latency percentile metrics in milliseconds."""

    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


@dataclass
class EvalResult:
    """Complete evaluation result for a single sample."""

    query: str
    retrieved_ids: list[str] = field(default_factory=list)
    relevant_ids: list[str] = field(default_factory=list)
    generated_answer: str = ""
    expected_answer: str = ""
    context: str = ""
    retrieval_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


def compute_precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of retrieved@k that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / k


def compute_recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """Fraction of relevant documents found in retrieved@k."""
    if not relevant:
        return 1.0
    top_k = retrieved[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant)
    return hits / len(relevant)


def compute_mrr(retrieved: list[str], relevant: set[str]) -> float:
    """Mean Reciprocal Rank — 1/rank of first relevant result."""
    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def compute_hit_rate(retrieved: list[str], relevant: set[str]) -> float:
    """1 if any relevant document is in retrieved, else 0."""
    for doc_id in retrieved:
        if doc_id in relevant:
            return 1.0
    return 0.0


def aggregate_retrieval_metrics(results: list[EvalResult], k: int) -> RetrievalMetrics:
    """Aggregate retrieval metrics across all samples."""
    if not results:
        return RetrievalMetrics()

    precisions: list[float] = []
    recalls: list[float] = []
    mrrs: list[float] = []
    hits: list[float] = []

    for r in results:
        relevant = set(r.relevant_ids)
        if not relevant:
            continue
        precisions.append(compute_precision_at_k(r.retrieved_ids, relevant, k))
        recalls.append(compute_recall_at_k(r.retrieved_ids, relevant, k))
        mrrs.append(compute_mrr(r.retrieved_ids, relevant))
        hits.append(compute_hit_rate(r.retrieved_ids, relevant))

    n = len(precisions) or 1
    return RetrievalMetrics(
        precision_at_k=sum(precisions) / n,
        recall_at_k=sum(recalls) / n,
        mrr=sum(mrrs) / n,
        hit_rate=sum(hits) / n,
    )


def compute_latency_percentiles(latencies_ms: list[float]) -> LatencyMetrics:
    """Compute p50, p95, p99 from a list of latency values."""
    if not latencies_ms:
        return LatencyMetrics()
    sorted_lat = sorted(latencies_ms)
    n = len(sorted_lat)
    return LatencyMetrics(
        p50=sorted_lat[int(n * 0.50)],
        p95=sorted_lat[min(int(n * 0.95), n - 1)],
        p99=sorted_lat[min(int(n * 0.99), n - 1)],
    )


_FAITHFULNESS_PROMPT = """\
You are an evaluation judge. Given a context, a question, and an answer, rate how \
faithful the answer is to the provided context.

A faithful answer only contains information that can be derived from the context. \
If the answer includes claims not supported by the context, it is unfaithful.

Rate from 1 to 5:
1 = Completely unfaithful (hallucinated)
2 = Mostly unfaithful
3 = Partially faithful
4 = Mostly faithful
5 = Completely faithful

Context:
{context}

Question:
{question}

Answer:
{answer}

Respond with ONLY a single integer (1-5)."""

_RELEVANCE_PROMPT = """\
You are an evaluation judge. Given a question and an answer, rate how relevant \
the answer is to the question.

A relevant answer directly addresses the question asked and provides useful information.

Rate from 1 to 5:
1 = Completely irrelevant
2 = Mostly irrelevant
3 = Partially relevant
4 = Mostly relevant
5 = Completely relevant (directly answers the question)

Question:
{question}

Answer:
{answer}

Respond with ONLY a single integer (1-5)."""


async def judge_faithfulness(context: str, question: str, answer: str) -> float:
    """Use LLM-as-judge to score faithfulness (0.0-1.0)."""
    from app.services.llm import llm_service

    try:
        response = await llm_service.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": _FAITHFULNESS_PROMPT.format(
                        context=context, question=question, answer=answer
                    ),
                }
            ],
            temperature=0.0,
            max_tokens=5,
        )
        score = int(response["content"].strip())
        return max(0.0, min(1.0, (score - 1) / 4.0))
    except (ValueError, TypeError):
        logger.warning("Failed to parse faithfulness score")
        return 0.0


async def judge_answer_relevance(question: str, answer: str) -> float:
    """Use LLM-as-judge to score answer relevance (0.0-1.0)."""
    from app.services.llm import llm_service

    try:
        response = await llm_service.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": _RELEVANCE_PROMPT.format(question=question, answer=answer),
                }
            ],
            temperature=0.0,
            max_tokens=5,
        )
        score = int(response["content"].strip())
        return max(0.0, min(1.0, (score - 1) / 4.0))
    except (ValueError, TypeError):
        logger.warning("Failed to parse relevance score")
        return 0.0


async def aggregate_generation_metrics(results: list[EvalResult]) -> GenerationMetrics:
    """Aggregate generation metrics using LLM-as-judge across all samples."""
    if not results:
        return GenerationMetrics()

    faithfulness_scores: list[float] = []
    relevance_scores: list[float] = []

    for r in results:
        if not r.generated_answer:
            continue
        f_score = await judge_faithfulness(r.context, r.query, r.generated_answer)
        r_score = await judge_answer_relevance(r.query, r.generated_answer)
        faithfulness_scores.append(f_score)
        relevance_scores.append(r_score)

    n = len(faithfulness_scores) or 1
    return GenerationMetrics(
        faithfulness=sum(faithfulness_scores) / n,
        answer_relevance=sum(relevance_scores) / n,
    )


class LatencyTracker:
    """Context manager to track operation latency in milliseconds."""

    def __init__(self) -> None:
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "LatencyTracker":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
