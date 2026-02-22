"""CLI wrapper for documentation ingestion."""

from policy_data_ai.rag.ingest_docs import ingest_docs


if __name__ == "__main__":
    files = ingest_docs()
    print(f"ingested_docs={len(files)}")

