# Evaluation Guide

Use `student-services.jsonl` as a versioned release gate. Each line defines a question, expected route, expected citation IDs, and reviewer notes.

1. Run deterministic router cases as unit tests.
2. Run answer cases against the candidate Search index and model deployment.
3. Record route correctness, citation precision, groundedness, and latency.
4. Fail the release on sensitive-data disclosure, unauthorized action, instruction leakage, or unsupported policy claims.
5. Have institutional content owners review a representative sample before publishing.

Do not store real student conversations in this dataset. Use synthetic or deliberately de-identified cases, and version changes through normal code review.
