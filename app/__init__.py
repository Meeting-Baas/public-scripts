from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="OpenAPI Comparison Service",
    description="Service for comparing OpenAPI specifications between different commits",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1") 