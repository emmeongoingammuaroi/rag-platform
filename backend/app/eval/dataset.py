"""Evaluation dataset loader and models."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class EvalSample(BaseModel):
    """A single evaluation sample."""

    query: str
    expected_answer: str
    relevant_chunk_ids: list[str] = []
    metadata: dict[str, Any] = {}


class EvalDataset(BaseModel):
    """Collection of evaluation samples."""

    name: str
    description: str = ""
    samples: list[EvalSample]

    @classmethod
    def from_json(cls, path: str | Path) -> "EvalDataset":
        """Load dataset from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def __len__(self) -> int:
        return len(self.samples)
