from __future__ import annotations

import re
from dataclasses import dataclass
import base64
from io import BytesIO
from os import getenv
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from models.schemas import ArtworkResponse, Player


@dataclass
class ArtworkGeneratorService:
    static_root: Path = Path("static")
    stable_diffusion_url: str | None = getenv("STABLE_DIFFUSION_API_URL")
    gemini_api_key: str | None = getenv("GEMINI_API_KEY")
    gemini_model: str = getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-001")
    timeout: int = 45

    def __post_init__(self) -> None:
        self.artwork_dir = self.static_root / "artwork"
        self.template_dir = self.static_root / "templates"
        self.artwork_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        team_name: str,
        logo_path: str | None,
        team_colors: list[str],
        players: list[Player] | None = None,
    ) -> ArtworkResponse:
        slug = self._slugify(team_name)
        
        provider = "Google Gemini (Nano Banana)"
        model = self.gemini_model
        prompt = self._build_prompt(team_name, team_colors)
        
        # 1. Generate 4:3 Artwork
        base_4x3 = self._generate_with_gemini(prompt, aspect_ratio="4:3")
        if base_4x3 is None:
            base_4x3 = self._generate_with_pollinations(prompt, width=1600, height=1200)
            if base_4x3 is not None:
                provider = "Pollinations.ai (Flux Model)"
                model = "flux"
                base_4x3 = self._add_overlays(base_4x3, team_name, logo_path, team_colors, players)
        else:
            base_4x3 = base_4x3.resize((1600, 1200), Image.Resampling.LANCZOS)
            base_4x3 = self._add_overlays(base_4x3, team_name, logo_path, team_colors, players)
            
        if base_4x3 is None:
            base_4x3 = self._fallback_artwork(team_name, logo_path, team_colors, players, width=1600, height=1200)
            provider = "PIL fallback composer"
            model = "local composer"
            
        # 2. Generate 16:9 Artwork
        base_16x9 = self._generate_with_gemini(prompt, aspect_ratio="16:9")
        if base_16x9 is None:
            base_16x9 = self._generate_with_pollinations(prompt, width=1920, height=1080)
            if base_16x9 is not None:
                if provider != "PIL fallback composer":
                    provider = "Pollinations.ai (Flux Model)"
                    model = "flux"
                base_16x9 = self._add_overlays(base_16x9, team_name, logo_path, team_colors, players)
        else:
            base_16x9 = base_16x9.resize((1920, 1080), Image.Resampling.LANCZOS)
            base_16x9 = self._add_overlays(base_16x9, team_name, logo_path, team_colors, players)

        if base_16x9 is None:
            base_16x9 = self._fallback_artwork(team_name, logo_path, team_colors, players, width=1920, height=1080)
            provider = "PIL fallback composer"
            model = "local composer"

        base_4x3 = self._enforce_color_tint(base_4x3, team_colors)
        base_16x9 = self._enforce_color_tint(base_16x9, team_colors)
        
        poster_path = self.artwork_dir / f"{slug}-poster.png"
        thumbnail_path = self.artwork_dir / f"{slug}-thumbnail.png"
        
        base_4x3.save(poster_path)
        base_16x9.save(thumbnail_path)

        return ArtworkResponse(
            thumbnail=f"/static/artwork/{thumbnail_path.name}",
            poster=f"/static/artwork/{poster_path.name}",
            variants=[],
            provider=provider,
            model=model,
            prompt=prompt,
        )

    def build_artwork(self, team_name: str, validation, players, logo_bytes: bytes | None) -> ArtworkResponse:
        colors = self._colors_from_validation(validation)
        logo_path = validation.matched_sources[0] if validation and validation.matched_sources else None
        return self.generate(team_name, logo_path, colors, players.players if hasattr(players, "players") else players)

    def _compose_from_template(
        self,
        team_name: str,
        logo_path: str | None,
        team_colors: list[str],
        players: list[Player] | None,
    ) -> Image.Image | None:
        template_path = self.template_dir / f"{self._slugify(team_name)}.png"
        if not template_path.exists():
            return None
        image = Image.open(template_path).convert("RGBA").resize((1600, 1200), Image.Resampling.LANCZOS)
        return self._add_overlays(image, team_name, logo_path, team_colors, players)

    def _generate_with_gemini(self, prompt: str, aspect_ratio: str = "4:3") -> Image.Image | None:
        if not self.gemini_api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:predict"
        try:
            response = requests.post(
                url,
                headers={"x-goog-api-key": self.gemini_api_key, "Content-Type": "application/json"},
                json={
                    "instances": [{"prompt": prompt}],
                    "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio}
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            for prediction in payload.get("predictions", []):
                b64 = prediction.get("bytesBase64Encoded")
                if b64:
                    return Image.open(BytesIO(base64.b64decode(b64))).convert("RGBA")
            return None
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None

    def _generate_with_pollinations(self, prompt: str, width: int = 1600, height: int = 1200) -> Image.Image | None:
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&enhance=true&model=flux"
        try:
            # Increase timeout to 80 for Pollinations image generation
            response = requests.get(url, timeout=80)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            print(f"Pollinations API Error: {e}")
            return None

    def _fallback_artwork(
        self,
        team_name: str,
        logo_path: str | None,
        team_colors: list[str],
        players: list[Player] | None,
        width: int = 1600,
        height: int = 1200
    ) -> Image.Image:
        primary = self._hex_to_rgb(team_colors[0] if team_colors else "#1F2937")
        secondary = self._hex_to_rgb(team_colors[1] if len(team_colors) > 1 else "#0EA5E9")
        image = Image.new("RGBA", (width, height), primary + (255,))
        draw = ImageDraw.Draw(image)
        for y in range(0, height, 12):
            ratio = y / height
            color = tuple(int(primary[i] * (1 - ratio) + secondary[i] * ratio) for i in range(3))
            draw.rectangle((0, y, width, y + 12), fill=color + (255,))
        for x in range(-300, width + 200, 180):
            draw.line((x, 0, x + (height * 0.75), height), fill=(255, 255, 255, 24), width=8)
        return self._add_overlays(image, team_name, logo_path, team_colors, players)

    def _add_overlays(
        self,
        image: Image.Image,
        team_name: str,
        logo_path: str | None,
        team_colors: list[str],
        players: list[Player] | None,
    ) -> Image.Image:
        width, height = image.size
        image = image.convert("RGBA")
        draw = ImageDraw.Draw(image)
        font_large = self._font(100)
        font_medium = self._font(40)
        font_small = self._font(28)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for y_offset in range(600):
            alpha = int((y_offset / 600) * 220)
            overlay_draw.line((0, height - 600 + y_offset, width, height - 600 + y_offset), fill=(0, 0, 0, alpha))
            
        image.alpha_composite(overlay)

        self._draw_wrapped_text(draw, team_name.upper(), (80, height - 520), font_large, width - 160, (255, 255, 255, 255))
        draw.text((86, height - 380), "DYNAMIC SPORTS POSTER", fill=(235, 245, 255, 230), font=font_medium)
        for index, color in enumerate(team_colors[:5]):
            draw.rounded_rectangle((86 + index * 70, height - 310, 146 + index * 70, height - 250), radius=15, fill=self._hex_to_rgb(color) + (255,))

        logo = self._load_logo(logo_path)
        if logo:
            logo.thumbnail((400, 400), Image.Resampling.LANCZOS)
            plate = Image.new("RGBA", (480, 480), (255, 255, 255, 200))
            plate_draw = ImageDraw.Draw(plate)
            plate_draw.ellipse((0, 0, 480, 480), fill=(255, 255, 255, 200))
            
            logo_offset_x = (480 - logo.width) // 2
            logo_offset_y = (480 - logo.height) // 2
            if logo.mode == "RGBA":
                plate.paste(logo, (logo_offset_x, logo_offset_y), logo)
            else:
                plate.paste(logo, (logo_offset_x, logo_offset_y))
                
            image.alpha_composite(plate, (width - 550, 100))

        if players:
            headshot_x = 86
            headshot_y = height - 220
            rendered_players = 0
            for player in players:
                if rendered_players >= 5:
                    break
                if player.image_url:
                    headshot = self._load_logo(player.image_url)
                    if headshot:
                        headshot_size = 140
                        headshot.thumbnail((headshot_size, headshot_size), Image.Resampling.LANCZOS)
                        
                        mask = Image.new("L", headshot.size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, headshot.width, headshot.height), fill=255)
                        
                        border_size = headshot_size + 12
                        plate = Image.new("RGBA", (border_size, border_size), (0,0,0,0))
                        plate_draw = ImageDraw.Draw(plate)
                        plate_draw.ellipse((0, 0, border_size, border_size), fill=self._hex_to_rgb(team_colors[0] if team_colors else "#0EA5E9") + (255,))
                        
                        offset_x = (border_size - headshot.width) // 2
                        offset_y = (border_size - headshot.height) // 2
                        plate.paste(headshot, (offset_x, offset_y), mask)
                        
                        image.alpha_composite(plate, (headshot_x, headshot_y))
                        headshot_x += border_size + 20
                        rendered_players += 1
            
            names = " / ".join(player.name for player in players[:5])
            self._draw_wrapped_text(draw, names, (86, height - 60), font_small, width - 160, (255, 255, 255, 220))
        return image

    def _load_logo(self, logo_path: str | None) -> Image.Image | None:
        if not logo_path:
            return None
        try:
            if logo_path.startswith("http"):
                response = requests.get(logo_path, timeout=12)
                response.raise_for_status()
                return Image.open(BytesIO(response.content)).convert("RGBA")
            path = Path(logo_path.lstrip("/"))
            if path.exists():
                return Image.open(path).convert("RGBA")
        except Exception:
            return None
        return None

    def _enforce_color_tint(self, image: Image.Image, team_colors: list[str]) -> Image.Image:
        if not team_colors:
            return image
        tint = Image.new("RGBA", image.size, self._hex_to_rgb(team_colors[0]) + (52,))
        blended = Image.alpha_composite(image.convert("RGBA"), tint)
        return ImageEnhance.Color(blended).enhance(1.08)

    def _create_slices(self, image: Image.Image, slug: str) -> list[Image.Image]:
        width, height = image.size
        return [
            image.crop((0, 0, width, height // 2)),
            image.crop((0, height // 4, width, (height // 4) + (height // 2))),
            image.crop((0, height // 2, width, height)),
        ]

    def _resize_cover(self, image: Image.Image, size: tuple[int, int]) -> Image.Image:
        target_w, target_h = size
        scale = max(target_w / image.width, target_h / image.height)
        resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
        left = (resized.width - target_w) // 2
        top = (resized.height - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))

    def _colors_from_validation(self, validation) -> list[str]:
        return getattr(validation, "dominant_colors", None) or ["#1F2937", "#0EA5E9", "#F8FAFC"]

    def _build_prompt(self, team_name: str, team_colors: list[str]) -> str:
        color_str = ", ".join(team_colors) if team_colors else "their iconic colors"
        return (
            f"Create an epic, hyper-realistic sports thumbnail and poster background representing {team_name}. "
            f"Use the team's primary colors ({color_str}) prominently. "
            "The artwork should have the look of a premium, high-budget sports broadcast graphic with cinematic stadium lighting, "
            "dynamic and bold composition, dramatic shadows, glowing neon accents, and intense energy. "
            "Include a visually striking team crest or thematic element in the background. "
            "Do NOT include any text or distorted letters. Leave ample empty space at the bottom and sides for text overlays. "
            "The image must be highly detailed, 8k resolution, photorealistic, and ready for use as a background."
        )

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for name in ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _draw_wrapped_text(self, draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font, max_width: int, fill) -> None:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        x, y = xy
        for line in lines:
            draw.text((x, y), line, fill=fill, font=font)
            y += int(font.size * 1.05) if hasattr(font, "size") else 34

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        color = color.lstrip("#")
        if len(color) != 6:
            return (31, 41, 55)
        return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "team"
