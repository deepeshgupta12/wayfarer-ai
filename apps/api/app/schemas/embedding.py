from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Input text to embed.")
    provider: str | None = Field(
        default=None,
        description="Optional provider override. Allowed values currently: openai, ollama.",
    )


class EmbeddingResponse(BaseModel):
    provider: str
    model: str
    dimensions: int
    vector: list[float]