from pydantic import BaseModel, Field


class LogoValidationRequest(BaseModel):
    team_name: str = Field(..., min_length=2)


class LogoSource(BaseModel):
    provider: str
    url: str
    label: str


class LogoValidationResponse(BaseModel):
    team: str
    confidence: float = 0.0
    status: str
    matched_sources: list[str] = []
    color_match: float = 0.0
    visual_match: float = 0.0
    validation_model: str = "openai/clip-vit-base-patch32"
    validation_provider: str = "Hugging Face Transformers CLIP"
    scoring_formula: str = "0.7 * visual_similarity + 0.3 * color_similarity"
    sources_checked: list[str] = []
    candidate_sources: list[LogoSource] = []
    uploaded_filename: str | None = None
    error: str | None = None
    validation_evidence: str | None = None
    dominant_colors: list[str] = Field(default_factory=list, exclude=True)

    @property
    def team_name(self) -> str:
        return self.team

    @property
    def is_valid(self) -> bool:
        return self.status == "valid"

    @property
    def source(self) -> LogoSource | None:
        return self.candidate_sources[0] if self.candidate_sources else None


class Player(BaseModel):
    name: str
    role: str | None = None
    image_url: str | None = None
    processed_image_path: str | None = None
    source: str | None = None

    @property
    def position(self) -> str | None:
        return self.role

    @property
    def has_image(self) -> bool:
        return bool(self.image_url)


class PlayerCollectionResponse(BaseModel):
    team_name: str
    players: list[Player]


class ArtworkResponse(BaseModel):
    thumbnail: str
    poster: str
    variants: list[str]
    provider: str = "PIL fallback composer"
    model: str | None = None
    prompt: str | None = None


class ProcessTeamResponse(BaseModel):
    validation: LogoValidationResponse | None = None
    players: list[Player] = []
    artwork: ArtworkResponse | None = None
