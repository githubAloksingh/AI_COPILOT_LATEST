import json
import chromadb
from chromadb.config import Settings
import httpx
from app.config import settings

def inspect_remote_chroma():
    """Inspect Chroma running as a server at CHROMA_URL."""
    print(f"Connecting to remote Chroma at: {settings.chroma_url}...")
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.chroma_url}/api/v2/tenants/default_tenant/databases/default_database/collections")
            if resp.status_code != 200:
                resp = client.get(f"{settings.chroma_url}/api/v1/collections")
            
            if resp.status_code == 200:
                collections = resp.json()
                print(f"\nFound {len(collections)} collection(s) in remote Chroma:")
                for col in collections:
                    name = col.get("name")
                    col_id = col.get("id")
                    print(f"\n📁 Collection Name: {name} (ID: {col_id})")
                    
                    # Fetch items from collection
                    fetch_url = f"{settings.chroma_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{col_id}/get"
                    fetch_resp = client.post(fetch_url, json={"limit": 50, "include": ["metadatas", "documents"]})
                    if fetch_resp.status_code != 200:
                        fetch_url = f"{settings.chroma_url}/api/v1/collections/{col_id}/get"
                        fetch_resp = client.post(fetch_url, json={"limit": 50, "include": ["metadatas", "documents"]})
                    
                    if fetch_resp.status_code == 200:
                        data = fetch_resp.json()
                        ids = data.get("ids", [])
                        metas = data.get("metadatas", [])
                        docs = data.get("documents", [])
                        
                        print(f"   Total Chunks stored: {len(ids)}")
                        for i in range(min(5, len(ids))):
                            print(f"\n   🔹 Chunk ID: {ids[i]}")
                            print(f"      Metadata: {metas[i] if i < len(metas) else {}}")
                            snippet = docs[i][:120].replace('\n', ' ') if i < len(docs) and docs[i] else ""
                            print(f"      Text Preview: \"{snippet}...\"")
                        if len(ids) > 5:
                            print(f"\n   ... and {len(ids) - 5} more chunks.")
                return True
    except Exception as e:
        print(f"Remote Chroma connection failed: {e}")
    return False

def inspect_local_chroma():
    """Inspect local ChromaDB storage."""
    print(f"\nChecking local persistent Chroma storage at: {settings.chroma_persist_directory}...")
    try:
        client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        collections = client.list_collections()
        print(f"Found {len(collections)} collection(s) in local storage:")
        for col in collections:
            count = col.count()
            print(f"\n📁 Collection Name: {col.name}")
            print(f"   Total Chunks Stored: {count}")
            
            if count > 0:
                sample = col.get(limit=5, include=["metadatas", "documents"])
                ids = sample.get("ids", [])
                metas = sample.get("metadatas", [])
                docs = sample.get("documents", [])
                
                for i in range(len(ids)):
                    print(f"\n   🔹 Chunk ID: {ids[i]}")
                    print(f"      Metadata: {metas[i] if i < len(metas) else {}}")
                    snippet = docs[i][:120].replace('\n', ' ') if i < len(docs) and docs[i] else ""
                    print(f"      Text Preview: \"{snippet}...\"")
    except Exception as e:
        print(f"Local Chroma check error: {e}")

if __name__ == "__main__":
    if not inspect_remote_chroma():
        inspect_local_chroma()
