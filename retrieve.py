"""CLI wrapper for definition retrieval."""

import json
import sys

from policy_data_ai.rag.retrieve import answer_definition


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip() or "What does value mean?"
    answer = answer_definition(question)
    print(json.dumps(answer, indent=2))

