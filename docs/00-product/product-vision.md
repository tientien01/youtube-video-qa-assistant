---
id: PRODUCT-001
document_status: approved
implementation_status: planned
normative: true
last_verified: 2026-07-16
---

# Product Vision

## Positioning

The product is a local-first, evidence-grounded, bilingual video knowledge and learning workspace. It turns a YouTube video into a trustworthy, searchable source for questions, summaries, study notes, quizzes, and later cross-video research.

## Primary users

- Students learning from lectures and tutorials
- Self-learners reviewing long technical videos
- Researchers extracting verifiable claims from talks and podcasts

## Core job

For a supported video, the product MUST:

1. acquire and validate a transcript without corrupting prior data;
2. retrieve the most relevant timestamped evidence;
3. answer in Vietnamese or English with clickable source timestamps;
4. state when the evidence is insufficient instead of fabricating an answer.

## Product principles

- Evidence before fluency
- Reliable baselines before advanced techniques
- Local operation before paid cloud dependencies
- Measured improvement before complexity
- Replaceable providers before vendor-specific application logic
- Inspectable failure before silent fallback

## Target capabilities

### Local V1

- Reliable, idempotent YouTube ingest with real job state
- Vietnamese and English transcript selection and chat
- Timestamp-preserving hierarchical chunks
- Lexical and multilingual dense retrieval with fusion and reranking
- Ollama generation with structured citations
- Transcript viewer, ingest retry, chat, summary, notes, and quiz
- Evidence-first video workspace conforming to `interface-specification.md`
- Reproducible local setup and evaluation dataset

### Product V2

- Cross-video collections and search
- Saved learning artifacts and progress
- Import/export and backup
- Optional local ASR fallback
- Retrieval and answer evaluation dashboard

### Production later

- Multi-user isolation, authentication, quotas, and abuse controls
- PostgreSQL, Qdrant server, external workers, and object storage
- Monitoring, backup/restore, CI/CD, and deployment runbooks

## Non-goals before Local V1

- Microservices or Kubernetes
- Agentic web browsing
- Video frame understanding, OCR, or full multimodal indexing
- Billing and team collaboration
- Supporting many LLM providers with incomplete adapters
- Claiming that every YouTube video can always be ingested

## Success measures

Local V1 is successful when:

- supported fixtures pass the ingest matrix deterministically;
- repeated ingest is idempotent and partial failure never produces `ready` data;
- bilingual retrieval meets thresholds defined by an approved evaluation dataset;
- every grounded answer contains valid chunk and timestamp citations;
- the application can run without a paid API key;
- a clean machine can follow one local setup guide and pass the quality gate.
