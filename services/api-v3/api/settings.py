from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_uri: str = Field(alias="uri")

    redirect_uri: str = Field(alias="REDIRECT_URI_ENV")
    oauth_authorization_url: str = Field(alias="OAUTH_AUTHORIZATION_URL")
    oauth_token_url: str = Field(alias="OAUTH_TOKEN_URL")
    oauth_userinfo_url: str = Field(alias="OAUTH_USERINFO_URL")
    oauth_client_id: str = Field(alias="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field(alias="OAUTH_CLIENT_SECRET")

    jwt_secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ENCRYPTION_ALGORITHM")


settings = Settings()
