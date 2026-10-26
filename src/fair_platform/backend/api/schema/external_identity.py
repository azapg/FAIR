from pydantic import BaseModel, Field

from .utils import schema_config


class GoogleLoginStart(BaseModel):
    model_config = schema_config
    invite_token: str | None = Field(default=None, max_length=512)
    remember_me: bool = False


class GoogleLinkStart(BaseModel):
    model_config = schema_config
    current_password: str = Field(min_length=1, max_length=128)
