"""CLI entry point: python -m app.eval.run

Usage:
    python -m app.eval.run --dataset eval_data.json --user-id <uuid>
    python -m app.eval.run --dataset eval_data.json --user-id <uuid> --configs baseline +reranker
    python -m app.eval.run --dataset eval_data.json --user-id <uuid> --skip-generation
    python -m app.eval.run --dataset eval_data.json --user-id <uuid> --output results.md
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

from app.eval.configs import ALL_CONFIGS, BASELINE, WITH_ALL, WITH_HYDE, WITH_RERANKER
from app.eval.dataset import EvalDataset
from app.eval.runner import EvalConfig, format_comparison_table, run_ab_comparison

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG_MAP: dict[str, EvalConfig] = {
    "baseline": BASELINE,
    "+reranker": WITH_RERANKER,
    "+hyde": WITH_HYDE,
    "+reranker+hyde": WITH_ALL,
    "+all": WITH_ALL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG Evaluation Pipeline — compare retrieval configs"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to eval dataset JSON file",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="UUID of the user whose documents to evaluate against",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=None,
        help="Config variants to test (default: all). Options: baseline, +reranker, +hyde, +all",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Skip LLM-as-judge generation metrics (faster)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output markdown file path (prints to stdout if omitted)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k results to evaluate (default: 5)",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.7,
        help="Minimum similarity score threshold (default: 0.7)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("Dataset file not found: %s", dataset_path)
        sys.exit(1)

    dataset = EvalDataset.from_json(dataset_path)
    logger.info("Loaded dataset: %s (%d samples)", dataset.name, len(dataset))

    user_id = UUID(args.user_id)

    if args.configs:
        configs = []
        for name in args.configs:
            if name not in CONFIG_MAP:
                logger.error("Unknown config: %s. Available: %s", name, list(CONFIG_MAP.keys()))
                sys.exit(1)
            configs.append(CONFIG_MAP[name])
    else:
        configs = list(ALL_CONFIGS)

    for config in configs:
        config.top_k = args.top_k
        config.score_threshold = args.score_threshold

    results = await run_ab_comparison(
        dataset=dataset,
        user_id=user_id,
        configs=configs,
        skip_generation_metrics=args.skip_generation,
    )

    table = format_comparison_table(results)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(table)
        logger.info("Results written to: %s", output_path)
    else:
        print(table)


if __name__ == "__main__":
    asyncio.run(main())
