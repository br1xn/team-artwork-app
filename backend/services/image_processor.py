from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

from models.schemas import Player


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


@dataclass
class ImageProcessor:
    static_root: Path = Path("static")
    output_size: int = 256
    timeout: int = 10

    def __post_init__(self) -> None:
        self.headshot_dir = self.static_root / "headshots"
        self.headshot_dir.mkdir(parents=True, exist_ok=True)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_detector = cv2.CascadeClassifier(cascade_path)

    def process_headshots(self, players: list[Player]) -> list[Player]:
        processed = []
        for player in players:
            path = self.process_player_image(player)
            processed.append(
                Player(
                    name=player.name,
                    role=player.role,
                    image_url=player.image_url,
                    processed_image_path=path,
                    source=player.source,
                )
            )
        return processed

    def process_player_image(self, player: Player) -> str:
        image = self._download_player_image(player.image_url) if player.image_url else None
        if image is None:
            image = self._placeholder_image()
        else:
            image = self._crop_face_or_center(image)
        image = self._make_circular_rgba(image)

        filename = f"{self._slugify(player.name)}.png"
        path = self.headshot_dir / filename
        image.save(path)
        return f"/static/headshots/{filename}"

    def prepare_logo_variants(self, logo_bytes: bytes | None) -> list[str]:
        if not logo_bytes:
            return []
        logo_dir = self.static_root / "logos"
        logo_dir.mkdir(parents=True, exist_ok=True)
        raw_path = logo_dir / "uploaded-logo.png"
        processed_path = logo_dir / "uploaded-logo-512.png"
        raw_path.write_bytes(logo_bytes)

        array = np.frombuffer(logo_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
        if image is None:
            return []
        resized = cv2.resize(image, (512, 512), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(processed_path), resized)
        return ["/static/logos/uploaded-logo.png", "/static/logos/uploaded-logo-512.png"]

    def _download_player_image(self, image_url: str | None) -> Image.Image | None:
        if not image_url:
            return None
        try:
            response = requests.get(image_url, headers=HEADERS, timeout=self.timeout)
            response.raise_for_status()
            if "image" not in response.headers.get("content-type", ""):
                return None
            from io import BytesIO
            return Image.open(BytesIO(response.content)).convert("RGB")
        except Exception:
            return None

    def _crop_face_or_center(self, image: Image.Image) -> Image.Image:
        rgb = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
            padding = int(max(w, h) * 0.45)
            left = max(0, x - padding)
            top = max(0, y - padding)
            right = min(image.width, x + w + padding)
            bottom = min(image.height, y + h + padding)
            crop = image.crop((left, top, right, bottom))
        else:
            side = min(image.width, image.height)
            left = (image.width - side) // 2
            top = (image.height - side) // 2
            crop = image.crop((left, top, left + side, top + side))
        return crop.resize((self.output_size, self.output_size), Image.Resampling.LANCZOS)

    def _make_circular_rgba(self, image: Image.Image) -> Image.Image:
        image = image.convert("RGBA").resize((self.output_size, self.output_size), Image.Resampling.LANCZOS)
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.output_size - 1, self.output_size - 1), fill=255)
        output = Image.new("RGBA", image.size, (0, 0, 0, 0))
        output.paste(image, (0, 0), mask)
        return output

    def _placeholder_image(self) -> Image.Image:
        image = Image.new("RGBA", (self.output_size, self.output_size), (31, 41, 55, 255))
        draw = ImageDraw.Draw(image)
        text = "No Image\nAvailable"
        font = ImageFont.load_default()
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=8, align="center")
        x = (self.output_size - (bbox[2] - bbox[0])) / 2
        y = (self.output_size - (bbox[3] - bbox[1])) / 2
        draw.multiline_text((x, y), text, fill=(248, 250, 252, 255), font=font, spacing=8, align="center")
        return image

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "player"
