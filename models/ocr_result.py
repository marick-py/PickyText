from dataclasses import dataclass


@dataclass
class OcrWord:
    text: str
    bbox: tuple[int, int, int, int]  # x, y, w, h — image pixel coordinates
    confidence: float                 # 0.0 – 1.0
    region_id: int                    # which selection region this word belongs to
