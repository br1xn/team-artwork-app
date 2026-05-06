import asyncio
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

from models.schemas import PlayerCollectionResponse, ProcessTeamResponse
from routes.artwork import router as artwork_router
from routes.players import router as players_router
from routes.validate import router as validate_router
from services.generator import ArtworkGeneratorService
from services.image_processor import ImageProcessor
from services.logo_validator import LogoValidator
from services.scraper import PlayerScraper
from services.team_identifier import TeamIdentifier  # <-- New Import
from utils.color_utils import infer_palette_from_name

limiter = Limiter(key_func=get_remote_address)


app = FastAPI(
    title="Team Artwork API",
    version="1.1.0",
    description="Validate team assets, scrape player data, auto-identify logos, and generate artwork.",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate_router, prefix="/api")
app.include_router(players_router, prefix="/api")
app.include_router(artwork_router, prefix="/api")

# Ensure all static subdirectories exist so the Figma Generator doesn't crash
static_root = Path("static")
static_root.mkdir(exist_ok=True)
(static_root / "artwork").mkdir(exist_ok=True)
(static_root / "logos").mkdir(exist_ok=True)
(static_root / "fonts").mkdir(exist_ok=True)

# Mount the static directory to serve generated images to the React frontend
app.mount("/static", StaticFiles(directory=static_root), name="static")

validator = LogoValidator(timeout=10)
scraper = PlayerScraper(timeout=10)
processor = ImageProcessor(static_root=static_root, timeout=10)
generator = ArtworkGeneratorService(static_root=static_root)
identifier = TeamIdentifier(timeout=15)  # <-- Instantiate the new service


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/process-team")
def process_team_preview() -> RedirectResponse:
    return RedirectResponse("http://127.0.0.1:5173", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.post("/process-team", response_model=ProcessTeamResponse)
@limiter.limit("15/minute")
async def process_team(
    request: Request,
    team_name: str | None = Form(default=None), # <-- Make this optional
    logo: UploadFile | None = File(default=None),
) -> ProcessTeamResponse:
    
    # 1. Catch if the user sent absolutely nothing
    if not team_name and not logo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must provide either a team name or upload a logo.")

    try:
        logo_bytes = await logo.read() if logo else None

        # 2. AI Team Identification (The New Magic)
        if not team_name:
            # We run the REST call in a threadpool so it doesn't block the async server
            inferred_name = await run_in_threadpool(identifier.identify, logo_bytes)
            if not inferred_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Could not automatically identify the team from this logo. Please enter the team name manually."
                )
            team_name = inferred_name

        team = team_name.strip()
        logo_path = _save_uploaded_logo(team, logo_bytes) if logo_bytes else None

        async def run_validation():
            if logo_bytes:
                return await asyncio.wait_for(
                    run_in_threadpool(validator.validate_from_inputs, team, logo_bytes, logo.filename),
                    timeout=120,
                )
            else:
                return await asyncio.wait_for(
                    run_in_threadpool(validator.fetch_candidate_logos, team),
                    timeout=30,
                )

        async def run_scraping():
            try:
                players_response = await asyncio.wait_for(
                    run_in_threadpool(scraper.scrape_players, team),
                    timeout=30,
                )
            except Exception:
                players_response = PlayerCollectionResponse(team_name=team, players=scraper._fallback_players())
            
            return await asyncio.wait_for(
                run_in_threadpool(processor.process_headshots, players_response.players),
                timeout=60,
            )

        validation_result, players = await asyncio.gather(run_validation(), run_scraping())

        validation = None
        team_colors = infer_palette_from_name(team)
        
        if logo_bytes:
            validation = validation_result
            if validation.status == "invalid":
                return ProcessTeamResponse(validation=validation, players=[], artwork=None)
            if validation.dominant_colors:
                team_colors = validation.dominant_colors
        else:
            discovered_sources = validation_result
            if discovered_sources:
                logo_path = discovered_sources[0].url

        artwork = await asyncio.wait_for(
            run_in_threadpool(generator.generate, team, logo_bytes, team_colors, players), # Passes logo_bytes directly to generator
            timeout=120,
        )

        return ProcessTeamResponse(validation=validation, players=players, artwork=artwork)
        
    except HTTPException:
        raise # Allow our explicit HTTP exceptions to pass through
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Processing timed out while scraping or generating assets.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Team processing failed: {exc}",
        ) from exc


def _save_uploaded_logo(team_name: str, logo_bytes: bytes | None) -> str | None:
    if not logo_bytes:
        return None
    logo_dir = static_root / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    slug = "".join(character if character.isalnum() else "-" for character in team_name.lower()).strip("-")
    path = logo_dir / f"{slug or 'team'}-uploaded-logo.png"
    path.write_bytes(logo_bytes)
    return f"/static/logos/{path.name}"