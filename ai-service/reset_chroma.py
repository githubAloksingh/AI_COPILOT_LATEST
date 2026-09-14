"""
Reset the configured ChromaDB collection to fix embedding dimension mismatches.

Run this once after changing the local embedding model, then restart the AI service.
"""

import chromadb
from chromadb.config import Settings

CHROMA_PERSIST_DIR = "./chroma_data"
COLLECTION_NAME = "ai_work_copilot"

print(f"Connecting to local ChromaDB at: {CHROMA_PERSIST_DIR}")

client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR,
    settings=Settings(anonymized_telemetry=False),
)

existing = [collection.name for collection in client.list_collections()]
print(f"Existing collections: {existing}")

if COLLECTION_NAME in existing:
    client.delete_collection(COLLECTION_NAME)
    print(f"Deleted collection '{COLLECTION_NAME}' (embedding model reset)")
else:
    print(f"Collection '{COLLECTION_NAME}' does not exist - nothing to delete")

print("Done. Restart the AI service to recreate the collection with 384-dimensional embeddings.")
