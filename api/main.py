from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, HttpUrl, conlist
from typing import Dict, Any, List, Optional
from indexify import IndexifyClient
import asyncio
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import prometheus_client
from prometheus_client import Counter, Histogram
import time

app = FastAPI(title="Web Content Extraction API")

EXTRACTION_REQUESTS = Counter(
    'extraction_requests_total',
    'Total number of extraction requests',
    ['endpoint', 'status']
)

EXTRACTION_DURATION = Histogram(
    'extraction_duration_seconds',
    'Time spent processing extraction requests',
    ['endpoint']
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractionSchema(BaseModel):
    type: str = "object"
    properties: Dict[str, Any]
    required: List[str] = []

class ExtractionRequest(BaseModel):
    url: HttpUrl
    schema: ExtractionSchema
    selector_rules: Optional[Dict[str, str]] = None

class BatchExtractionRequest(BaseModel):
    urls: conlist(HttpUrl, min_items=1, max_items=10)  # Limit batch size
    schema: ExtractionSchema
    selector_rules: Optional[Dict[str, str]] = None

class ExtractionResponse(BaseModel):
    status: str
    data: Dict[str, Any]
    error: Optional[str] = None

class BatchExtractionResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    errors: Optional[List[str]] = None

async def update_extraction_metrics(start_time: float, endpoint: str, status: str):
    duration = time.time() - start_time
    EXTRACTION_REQUESTS.labels(endpoint = endpoint, status = status).inc()
    EXTRACTION_DURATION.labels(endpoint = endpoint).observe(duration)

async def get_indexify_client(): # easier to hv a generator than check and instantiate
    client = IndexifyClient("http://localhost:9000")
    try:
        yield client
    finally:
        await client.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return prometheus_client.generate_latest()

@app.post("/extract", response_model = ExtractionResponse)
@limiter.limit("100/minute")
async def extract_content(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks,
    client: IndexifyClient = Depends(get_indexify_client)
):
    start_time = time.time()
    try:
        job = await client.submit_extraction_job(
            "web-content-extractor",
            urls = [str(request.url)],
            params = {
                "schema": request.schema.dict(),
                "selector_rules": request.selector_rules
            }
        )
        
        try:
            results = await asyncio.wait_for(job.wait_for_completion(), timeout = 30)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code = 408,
                detail = "Extraction timed out"
            )
        
        if not results or not results[0]:
            background_tasks.add_task(
                update_extraction_metrics,
                start_time,
                "single",
                "failure"
            )
            return ExtractionResponse(
                status = "error",
                data = {},
                error = "Failed to extract content"
            )
            
        background_tasks.add_task(
            update_extraction_metrics,
            start_time,
            "single",
            "success"
        )
        return ExtractionResponse(
            status = "success",
            data = results[0]
        )
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        background_tasks.add_task(
            update_extraction_metrics,
            start_time,
            "single",
            "error"
        )
        return ExtractionResponse(
            status = "error",
            data = {},
            error = str(e)
        )

@app.post("/extract/batch", response_model=BatchExtractionResponse)
@limiter.limit("20/minute")
async def extract_batch(
    request: BatchExtractionRequest,
    background_tasks: BackgroundTasks,
    client: IndexifyClient = Depends(get_indexify_client)
):
    start_time = time.time()
    try:
        job = await client.submit_extraction_job(
            "web-content-extractor",
            urls = [str(url) for url in request.urls],
            params = {
                "schema": request.schema.dict(),
                "selector_rules": request.selector_rules
            }
        )
        
        try:
            results = await asyncio.wait_for(job.wait_for_completion(), timeout=60)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code = 408,
                detail = "Batch extraction timed out"
            )
        
        valid_results = []
        errors = []
        
        for i, result in enumerate(results):
            if result is None:
                errors.append(f"Failed to extract content from URL {request.urls[i]}")
            else:
                valid_results.append(result)
        
        background_tasks.add_task(
            update_extraction_metrics,
            start_time,
            "batch",
            "success" if valid_results else "failure"
        )
        
        return BatchExtractionResponse(
            status = "success" if valid_results else "error",
            data = valid_results,
            errors = errors if errors else None
        )
        
    except Exception as e:
        logger.error(f"Batch extraction error: {str(e)}")
        background_tasks.add_task(
            update_extraction_metrics,
            start_time,
            "batch",
            "error"
        )
        return BatchExtractionResponse(
            status = "error",
            data = [],
            errors = [str(e)]
        )

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title = "Web Content Extraction API",
        version = "1.0.0",
        description = "API for extracting structured content from web pages",
        routes = app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
