import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.proxy.cache_middleware import CacheMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

middleware = CacheMiddleware()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Hit-or-Miss starting up (model=%s, threshold=%.2f)",
                middleware.active_model, middleware.threshold)
    yield
    await middleware.close()
    logger.info("Hit-or-Miss shut down")


app = FastAPI(title="Hit-or-Miss", version="0.1.0", lifespan=lifespan)


@app.post("/v1/messages")
async def proxy_messages(request: Request) -> JSONResponse:
    """Anthropic-compatible /v1/messages endpoint with semantic caching."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        result = await middleware.process_request(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error processing request")
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

    # Return the LLM response directly, with cache metadata in headers
    response = JSONResponse(content=result["response"])
    response.headers["X-Cache"] = "HIT" if result["cache_hit"] else "MISS"
    response.headers["X-Cache-Similarity"] = f"{result['similarity_score']:.4f}"
    response.headers["X-Timing-Embed-Ms"] = f"{result['timings']['embed_ms']:.2f}"
    response.headers["X-Timing-Search-Ms"] = f"{result['timings']['search_ms']:.2f}"
    response.headers["X-Timing-LLM-Ms"] = f"{result['timings']['llm_ms']:.2f}"
    response.headers["X-Timing-Total-Ms"] = f"{result['timings']['total_ms']:.2f}"
    return response
