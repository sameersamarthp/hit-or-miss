import logging
import markdown
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.config import EMBEDDING_MODELS
from src.proxy.cache_middleware import CacheMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

middleware = CacheMiddleware()

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "benchmark_report.md"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Hit-or-Miss starting up (model=%s, threshold=%.2f)",
                middleware.active_model, middleware.threshold)
    yield
    await middleware.close()
    logger.info("Hit-or-Miss shut down")


app = FastAPI(title="Hit-or-Miss", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# LLM Proxy Endpoint
# ---------------------------------------------------------------------------

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

    response = JSONResponse(content=result["response"])
    response.headers["X-Cache"] = "HIT" if result["cache_hit"] else "MISS"
    response.headers["X-Cache-Similarity"] = f"{result['similarity_score']:.4f}"
    response.headers["X-Timing-Embed-Ms"] = f"{result['timings']['embed_ms']:.2f}"
    response.headers["X-Timing-Search-Ms"] = f"{result['timings']['search_ms']:.2f}"
    response.headers["X-Timing-LLM-Ms"] = f"{result['timings']['llm_ms']:.2f}"
    response.headers["X-Timing-Total-Ms"] = f"{result['timings']['total_ms']:.2f}"
    return response


# ---------------------------------------------------------------------------
# Playground API (used by the JS frontend)
# ---------------------------------------------------------------------------

@app.post("/api/playground")
async def api_playground(request: Request) -> JSONResponse:
    """Process a playground prompt through the cache middleware."""
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    model = data.get("model")
    threshold = data.get("threshold")

    body = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }

    try:
        result = await middleware.process_request(
            body,
            model_override=model,
            threshold_override=float(threshold) if threshold else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Playground error")
        raise HTTPException(status_code=502, detail=str(e))

    return JSONResponse(content=result)


# ---------------------------------------------------------------------------
# Management API
# ---------------------------------------------------------------------------

@app.get("/api/stats")
async def api_stats() -> JSONResponse:
    """Cache statistics."""
    return JSONResponse(content=middleware.get_stats())


@app.get("/api/models")
async def api_models() -> JSONResponse:
    """List available embedding models."""
    models = []
    for name, info in EMBEDDING_MODELS.items():
        cache = middleware.get_cache_for_model(name)
        models.append({
            "name": name,
            "display_name": info["display_name"],
            "dimension": info["dimension"],
            "params": info["params"],
            "is_active": name == middleware.active_model,
            "cache_entries": cache.count(),
        })
    return JSONResponse(content={"models": models})


@app.post("/api/model/switch")
async def api_switch_model(request: Request) -> JSONResponse:
    """Switch the active embedding model."""
    data = await request.json()
    model_name = data.get("model")
    if not model_name:
        raise HTTPException(status_code=400, detail="model is required")
    try:
        middleware.active_model = model_name
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content={"status": "ok", "active_model": middleware.active_model})


@app.post("/api/cache/clear")
async def api_clear_cache(request: Request) -> JSONResponse:
    """Clear cache for a specific model or all models."""
    data = await request.json()
    model_name = data.get("model")

    if model_name and model_name != "all":
        if model_name not in EMBEDDING_MODELS:
            raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
        cache = middleware.get_cache_for_model(model_name)
        cache.clear()
        return JSONResponse(content={"status": "ok", "cleared": model_name})

    # Clear all
    for name in EMBEDDING_MODELS:
        cache = middleware.get_cache_for_model(name)
        cache.clear()
    return JSONResponse(content={"status": "ok", "cleared": "all"})


@app.get("/api/cache/entries")
async def api_cache_entries(model: str | None = None) -> JSONResponse:
    """Return all cached entries for a model."""
    model_name = model or middleware.active_model
    if model_name not in EMBEDDING_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
    cache = middleware.get_cache_for_model(model_name)
    entries = cache.get_all_entries()
    return JSONResponse(content={"model": model_name, "entries": entries})


# ---------------------------------------------------------------------------
# UI Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to playground."""
    return templates.TemplateResponse(request, "playground.html", {
        "models": EMBEDDING_MODELS,
        "active_model": middleware.active_model,
        "threshold": middleware.threshold,
        "recent_queries": middleware.get_recent_queries(),
    })


@app.get("/playground", response_class=HTMLResponse)
async def playground(request: Request):
    return templates.TemplateResponse(request, "playground.html", {
        "models": EMBEDDING_MODELS,
        "active_model": middleware.active_model,
        "threshold": middleware.threshold,
        "recent_queries": middleware.get_recent_queries(),
    })


@app.get("/cache", response_class=HTMLResponse)
async def cache_inspector(request: Request):
    active_model = middleware.active_model
    cache = middleware.get_cache_for_model(active_model)
    entries = cache.get_all_entries()
    counts = {}
    for name in EMBEDDING_MODELS:
        c = middleware.get_cache_for_model(name)
        counts[name] = c.count()
    return templates.TemplateResponse(request, "cache_inspector.html", {
        "models": EMBEDDING_MODELS,
        "active_model": active_model,
        "entries": entries,
        "counts": counts,
    })


@app.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    report_html = None
    if REPORT_PATH.exists():
        md_content = REPORT_PATH.read_text()
        report_html = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
    return templates.TemplateResponse(request, "report.html", {
        "report_html": report_html,
    })
