import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import LinkAnalysisRequest, LinkAnalysisResponse, ErrorResponse
from app.services.analysis_service import AnalysisService
from app.services.llm_service import LLMProviderError
from app.utils.validators import (
    InvalidURLError,
    SSRFProtectionError,
    WebsiteInaccessibleError,
    InsufficientBusinessContentError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("link_analysis")

app = FastAPI(
    title="AI-Powered Website Link Analysis API",
    description=(
        "Production-grade FastAPI application that securely analyzes website URLs, "
        "extracts real business content with SSRF protection, and generates comprehensive "
        "competitor, SEO, search query, top services, and target audience intelligence via LLM."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Initialize analysis service singleton
analysis_service = AnalysisService()


@app.exception_handler(InvalidURLError)
async def invalid_url_handler(request: Request, exc: InvalidURLError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": "Invalid URL", "detail": str(exc)},
    )


@app.exception_handler(SSRFProtectionError)
async def ssrf_protection_handler(request: Request, exc: SSRFProtectionError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": "SSRF Protection Violation", "detail": str(exc)},
    )


@app.exception_handler(WebsiteInaccessibleError)
async def website_inaccessible_handler(request: Request, exc: WebsiteInaccessibleError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"success": False, "error": "Website Inaccessible", "detail": str(exc)},
    )


@app.exception_handler(InsufficientBusinessContentError)
async def insufficient_business_content_handler(request: Request, exc: InsufficientBusinessContentError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": "Insufficient Business Content", "detail": str(exc)},
    )


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(request: Request, exc: LLMProviderError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"success": False, "error": "LLM Provider Error", "detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "error": "Validation Error", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing request: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "error": "Internal Server Error", "detail": "An unexpected error occurred."},
    )


@app.post(
    "/link-analysis",
    response_model=LinkAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze website URL and generate 5-section AI intelligence",
    responses={
        200: {"model": LinkAnalysisResponse, "description": "Structured link analysis successfully generated."},
        400: {"model": ErrorResponse, "description": "Invalid URL or SSRF protection violation."},
        422: {"model": ErrorResponse, "description": "Malformed request payload."},
        502: {"model": ErrorResponse, "description": "Target website inaccessible or LLM provider error."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
async def link_analysis(payload: LinkAnalysisRequest) -> LinkAnalysisResponse:
    """
    Accepts a website URL, verifies SSRF safety, fetches and cleans the page content,
    and returns a structured 5-section intelligence analysis:
    1. Competitor vs Brand details
    2. Exactly 5 Target Search Queries across Google, Facebook, Instagram, LinkedIn, and/or X
    3. Practical SEO Improvements (keywords, title, meta description, supporting content)
    4. Exactly 5 Top Services with explicit/inferred labeling
    5. Target Audience Identification
    """
    logger.info(f"Received link analysis request for URL: {payload.url}")
    response = await analysis_service.run_analysis(payload.url)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
