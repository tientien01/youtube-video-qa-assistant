---
id: REF-001
document_status: approved
normative: false
last_verified: 2026-07-16
---

# Related Projects and Primary References

These references inform decisions but are not project specifications.

## Related repositories

- [youtube-ai-assistant](https://github.com/iamarunbrahma/youtube-ai-assistant): demonstrates YouTube loading, recursive/token-aware chunking, Qdrant, and RAG; useful baseline, but this project adds persistent jobs, provenance, evaluation, and provider boundaries.
- [youtube-rag](https://github.com/yanliu1111/youtube-rag): demonstrates Whisper as an audio transcription path; informs optional ASR fallback rather than the default path.
- [local-rag-llamaindex](https://github.com/Otman404/local-rag-llamaindex): demonstrates a local FastAPI, Qdrant, Ollama, and LlamaIndex stack; supports the local-first deployment direction.
- [OpenAI knowledge retrieval](https://github.com/openai/openai-knowledge-retrieval): demonstrates configuration-driven retrieval strategies and evaluation; informs experiment/version discipline.
- [YapBack](https://huggingface.co/spaces/Yuvan777/yapback/blob/main/README.md): demonstrates timestamp metadata, sentence-oriented chunks, and retrieval evaluation in a video RAG product.

## Primary technical references

- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [yt-dlp subtitle options](https://github.com/yt-dlp/yt-dlp#subtitle-options)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Stanza sentence segmentation](https://stanfordnlp.github.io/stanza/tokenize.html)
- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html#symmetric-vs-asymmetric-semantic-search)
- [Qwen3 Embedding on Ollama](https://ollama.com/library/qwen3-embedding)
- [BGE-M3](https://huggingface.co/BAAI/bge-m3)
- [BGE reranker v2 M3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- [Qdrant local client](https://github.com/qdrant/qdrant-client)
- [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- [Ollama embeddings](https://docs.ollama.com/capabilities/embeddings)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [uv project lockfiles](https://docs.astral.sh/uv/concepts/projects/layout/)
