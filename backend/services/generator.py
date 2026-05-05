from __future__ import annotations

import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import requests
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from models.schemas import ArtworkResponse, Player


@dataclass
class ArtworkGeneratorService:
    static_root: Path = Path("static")
    timeout: int = 30

    def __post_init__(self) -> None:
        self.artwork_dir = self.static_root / "artwork"
        self.artwork_dir.mkdir(parents=True, exist_ok=True)
        
        self.figma_token = os.getenv("FIGMA_TOKEN")
        self.figma_file_key = os.getenv("FIGMA_FILE_KEY")
        self.node_16x9 = os.getenv("FIGMA_NODE_16X9")
        self.node_4x3 = os.getenv("FIGMA_NODE_4X3")

    def generate(
        self,
        team_name: str,
        logo_path: str | None,
        team_colors: list[str],
        players: list[Player] | None = None,
    ) -> ArtworkResponse:
        slug = self._slugify(team_name)
        
        # 1. Fetch pristine base layouts from Figma
        base_16x9 = self._fetch_from_figma(self.node_16x9) or self._fallback_background(1920, 1080)
        base_4x3 = self._fetch_from_figma(self.node_4x3) or self._fallback_background(1600, 1200)

        # 2. Extract Primary Team Color
        primary_hex = team_colors[0] if team_colors else "#0EA5E9"
        
        # 3. Process & Composite 16:9
        final_16x9 = self._composite_artwork(base_16x9, logo_path, primary_hex, team_name)
        poster_path = self.artwork_dir / f"{slug}-16x9.png"
        final_16x9.save(poster_path)
        
        # 4. Process & Composite 4:3
        final_4x3 = self._composite_artwork(base_4x3, logo_path, primary_hex, team_name)
        thumbnail_path = self.artwork_dir / f"{slug}-4x3.png"
        final_4x3.save(thumbnail_path)

        return ArtworkResponse(
            poster=f"/static/artwork/{poster_path.name}",
            thumbnail=f"/static/artwork/{thumbnail_path.name}",
            variants=[],
            provider="Figma Generator",
            model="PIL Compositor",
            prompt="Success",
        )

    def _fetch_from_figma(self, node_id: str | None) -> Image.Image | None:
        if not self.figma_token or not self.figma_file_key or not node_id:
            print("!!! FIGMA API WARNING: Missing credentials in .env file. Using fallback background. !!!")
            return None
            
        url = f"https://api.figma.com/v1/images/{self.figma_file_key}?ids={node_id}&format=png&scale=1"
        headers = {"X-Figma-Token": self.figma_token}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            image_url = data.get("images", {}).get(node_id)
            if not image_url:
                print(f"!!! FIGMA API WARNING: Node ID {node_id} not found in file. Check your Node IDs! !!!")
                return None
                
            img_response = requests.get(image_url, timeout=self.timeout)
            img_response.raise_for_status()
            return Image.open(BytesIO(img_response.content)).convert("RGBA")
        except Exception as e:
            print(f"!!! FIGMA API FAILED: {e} !!!")
            return None

    def _composite_artwork(self, base_image: Image.Image, logo_path: str | None, hex_color: str, team_name: str) -> Image.Image:
        width, height = base_image.size
        base_image = base_image.convert("RGBA")
        
        # Enhance base contrast
        darker = ImageEnhance.Brightness(base_image).enhance(0.5)
        contrasty = ImageEnhance.Contrast(darker).enhance(1.2).convert("RGB")
        
        # Multiply Blend
        rgb_color = self._hex_to_rgb(hex_color)
        color_layer = Image.new("RGB", (width, height), rgb_color)
        tinted = ImageChops.multiply(contrasty, color_layer)
        composited = Image.blend(contrasty, tinted, alpha=0.75).convert("RGBA")

        # Overlay Team Logo
        logo = self._load_logo(logo_path)
        if logo:
            logo = self._remove_solid_background(logo)
            
            # Scale logo
            target_height = int(height * 0.35)
            scale = target_height / logo.height
            logo = logo.resize((int(logo.width * scale), target_height), Image.Resampling.LANCZOS)
            
            # Position: Shifted left and pushed DOWN to 45% of the screen height
            offset_x = int(width * 0.10)
            offset_y = int(height * 0.45)
            
            # Drop shadow
            shadow = logo.copy().convert("RGBA")
            shadow_data = shadow.load()
            for y in range(shadow.height):
                for x in range(shadow.width):
                    if shadow_data[x, y][3] > 0:
                        shadow_data[x, y] = (0, 0, 0, 220)
            shadow = shadow.filter(ImageFilter.GaussianBlur(20))
            
            composited.alpha_composite(shadow, (offset_x + 5, offset_y + 15))
            composited.alpha_composite(logo, (offset_x, offset_y))

            # Team Name underneath logo
            draw = ImageDraw.Draw(composited)
            font_size = int(height * 0.055)
            font = self._get_anton_font(font_size)
            team_text = team_name.upper()
            
            # Tight spacing: Just a tiny gap between the logo and the text
            bbox = draw.textbbox((0, 0), team_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = offset_x + (logo.width // 2) - (text_w // 2)
            text_y = offset_y + logo.height + int(height * 0.015) 
            
            # Outline
            for dx in [-2, -1, 1, 2]:
                for dy in [-2, -1, 1, 2]:
                    draw.text((text_x + dx, text_y + dy), team_text, font=font, fill=(0, 0, 0, 255))
                    
            draw.text((text_x, text_y), team_text, font=font, fill=(255, 255, 255, 255))

        return composited

    def _remove_solid_background(self, image: Image.Image) -> Image.Image:
        try:
            image = image.convert("RGBA")
            img_np = np.array(image)
            if np.mean(img_np[:, :, 3]) < 250:
                return image

            h, w = img_np.shape[:2]
            mask = np.zeros((h + 2, w + 2), np.uint8)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
            
            corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
            for pt in corners:
                cv2.floodFill(img_bgr, mask, pt, (255, 255, 255), (10, 10, 10), (10, 10, 10), flags=4 | (255 << 8))
            
            img_np[mask[1:-1, 1:-1] == 255, 3] = 0
            return Image.fromarray(img_np)
        except Exception as e:
            print(f"Background removal failed: {e}")
            return image

    def _get_anton_font(self, size: int):
        """Automatically downloads and uses the Google Anton font."""
        font_dir = self.static_root / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        font_path = font_dir / "Anton-Regular.ttf"
        
        if not font_path.exists():
            try:
                # Direct download link from Google Fonts GitHub
                url = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                font_path.write_bytes(r.content)
            except Exception as e:
                print(f"Failed to download Anton font: {e}")
                return ImageFont.load_default()
                
        return ImageFont.truetype(str(font_path), size)

    def _fallback_background(self, width: int, height: int) -> Image.Image:
        return Image.new("RGBA", (width, height), (15, 23, 42, 255))

    def _load_logo(self, logo_path: str | None) -> Image.Image | None:
        # 1. Try to load the explicit path
        try:
            if logo_path and logo_path.startswith("http"):
                response = requests.get(logo_path, timeout=12)
                response.raise_for_status()
                return Image.open(BytesIO(response.content)).convert("RGBA")
            
            if logo_path:
                path = Path(logo_path.lstrip("/"))
                if path.exists():
                    return Image.open(path).convert("RGBA")
        except Exception as e:
            print(f"Failed to load explicit logo path: {e}")

        # 2. FIX: Fallback to the MOST RECENTLY UPLOADED logo
        fallback_dir = self.static_root / "logos"
        files = sorted(fallback_dir.glob("*-uploaded-logo.png"), key=os.path.getmtime, reverse=True)
        if files:
            try:
                return Image.open(files[0]).convert("RGBA")
            except Exception:
                pass
                
        return None

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        color = color.lstrip("#")
        if len(color) != 6:
            return (14, 165, 233)
        return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "team"