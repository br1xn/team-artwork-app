from __future__ import annotations

import io
from dataclasses import dataclass, field

import requests
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from models.schemas import LogoSource


@dataclass
class ClipSimilarityService:
    model_name: str = "openai/clip-vit-base-patch32"
    processor: CLIPProcessor | None = field(default=None, init=False)
    model: CLIPModel | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        try:
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
        except Exception:
            self.processor = None
            self.model = None

    def compare_against_sources(self, logo_bytes: bytes, sources: list[LogoSource]) -> float:
        if not sources:
            return 0.0
        if not self.processor or not self.model:
            return 0.5

        input_image = Image.open(io.BytesIO(logo_bytes)).convert("RGB")
        best_score = 0.0

        for source in sources:
            try:
                response = requests.get(source.url, timeout=15)
                response.raise_for_status()
                source_image = Image.open(io.BytesIO(response.content)).convert("RGB")
                inputs = self.processor(images=[input_image, source_image], return_tensors="pt")
                image_features = self.model.get_image_features(**inputs)
                input_vec = image_features[0]
                source_vec = image_features[1]
                score = torch.nn.functional.cosine_similarity(input_vec.unsqueeze(0), source_vec.unsqueeze(0)).item()
                best_score = max(best_score, float(score))
            except Exception:
                continue
        return best_score
