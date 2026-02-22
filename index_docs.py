"""CLI wrapper for docs indexing."""

from policy_data_ai.rag.index_docs import index_docs


if __name__ == "__main__":
    path = index_docs()
    print(f"index_path={path}")

