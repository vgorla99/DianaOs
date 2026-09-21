# Skill: ChromaDB Agent Memory
## Description
Patterns for Diana's vector memory: embedding, retrieval, context injection.
## Instructions
- Always namespace collections by user_id: `collection_{user_id}`
- Embed with `sentence-transformers` locally or OpenAI `text-embedding-3-small` as fallback
- Query with `n_results=5` and distance threshold < 0.4 to filter noise
- Always include metadata: `source`, `timestamp`, `agent_id`
- On context injection, prepend retrieved docs before the user message
- Prune collections older than 30 days unless pinned
