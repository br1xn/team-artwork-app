from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
import asyncio

from models.schemas import ArtworkResponse
from services.generator import ArtworkGeneratorService
from utils.color_utils import infer_palette_from_name

router = APIRouter()
generator = ArtworkGeneratorService()

@router.post("/artwork", response_model=ArtworkResponse)
async def generate_artwork(
    team_name: str = Form(...),
    logo: UploadFile = File(...),
):
    try:
        team = team_name.strip()
        logo_bytes = await logo.read()
        team_colors = infer_palette_from_name(team)
        
        # Pass the raw bytes directly to the generator
        artwork = await asyncio.wait_for(
            run_in_threadpool(generator.generate, team, logo_bytes, team_colors),
            timeout=120,
        )
        return artwork
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Artwork generation failed: {exc}",
        ) from exc