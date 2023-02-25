"""Initialize API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import accounts, analytics, authors, donations, github, images, newsletter, posts, tags
from config import settings
from database.orm import Base, engine
from log import LOGGER

Base.metadata.create_all(bind=engine)

# Initialize API
api = FastAPI(
    title=settings.TITLE,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    debug=settings.DEBUG,
    docs_url="/",
    openapi_url="/api.json",
    openapi_tags=settings.API_TAGS,
    root_path=settings.ROOT_PATH,
)

# Define Middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
api.include_router(analytics.router)
api.include_router(newsletter.router)
api.include_router(posts.router)
api.include_router(accounts.router)
api.include_router(authors.router)
api.include_router(donations.router)
api.include_router(images.router)
api.include_router(tags.router)
api.include_router(github.router)

LOGGER.success("API successfully started.")
