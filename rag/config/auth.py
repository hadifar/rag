from pydantic import BaseModel, SecretStr


class AuthConfig(BaseModel):
    JWT_SECRET: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
