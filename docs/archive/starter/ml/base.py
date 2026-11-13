"""Every AI function type is a plugin. Add a new type = new folder + subclass + register()."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class TrainContext:
    dataset_dir: Path            # frozen dataset version exported locally (e.g. COCO for detection)
    output_dir: Path             # where checkpoints, model files and report are written
    config: dict[str, Any]       # function config + training settings from the UI
    progress: Callable[[float, str], None] = lambda pct, msg: None
    should_cancel: Callable[[], bool] = lambda: False
    seed: int = 42


@dataclass
class TrainResult:
    model_path: Path
    metrics: dict[str, Any]
    extra_files: list[Path] = field(default_factory=list)


class FunctionPlugin(ABC):
    type: str = ""               # e.g. "object_detection"
    template_version: int = 1
    needs_training: bool = True  # False for functions usable with an existing model only

    def template(self) -> dict[str, Any]:
        """JSON Schema + UI schema shown by the Function Builder."""
        path = Path(__file__).parent / self.type / "template.json"
        return json.loads(path.read_text())

    @abstractmethod
    def predict(self, image: np.ndarray, config: dict[str, Any], model: Any | None = None) -> dict[str, Any]:
        """Return a result that validates against contracts/results/<type>.schema.json."""

    def load_model(self, model_path: Path | None, config: dict[str, Any]) -> Any:
        return None

    def train(self, ctx: TrainContext) -> TrainResult:
        raise NotImplementedError(f"{self.type} does not support training yet")

    def evaluate(self, model: Any, dataset_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


REGISTRY: dict[str, FunctionPlugin] = {}


def register(cls: type[FunctionPlugin]) -> type[FunctionPlugin]:
    REGISTRY[cls.type] = cls()
    return cls
