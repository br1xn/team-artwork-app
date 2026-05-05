from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urljoin, urlparse

import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

from models.schemas import LogoSource, LogoValidationRequest, LogoValidationResponse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

TRUSTED_DOMAINS = [
    "nfl.com",
    "espn.com",
    "sports.yahoo.com",
    "cbssports.com",
    "wikipedia.org",
    "wikimedia.org",
    "iplt20.com",
    "espncricinfo.com",
    "cricbuzz.com"
]

@dataclass
class LogoValidator:
    timeout: int = 10
    model_name: str = "openai/clip-vit-base-patch32"
    valid_threshold: float = 0.58
    validation_provider: str = "Hugging Face Transformers CLIP"

    def __post_init__(self) -> None:
        self.torch = None
        self.processor = None
        self.model = None
        self._model_load_attempted = False

    def validate(
        self,
        payload: LogoValidationRequest,
        logo_bytes: bytes | None,
        filename: str | None = None,
    ) -> LogoValidationResponse:
        return self.validate_from_inputs(payload.team_name, logo_bytes, filename)

    def validate_from_inputs(
        self,
        team_name: str,
        logo_bytes: bytes | None,
        filename: str | None = None,
    ) -> LogoValidationResponse:
        team = team_name.strip()
        if not team:
            raise ValueError("Team name is required.")
        
        if not logo_bytes:
            return LogoValidationResponse(
                team=team,
                confidence=1.0,
                status="valid",
                matched_sources=[],
                color_match=1.0,
                visual_match=1.0,
                sources_checked=[],
                uploaded_filename=filename,
            )

        try:
            input_image = self._load_image(logo_bytes)
        except UnidentifiedImageError as exc:
            raise ValueError("Uploaded logo is corrupt or not a supported image.") from exc

        candidate_sources = self.fetch_candidate_logos(team)
        if not candidate_sources:
            return LogoValidationResponse(
                team=team,
                confidence=0.05,
                status="invalid",
                matched_sources=[],
                color_match=0.0,
                visual_match=0.0,
                sources_checked=[],
                candidate_sources=[],
                uploaded_filename=filename,
                error="No trusted candidate logos found.",
                validation_evidence=f"No online sources from trusted domains ({', '.join(TRUSTED_DOMAINS[:3])}...) could be found to validate the logo against.",
                dominant_colors=[],
            )

        input_palette = self.extract_dominant_colors(input_image)
        input_embedding = self._embed_image(input_image)

        scored_candidates = []

        # Evaluate and score EVERY candidate source
        for source in candidate_sources:
            candidate_bytes = self._download_image(source.url)
            if not candidate_bytes:
                continue
            try:
                candidate_image = self._load_image(candidate_bytes)
            except UnidentifiedImageError:
                continue

            visual = self._visual_similarity(input_embedding, candidate_image)
            color = self._color_similarity(input_palette, self.extract_dominant_colors(candidate_image))
            
            combined_score = (0.7 * visual) + (0.3 * color)
            
            scored_candidates.append({
                "url": source.url,
                "visual": visual,
                "color": color,
                "score": combined_score,
                "provider": source.provider
            })

        # Sort all candidates by their combined score, highest first
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)

        if not scored_candidates:
            return LogoValidationResponse(
                team=team,
                confidence=0.05,
                status="invalid",
                matched_sources=[],
                color_match=0.0,
                visual_match=0.0,
                sources_checked=[s.url for s in candidate_sources],
                candidate_sources=candidate_sources,
                uploaded_filename=filename,
                error="Failed to process candidate images.",
                validation_evidence="Trusted sources were found, but the image processing pipeline failed to parse them.",
                dominant_colors=self._palette_to_hex(input_palette),
            )

        # Slice the Top 3 strongest matches
        top_sources = scored_candidates[:3]
        best_match = top_sources[0]
        
        confidence = round(best_match["score"], 4)
        is_valid = confidence >= self.valid_threshold
        
        # Keep up to 3 sources for the frontend display
        matched_sources = [m["url"] for m in top_sources]

        evidence = (
            f"Validated using {self.model_name} via {self.validation_provider}. "
            f"Achieved a primary confidence score of {confidence * 100:.2f}%. "
            f"Cross-referenced and ranked against {len(matched_sources)} highly correlated trusted sources (Top Match: {best_match['provider']}). "
            f"Top visual similarity contributed {(best_match['visual'] * 0.7 * 100):.1f}% and color contributed {(best_match['color'] * 0.3 * 100):.1f}%."
        )
        
        return LogoValidationResponse(
            team=team,
            confidence=confidence,
            status="valid" if is_valid else "invalid",
            matched_sources=matched_sources,
            color_match=round(best_match["color"], 4),
            visual_match=round(best_match["visual"], 4),
            sources_checked=[source.url for source in candidate_sources],
            candidate_sources=candidate_sources,
            uploaded_filename=filename,
            validation_evidence=evidence,
            dominant_colors=self._palette_to_hex(input_palette),
        )

    def fetch_candidate_logos(self, team_name: str) -> list[LogoSource]:
        sources = []
        sources.extend(self._fetch_wikipedia_logos(team_name))
        sources.extend(self._fetch_google_image_logos(team_name))
        return self._dedupe_sources(sources)

    def _is_valid_logo_url(self, url: str) -> bool:
        if not url: return False
        
        # 1. Enforce Trusted Domains
        domain = urlparse(url).netloc.lower()
        is_trusted = any(trusted in domain for trusted in TRUSTED_DOMAINS)
        
        # CDN exceptions for sports sites
        cdn_exceptions = ["espncdn.com", "turner.com", "wikimedia.org", "wimg.co.uk"]
        is_trusted = is_trusted or any(cdn in domain for cdn in cdn_exceptions)

        if not is_trusted:
            return False

        lower_url = url.lower()
        
        # 2. Filter out non-logo items AND Wikipedia UI icons
        invalid_keywords = [
            'kit', 'body', 'shorts', 'uniform', 'cap', 'jersey', 'shoe', 'socks', 'stadium', 'fans',
            'current_event', 'portal', 'icon', 'stub', 'edit_ambox', 'question_mark'
        ]
        if any(kw in lower_url for kw in invalid_keywords):
            return False
            
        # 3. Filter out tiny Wikipedia thumbnails (e.g., /40px-)
        if re.search(r'/[1-9][0-9]?px-', lower_url):
            return False

        return True

    def _fetch_wikipedia_logos(self, team_name: str) -> list[LogoSource]:
        page_url = f"https://en.wikipedia.org/wiki/{quote_plus(team_name.replace(' ', '_'))}"
        soup = self._get_soup(page_url)
        if not soup:
            return []
        
        sources = []
        for img in soup.select(".infobox img"):
            src = img.get("src")
            abs_url = self._absolute_url(src, "https://en.wikipedia.org")
            if src and self._is_valid_logo_url(abs_url):
                alt_text = img.get("alt") or team_name
                if "logo" in alt_text.lower() or "crest" in alt_text.lower() or "logo" in src.lower():
                    sources.insert(0, LogoSource(provider="Wikipedia", url=abs_url, label=alt_text))
                else:
                    sources.append(LogoSource(provider="Wikipedia", url=abs_url, label=alt_text))
                if len(sources) >= 5:
                    break
        return sources

    def _fetch_google_image_logos(self, team_name: str) -> list[LogoSource]:
        # Force Google to only pull from our trusted domains
        site_query = " OR ".join([f"site:{domain}" for domain in TRUSTED_DOMAINS[:6]])
        query = quote_plus(f"{team_name} logo ({site_query})")
        url = f"https://www.google.com/search?tbm=isch&q={query}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException:
            return []
            
        matches = re.findall(r'"(https?://[^"]+\.(?:png|jpg|jpeg|webp))"', response.text)
        sources = []
        for match in matches:
            clean_url = match.replace("\\u003d", "=")
            if self._is_valid_logo_url(clean_url):
                sources.append(LogoSource(provider="Google Images (Trusted)", url=clean_url, label=f"{team_name} logo"))
                
        return sources[:8]

    def extract_dominant_colors(self, image: Image.Image, color_count: int = 5) -> list[tuple[int, int, int]]:
        prepared = self._preprocess_image(image).convert("RGB")
        pixels = np.float32(np.array(prepared).reshape((-1, 3)))
        color_count = max(3, min(color_count, 5, len(pixels)))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.2)
        _, labels, centers = cv2.kmeans(pixels, color_count, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(labels.flatten())
        ordered = centers[np.argsort(counts)[::-1]]
        return [tuple(int(channel) for channel in color) for color in ordered]

    def _load_image(self, image_bytes: bytes) -> Image.Image:
        return self._preprocess_image(Image.open(io.BytesIO(image_bytes)).convert("RGBA"))

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA")
        width, height = image.size
        if width < 224 or height < 224:
            scale = max(224 / width, 224 / height)
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        offset = ((512 - image.width) // 2, (512 - image.height) // 2)
        canvas.alpha_composite(image, offset)
        return canvas

    def _embed_image(self, image: Image.Image):
        self._ensure_model()
        if not self.processor or not self.model or not self.torch:
            return None
        inputs = self.processor(images=image.convert("RGB"), return_tensors="pt")
        with self.torch.no_grad():
            embedding = self.model.get_image_features(**inputs)
        return self.torch.nn.functional.normalize(embedding, dim=-1)

    def _visual_similarity(self, input_embedding, candidate_image: Image.Image) -> float:
        if input_embedding is None:
            return 0.5
        candidate_embedding = self._embed_image(candidate_image)
        if candidate_embedding is None:
            return 0.5
        score = self.torch.nn.functional.cosine_similarity(input_embedding, candidate_embedding).item()
        return max(0.0, min(1.0, (score + 1.0) / 2.0))

    def _ensure_model(self) -> None:
        if self._model_load_attempted:
            return
        self._model_load_attempted = True
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            self.torch = torch
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.model.eval()
        except Exception as e:
            print(f"Failed to load CLIP model: {e}")
            self.torch = None
            self.processor = None
            self.model = None

    def _color_similarity(self, input_palette: list[tuple[int, int, int]], candidate_palette: list[tuple[int, int, int]]) -> float:
        if not input_palette or not candidate_palette:
            return 0.0
        max_distance = np.sqrt(3 * (255**2))
        scores = []
        for input_color in input_palette:
            distances = [np.linalg.norm(np.array(input_color) - np.array(candidate_color)) for candidate_color in candidate_palette]
            scores.append(1.0 - (min(distances) / max_distance))
        return max(0.0, min(1.0, float(np.mean(scores))))

    def _palette_to_hex(self, palette: list[tuple[int, int, int]]) -> list[str]:
        return [f"#{red:02X}{green:02X}{blue:02X}" for red, green, blue in palette[:5]]

    def _download_image(self, url: str) -> bytes | None:
        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                return None
            return response.content
        except requests.RequestException:
            return None

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        try:
            response = requests.get(url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException:
            return None

    def _absolute_url(self, src: str | None, base: str) -> str:
        if not src:
            return ""
        if src.startswith("//"):
            return f"https:{src}"
        return urljoin(base, src)

    def _dedupe_sources(self, sources: list[LogoSource]) -> list[LogoSource]:
        seen = set()
        unique = []
        for source in sources:
            if source.url and source.url not in seen:
                seen.add(source.url)
                unique.append(source)
        return unique[:12]