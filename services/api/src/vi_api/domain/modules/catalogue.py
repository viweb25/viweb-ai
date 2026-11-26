"""The product modules shown in the app menu.

Each module is one AI capability. ``available`` modules open in the app; ``coming_soon``
modules show what is planned. Enabling modules per organisation can later replace this
static list with a repository behind the same ListModules service.
"""

from dataclasses import dataclass, field
from typing import Literal

ModuleStatus = Literal["available", "coming_soon"]


@dataclass(frozen=True)
class ModuleSection:
    key: str
    name: str
    icon: str


@dataclass(frozen=True)
class Module:
    key: str
    name: str
    summary: str
    icon: str
    status: ModuleStatus
    sections: list[ModuleSection] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)


MODULES: tuple[Module, ...] = (
    Module(
        key="object-detection",
        name="Object detection",
        summary=(
            "Teach a model to find parts, then check boards zone by zone against a golden layout."
        ),
        icon="target",
        status="available",
        sections=[
            ModuleSection("guide", "Getting started", "help"),
            ModuleSection("projects", "Projects", "grid"),
            ModuleSection("programs", "Inspection programs", "layers"),
            ModuleSection("results", "Results and review", "flag"),
            ModuleSection("inspect", "Quick check", "inspect"),
        ],
        highlights=[
            "Label photos and train your own model",
            "Golden layout per zone with pass/fail rules",
            "Result log, human review and retraining loop",
        ],
    ),
    Module(
        key="anomaly-detection",
        name="Anomaly detection",
        summary=(
            "Learn from good boards only and flag anything unusual, including defects nobody "
            "labeled."
        ),
        icon="sparkle",
        status="coming_soon",
        highlights=[
            "Train on good boards only",
            "Heat map of where the board looks different",
            "Runs next to object detection in the same program",
        ],
    ),
    Module(
        key="electrical-test",
        name="Electrical testing",
        summary=(
            "Record continuity test results next to the vision result, so a wire is proven to "
            "make contact."
        ),
        icon="bolt",
        status="coming_soon",
        highlights=[
            "Import tester results per board serial number",
            "Combine vision and electrical result into one verdict",
        ],
    ),
    Module(
        key="predictive-maintenance",
        name="Predictive maintenance",
        summary="Watch machine sensor data and warn before a failure stops the line.",
        icon="clock",
        status="coming_soon",
        highlights=[
            "Connect sensor and PLC data",
            "Remaining-useful-life estimates",
            "Alerts before breakdowns",
        ],
    ),
    Module(
        key="ocr",
        name="Label and text reading",
        summary="Read serial numbers, part labels and date codes from camera images.",
        icon="tag",
        status="coming_soon",
        highlights=["Serial and batch numbers", "Check printed labels against the order"],
    ),
)
