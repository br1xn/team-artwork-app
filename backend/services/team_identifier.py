from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from google import genai


@dataclass
class TeamIdentifier:
    timeout: int = 15

    def __post_init__(self) -> None:
        # The new SDK automatically picks up GEMINI_API_KEY from your .env file
        self.client = genai.Client()
        # Using the exact model and interactions API specified in the new documentation
        self.model = "gemini-3-flash-preview"

    def _get_mime_type(self, image_bytes: bytes) -> str:
        # Check the "magic bytes" of the file to determine its actual format
        if image_bytes.startswith(b'\xff\xd8'):
            return 'image/jpeg'
        elif image_bytes.startswith(b'\x89PNG'):
            return 'image/png'
        elif image_bytes.startswith(b'RIFF') and image_bytes[8:12] == b'WEBP':
            return 'image/webp'
        return 'image/png'  # Default fallback

    def identify(self, image_bytes: bytes) -> str | None:
        if not image_bytes:
            print("Error: Missing Image Data.")
            return None

        try:
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            mime_type = self._get_mime_type(image_bytes)

            prompt = (
                "Identify the sports team represented by this logo. "
                "Return ONLY the official full team name (e.g., 'Dallas Cowboys', 'Chennai Super Kings'). "
                "Do not include any other text, punctuation, or explanation. "
                "If you absolutely cannot identify the team, reply strictly with 'Unknown'."
            )

            # Using the new multimodal array structure required by the Interactions API
            input_payload = [
                {"type": "text", "text": prompt},
                {"type": "image", "mime_type": mime_type, "data": base64_image}
            ]

            interaction = self.client.interactions.create(
                model=self.model,
                input=input_payload
            )

            # Safely extract the text from the new output format
            text_output = next((o for o in interaction.outputs if o.type == "text"), None)
            
            if text_output and text_output.text:
                text = text_output.text.strip()
                if text.lower() != "unknown":
                    # Clean up any trailing periods or weird formatting the LLM might add
                    return text.strip(" .\"'")
            
            return None

        except Exception as e:
            # This will gracefully catch any SDK or API errors without crashing the server
            print(f"Team Identification Request Failed: {e}")
            return None