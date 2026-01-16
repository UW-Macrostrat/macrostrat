from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application settings for API v3.
    Values are loaded from environment variables and .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Database
    database_uri: str = Field(alias="uri")

    # OAuth
    redirect_uri: str = Field(alias="REDIRECT_URI_ENV")
    oauth_authorization_url: str = Field(alias="OAUTH_AUTHORIZATION_URL")
    oauth_token_url: str = Field(alias="OAUTH_TOKEN_URL")
    oauth_userinfo_url: str = Field(alias="OAUTH_USERINFO_URL")
    oauth_client_id: str = Field(alias="OAUTH_CLIENT_ID")
    oauth_client_secret: str = Field(alias="OAUTH_CLIENT_SECRET")

    # JWT
    jwt_secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ENCRYPTION_ALGORITHM",
    )

    # S3 / MinIO
    s3_access_key: str = Field(alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(alias="S3_SECRET_KEY")
    s3_bucket: str = Field(alias="S3_BUCKET")
    s3_endpoint: str = Field(alias="S3_ENDPOINT")
    s3_secure: bool = Field(default=True, alias="S3_SECURE")


settings = Settings()
