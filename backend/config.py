from pydantic_settings import BaseSettings, SettingsConfigDict


# Reads the values from our .env file into a typed Python object.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # PostgreSQL connection string. The real value lives in .env as DATABASE_URL;
    # this default is the local dev database so the app still boots without it.
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/cartpilot"

    razorpay_key_id: str
    razorpay_key_secret: str
    groq_api_key: str
    groq_model: str
    llm_provider: str = "groq"  # which backend get_provider() picks: "groq" or "hosted"
    razorpay_webhook_secret: str = ""  # shared secret Razorpay signs webhooks with (set in dashboard)


# One shared settings object that the rest of the app imports.
settings = Settings()
