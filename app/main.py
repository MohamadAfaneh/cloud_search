from fastapi import FastAPI, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
import logging
import uvicorn
from .core.constants import API , V1
from .core.config import get_settings
from .api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if get_settings().DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cloud Search Service",
    description="A service for searching through cloud storage files",
    version=get_settings().API_VERSION,
    debug=get_settings().DEBUG
)

settings = get_settings()

app.include_router(router, prefix="/{}/{}".format(API,V1))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=get_settings().DEBUG,
        log_level="debug" if get_settings().DEBUG else "info"
    ) 
