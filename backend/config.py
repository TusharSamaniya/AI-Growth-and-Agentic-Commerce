from pydantic_settings import BaseSettings, SettingsConfigDict


# Reads the values from our .env file into a typed Python object.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    razorpay_key_id: str
    razorpay_key_secret: str
    ollama_model: str


# One shared settings object that the rest of the app imports.
settings = Settings()
