"""
知识库入库脚本：将 data/knowledge/ 下的文档导入 Chroma 向量库。

用法：
    cd backend
    python -m data.scripts.ingest_knowledge
"""
import json
import os
import sys
from pathlib import Path

import chromadb
from chromadb.config import Settings

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"


def load_json_docs(filepath: Path, city: str) -> list[dict]:
    """加载 JSON 文件并切分为文档片段。"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []
    category = filepath.stem

    if isinstance(data, list):
        for item in data:
            text = json.dumps(item, ensure_ascii=False, indent=2)
            name = item.get("name", "")
            docs.append({
                "text": text,
                "metadata": {
                    "city": city,
                    "category": category,
                    "name": name,
                    "source": str(filepath.name),
                },
            })
    elif isinstance(data, dict):
        text = json.dumps(data, ensure_ascii=False, indent=2)
        docs.append({
            "text": text,
            "metadata": {
                "city": city,
                "category": category,
                "name": data.get("city", city),
                "source": str(filepath.name),
            },
        })

    return docs


def load_markdown_docs(filepath: Path, city: str) -> list[dict]:
    """加载 Markdown 文件并按二级标题切分。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    sections = []
    current_section = ""
    current_title = filepath.stem

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_section.strip():
                sections.append({
                    "text": current_section.strip(),
                    "metadata": {
                        "city": city,
                        "category": "tips",
                        "name": current_title,
                        "source": str(filepath.name),
                    },
                })
            current_title = line.replace("## ", "").strip()
            current_section = line + "\n"
        else:
            current_section += line + "\n"

    if current_section.strip():
        sections.append({
            "text": current_section.strip(),
            "metadata": {
                "city": city,
                "category": "tips",
                "name": current_title,
                "source": str(filepath.name),
            },
        })

    return sections


def main():
    print(f"Knowledge dir: {KNOWLEDGE_DIR}")
    print(f"Chroma dir: {CHROMA_DIR}")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    try:
        client.delete_collection("travel_knowledge")
        print("Deleted existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="travel_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    all_docs = []

    for city_dir in KNOWLEDGE_DIR.iterdir():
        if not city_dir.is_dir() or city_dir.name.startswith("."):
            continue

        city = city_dir.name
        print(f"\nProcessing city: {city}")

        for filepath in city_dir.iterdir():
            if filepath.suffix == ".json":
                docs = load_json_docs(filepath, city)
                print(f"  {filepath.name}: {len(docs)} documents")
                all_docs.extend(docs)
            elif filepath.suffix == ".md":
                docs = load_markdown_docs(filepath, city)
                print(f"  {filepath.name}: {len(docs)} sections")
                all_docs.extend(docs)

    if not all_docs:
        print("No documents found!")
        return

    print(f"\nTotal documents to ingest: {len(all_docs)}")

    batch_size = 50
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i : i + batch_size]
        collection.add(
            documents=[d["text"] for d in batch],
            metadatas=[d["metadata"] for d in batch],
            ids=[f"doc_{i + j}" for j in range(len(batch))],
        )
        print(f"  Ingested batch {i // batch_size + 1}: {len(batch)} docs")

    print(f"\nDone! Total documents in collection: {collection.count()}")


if __name__ == "__main__":
    main()
