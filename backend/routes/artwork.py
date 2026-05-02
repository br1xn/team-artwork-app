from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import ProcessTeamResponse
from services.generator import ArtworkGeneratorService
from services.image_processor import ImageProcessor
from services.logo_validator import LogoValidator
from services.scraper import PlayerScraper
from utils.color_utils import infer_palette_from_name


router = APIRouter(tags=["artwork"])
validator = LogoValidator()
scraper = PlayerScraper()
processor = ImageProcessor()
generator = ArtworkGeneratorService()


@router.post("/artwork", response_model=ProcessTeamResponse)
async def create_artwork(
    team_name: str = Form(...),
    logo: UploadFile | None = File(default=None),
) -> ProcessTeamResponse:
    try:
        logo_bytes = await logo.read() if logo else None
        validation = validator.validate_from_inputs(team_name, logo_bytes, logo.filename if logo else None) if logo_bytes else None
        if validation and validation.status == "invalid":
            return ProcessTeamResponse(validation=validation, players=[], artwork=None)
        players = scraper.scrape_players(team_name)
        processed_players = processor.process_headshots(players.players)
        processor.prepare_logo_variants(logo_bytes) if logo_bytes else []
        colors = validation.dominant_colors if validation and validation.dominant_colors else infer_palette_from_name(team_name)
        artwork = generator.generate(team_name, None, colors, processed_players)

        return ProcessTeamResponse(
            validation=validation,
            players=processed_players,
            artwork=artwork,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Artwork pipeline failed: {exc}",
        ) from exc
