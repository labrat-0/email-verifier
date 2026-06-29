from pydantic import BaseModel, Field
from typing import Optional


class InputModel(BaseModel):
    """Input schema matching .actor/input_schema.json exactly."""
    emails: list[str] = Field(
        min_length=1,
        max_length=100000,
        description="List of email addresses to verify.",
    )
    concurrency: int = Field(
        default=10,
        ge=1,
        le=50,
        description="How many emails to verify in parallel.",
    )
    perEmailTimeoutMs: int = Field(
        default=8000,
        ge=2000,
        le=30000,
        description="Hard timeout for each email's network checks (MX + SMTP).",
    )
    verifyCatchAll: bool = Field(
        default=True,
        description="When on, probe for catch-all detection.",
    )


class OutputModel(BaseModel):
    """Output row matching .actor/dataset_schema.json field-for-field."""
    email: str
    status: str  # valid | invalid | risky | unknown
    reason: str  # machine-readable reason code
    score: int   # 0-100 deliverability score
    mxFound: bool = False
    isDisposable: bool = False
    isRoleAccount: bool = False
    isFreeProvider: bool = False
    isCatchAll: bool = False
