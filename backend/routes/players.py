from fastapi import APIRouter, HTTPException, Query, status

from models.schemas import PlayerCollectionResponse
from services.scraper import PlayerScraper


router = APIRouter(tags=["players"])
scraper = PlayerScraper()


@router.get("/players", response_model=PlayerCollectionResponse)
def get_players(team_name: str = Query(..., min_length=2)) -> PlayerCollectionResponse:
    try:
        return scraper.scrape_players(team_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Player scraping failed: {exc}",
        ) from exc
