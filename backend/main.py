from fastapi import FastAPI

# Create the FastAPI application. This "app" is what Uvicorn runs.
app = FastAPI()


# When someone sends a GET request to /health, run this function.
@app.get("/health")
def health():
    # FastAPI turns this dict into a JSON response automatically.
    return {"status": "ok"}
