"""Predefined A/B config variants for evaluation."""

from app.eval.runner import EvalConfig

BASELINE = EvalConfig(
    name="baseline",
    reranker_enabled=False,
    hyde_enabled=False,
    description="Vanilla retrieval: embed query → vector search → top-k",
)

WITH_RERANKER = EvalConfig(
    name="+reranker",
    reranker_enabled=True,
    hyde_enabled=False,
    description="Two-stage: vector search top-20 → cross-encoder rerank → top-5",
)

WITH_HYDE = EvalConfig(
    name="+hyde",
    reranker_enabled=False,
    hyde_enabled=True,
    description="HyDE: generate hypothetical answer → embed that → vector search",
)

WITH_ALL = EvalConfig(
    name="+reranker+hyde",
    reranker_enabled=True,
    hyde_enabled=True,
    description="Full pipeline: HyDE expand → vector search top-20 → rerank → top-5",
)

ALL_CONFIGS = [BASELINE, WITH_RERANKER, WITH_HYDE, WITH_ALL]
