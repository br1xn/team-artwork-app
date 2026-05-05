import asyncio
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from models.schemas import LogoValidationResponse
from services.logo_validator import LogoValidator
from services.team_identifier import TeamIdentifier

router = APIRouter()

# Instantiate our services
validator = LogoValidator(timeout=10)
identifier = TeamIdentifier(timeout=15)

@router.post("/validate-logo", response_model=LogoValidationResponse)
async def validate_logo(
    team_name: str | None = Form(default=None), # <-- Magic happens here (Optional)
    logo: UploadFile = File(...),
):
    # 1. Read the uploaded image bytes
    try:
        logo_bytes = await logo.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read the uploaded logo.")

    # 2. AI Team Identification (Zero-Friction Trigger)
    if not team_name:
        inferred_name = await run_in_threadpool(identifier.identify, logo_bytes)
        
        if not inferred_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Our AI could not identify the team from this logo. Please ensure it is a valid sports logo."
            )
        team_name = inferred_name

    team = team_name.strip()

    # 3. Run the strict CLIP Validation
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(validator.validate_from_inputs, team, logo_bytes, logo.filename),
            timeout=120,
        )
        return result
        
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except asyncio.TimeoutError:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Validation timed out.")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(exc)}")