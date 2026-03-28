import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# --- Embedding Models ---
EMBEDDING_MODELS: dict[str, dict] = {
    "all-MiniLM-L6-v2": {
        "display_name": "Small (MiniLM)",
        "dimension": 384,
        "params": "22M",
    },
    "all-mpnet-base-v2": {
        "display_name": "Medium (MPNet)",
        "dimension": 768,
        "params": "109M",
    },
    "BAAI/bge-large-en-v1.5": {
        "display_name": "Large (BGE)",
        "dimension": 1024,
        "params": "335M",
    },
}

DEFAULT_EMBEDDING_MODEL: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
DEFAULT_SIMILARITY_THRESHOLD: float = float(os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.85"))

# --- ChromaDB ---
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", str(Path("./chroma_data")))

def collection_name_for_model(model_name: str) -> str:
    """Return ChromaDB collection name for a given embedding model."""
    safe_name = model_name.replace("/", "_")
    return f"semantic_cache_{safe_name}"

# --- Anthropic API ---
ANTHROPIC_API_URL: str = "https://api.anthropic.com/v1/messages"
ANTHROPIC_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
