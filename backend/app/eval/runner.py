"""Evaluation runner — executes retrieval + generation pipeline on an eval dataset."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from app.eval.dataset import EvalDataset, EvalSample
from app.eval.metrics import (
    EvalResult,
    GenerationMetrics,
    LatencyMetrics,
    LatencyTracker,
    RetrievalMetrics,
    aggregate_generation_metrics,
    aggregate_retrieval_metrics,
    compute_latency_percentiles,
)
from app.rag.retriever import format_context, retrieve
from app.services.llm import llm_service

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question based ONLY on "
    "the provided context. If the context doesn't contain enough information, "
    "say so clearly."
)


@dataclass
class EvalConfig:
    """Configuration variant for an evaluation run."""

    name: str
    reranker_enabled: bool = False
    hyde_enabled: bool = False
    top_k: int = 5
    score_threshold: float = 0.7
    description: str = ""


@dataclass
class EvalRunResult:
    """Aggregated results from a full evaluation run."""

    config_name: str
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation: GenerationMetrics = field(default_factory=GenerationMetrics)
    latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    sample_count: int = 0
    sample_results: list[EvalResult] = field(default_factory=list)


async def run_single_sample(
    sample: EvalSample,
    user_id: UUID,
    config: EvalConfig,
) -> EvalResult:
    """Run retrieval + generation for a single eval sample."""
    from app.core.config import settings

    original_reranker = settings.RERANKER_ENABLED
    original_hyde = settings.HYDE_ENABLED
    settings.RERANKER_ENABLED = config.reranker_enabled
    settings.HYDE_ENABLED = config.hyde_enabled

    try:
        with LatencyTracker() as retrieval_timer:
            results = await retrieve(
                query=sample.query,
                user_id=user_id,
                top_k=config.top_k,
                score_threshold=config.score_threshold,
            )

        context = format_context(results)
        retrieved_ids = [str(r["id"]) for r in results]

        with LatencyTracker() as generation_timer:
            response = await llm_service.chat_completion(
                messages=[
                    {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {sample.query}",
                    },
                ],
                temperature=0.0,
            )
        generated_answer = response["content"] or ""

        return EvalResult(
            query=sample.query,
            retrieved_ids=retrieved_ids,
            relevant_ids=sample.relevant_chunk_ids,
            generated_answer=generated_answer,
            expected_answer=sample.expected_answer,
            context=context,
            retrieval_latency_ms=retrieval_timer.elapsed_ms,
            generation_latency_ms=generation_timer.elapsed_ms,
            total_latency_ms=retrieval_timer.elapsed_ms + generation_timer.elapsed_ms,
        )
    finally:
        settings.RERANKER_ENABLED = original_reranker
        settings.HYDE_ENABLED = original_hyde


async def run_eval(
    dataset: EvalDataset,
    user_id: UUID,
    config: EvalConfig,
    skip_generation_metrics: bool = False,
) -> EvalRunResult:
    """Run full evaluation on a dataset with a given config.

    Args:
        dataset: Evaluation dataset with queries and expected answers.
        user_id: The user whose documents to search (eval user).
        config: Pipeline config variant to evaluate.
        skip_generation_metrics: If True, skip LLM-as-judge (faster).

    Returns:
        Aggregated retrieval, generation, and latency metrics.
    """
    logger.info("Starting eval run: config=%s, samples=%d", config.name, len(dataset))

    sample_results: list[EvalResult] = []
    for i, sample in enumerate(dataset.samples):
        logger.info("  [%d/%d] %s", i + 1, len(dataset), sample.query[:60])
        result = await run_single_sample(sample, user_id, config)
        sample_results.append(result)

    retrieval_metrics = aggregate_retrieval_metrics(sample_results, k=config.top_k)

    if skip_generation_metrics:
        generation_metrics = GenerationMetrics()
    else:
        generation_metrics = await aggregate_generation_metrics(sample_results)

    latencies = [r.total_latency_ms for r in sample_results]
    latency_metrics = compute_latency_percentiles(latencies)

    return EvalRunResult(
        config_name=config.name,
        retrieval=retrieval_metrics,
        generation=generation_metrics,
        latency=latency_metrics,
        sample_count=len(sample_results),
        sample_results=sample_results,
    )


async def run_ab_comparison(
    dataset: EvalDataset,
    user_id: UUID,
    configs: list[EvalConfig],
    skip_generation_metrics: bool = False,
) -> list[EvalRunResult]:
    """Run evaluation with multiple config variants for A/B comparison.

    Args:
        dataset: Shared eval dataset.
        user_id: User whose documents to search.
        configs: List of config variants to compare.
        skip_generation_metrics: If True, skip LLM-as-judge.

    Returns:
        List of EvalRunResult, one per config.
    """
    results: list[EvalRunResult] = []
    for config in configs:
        logger.info("=== Running variant: %s ===", config.name)
        run_result = await run_eval(dataset, user_id, config, skip_generation_metrics)
        results.append(run_result)
    return results


def format_comparison_table(results: list[EvalRunResult]) -> str:
    """Format A/B comparison results as a markdown table."""
    lines: list[str] = []
    lines.append("# RAG Evaluation Results\n")

    headers = [
        "Config",
        "Precision@k",
        "Recall@k",
        "MRR",
        "Hit Rate",
        "Faithfulness",
        "Relevance",
        "Latency p50",
        "Latency p95",
        "Latency p99",
    ]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for r in results:
        row = [
            r.config_name,
            f"{r.retrieval.precision_at_k:.3f}",
            f"{r.retrieval.recall_at_k:.3f}",
            f"{r.retrieval.mrr:.3f}",
            f"{r.retrieval.hit_rate:.3f}",
            f"{r.generation.faithfulness:.3f}",
            f"{r.generation.answer_relevance:.3f}",
            f"{r.latency.p50:.0f}ms",
            f"{r.latency.p95:.0f}ms",
            f"{r.latency.p99:.0f}ms",
        ]
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append(f"*Samples per config: {results[0].sample_count if results else 0}*")
    return "\n".join(lines)
