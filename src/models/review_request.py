from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="The T-SQL script to review")
    schema_context: dict | None = Field(
        default=None,
        description="Optional schema override; defaults to the built-in Schema.json",
    )
    max_iterations: int = Field(
        default=3, ge=1, le=10, description="Max critique-revise loop iterations"
    )
