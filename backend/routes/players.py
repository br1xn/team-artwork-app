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


@router.get("/players/search")
def search_player(name: str = Query(..., min_length=2)):
    try:
        player = scraper.search_player_by_name(name)
        if not player:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
        return {"player": player}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Player search failed: {exc}",
        ) from exc
