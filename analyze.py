"""
analyze.py – Semantic search over saved articles using ChromaDB.

Indexes all articles into a ChromaDB collection, queries with each keyword,
then translates and saves the best-matching results to search_results.json.

Usage:
    python analyze.py                        # use default articles_db/index.json
    python analyze.py --db articles_db/index.json
    python analyze.py --top 10              # results per keyword (default 5)
"""

import argparse
import json
import os
from datetime import datetime, timezone

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from deep_translator import GoogleTranslator

KEYWORDS = [
    "Saisonarbeiter",
    "Erntehelfer",
    "Drittstaatenabkommen",
    "nicht-eu",
]

COLLECTION_NAME = "articles"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_index(index_file: str) -> dict:
    if not os.path.exists(index_file):
        raise FileNotFoundError(f"Index not found: {index_file}")
    with open(index_file, encoding="utf-8") as fh:
        return json.load(fh)


def load_article(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as fh:
        return json.load(fh)


def translate(text: str) -> str:
    if not text or not text.strip():
        return ""
    try:
        return GoogleTranslator(source="auto", target="en").translate(text[:4999])
    except Exception as exc:
        return f"(translation failed: {exc})"


# ---------------------------------------------------------------------------
# ChromaDB indexing
# ---------------------------------------------------------------------------

def build_collection(index: dict) -> chromadb.Collection:
    """Load all articles into an in-memory ChromaDB collection."""
    client = chromadb.Client()  # ephemeral, in-memory
    ef = DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)

    ids, documents, metadatas = [], [], []
    for entry in index.values():
        filepath = entry.get("file", "")
        if not os.path.exists(filepath):
            continue
        article = load_article(filepath)
        doc_text = " ".join(filter(None, [
            article.get("title", ""),
            article.get("meta_description", ""),
            article.get("summary", ""),
            article.get("full_text", "")[:2000],  # cap to avoid huge embeddings
        ]))
        if not doc_text.strip():
            continue
        ids.append(article["id"])
        documents.append(doc_text)
        metadatas.append({
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "url": article.get("url", ""),
            "published_date": article.get("published_date") or "",
            "summary": article.get("summary", "") or article.get("meta_description", ""),
        })

    # ChromaDB requires unique ids; upsert in batches of 100
    batch = 100
    for i in range(0, len(ids), batch):
        collection.upsert(
            ids=ids[i:i+batch],
            documents=documents[i:i+batch],
            metadatas=metadatas[i:i+batch],
        )

    print(f"Indexed {len(ids)} articles into ChromaDB.")
    return collection


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic keyword analysis of scraped articles")
    parser.add_argument("--db", default="articles_db/index.json", help="Path to index.json")
    parser.add_argument("--top", type=int, default=5, help="Top N results per keyword")
    parser.add_argument("--out", default="search_results.json", help="Output file path")
    args = parser.parse_args()

    index = load_index(args.db)
    print(f"Total articles in database: {len(index)}\n")

    collection = build_collection(index)

    results_by_keyword: dict[str, list[dict]] = {}
    seen_ids: set[str] = set()

    for keyword in KEYWORDS:
        print(f"\nQuerying: '{keyword}'")
        results = collection.query(query_texts=[keyword], n_results=min(args.top, collection.count()))

        keyword_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            similarity = round(1 - distance, 4)  # cosine distance → similarity

            title_en = translate(meta["title"])
            summary_en = translate(meta["summary"])

            entry = {
                "id": doc_id,
                "similarity_score": similarity,
                "source": meta["source"],
                "url": meta["url"],
                "published_date": meta["published_date"],
                "title_original": meta["title"],
                "title_english": title_en,
                "summary_english": summary_en,
            }
            keyword_results.append(entry)
            seen_ids.add(doc_id)

            print(f"  [{similarity:.3f}] {meta['source']} – {title_en[:80]}")

        results_by_keyword[keyword] = keyword_results

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles_indexed": collection.count(),
        "keywords_queried": KEYWORDS,
        "top_n_per_keyword": args.top,
        "results": results_by_keyword,
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {args.out}")
    print(f"Total unique articles matched: {len(seen_ids)}")


if __name__ == "__main__":
    main()
