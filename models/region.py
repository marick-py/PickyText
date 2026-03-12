from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from models.ocr_result import OcrWord


class RegionShape(Enum):
    RECT = "rect"
    POLYGON = "polygon"


@dataclass
class Region:
    id: int
    shape: RegionShape
    # RECT:    (x, y, w, h) in image pixel coordinates
    # POLYGON: list of (x, y) tuples in image pixel coordinates
    geometry: tuple | list
    label: str = ""
    ocr_words: list[OcrWord] = field(default_factory=list)
    translation: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.label:
            self.label = f"Region {self.id}"
