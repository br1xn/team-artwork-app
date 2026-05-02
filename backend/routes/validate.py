from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from models.schemas import LogoValidationRequest, LogoValidationResponse
from services.logo_validator import LogoValidator


router = APIRouter(tags=["validation"])
validator = LogoValidator()


@router.post("/validate-logo", response_model=LogoValidationResponse)
async def validate_logo(
    team_name: str = Form(...),
    logo: UploadFile | None = File(default=None),
) -> LogoValidationResponse:
    try:
        payload = LogoValidationRequest(team_name=team_name)
        logo_bytes = await logo.read() if logo else None
        return validator.validate(payload, logo_bytes, logo.filename if logo else None)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Logo validation failed: {exc}",
        ) from exc
