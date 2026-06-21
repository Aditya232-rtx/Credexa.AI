# Technology Head Review: Progress and Critique

**Date:** June 21, 2026
**Reviewer:** Head of Technology
**Subject:** Infrastructure Overhaul & OCR Modernization

## 1. Executive Summary
We have successfully transitioned the backend from a synchronous SQLite-based prototype to a robust, asynchronous architecture utilizing **PostgreSQL** and **Celery with Redis**. Furthermore, we eliminated the reliance on raw text-only OCR and cloud APIs by integrating **LayoutLMv3** locally for semantic key-value extraction, enabling superior document understanding entirely on-premise.

While the foundation is vastly improved, the system is not yet fully production-ready. Below is my honest critique and rating of our current progress across phases.

---

## 2. Phase-by-Phase Evaluation

### Phase 1: Core Infrastructure Overhaul (Rating: 8/10)
**Progress:**
- Migrated the primary datastore from SQLite to PostgreSQL.
- Implemented Celery with a Redis broker to handle long-running document analysis tasks asynchronously.
- Refactored `case_pipeline.py` and `api/main.py` to seamlessly enqueue and process tasks without blocking the main event loop.

**Critique & Areas to Improve:**
- **Containerization Gap:** We are currently relying on local Homebrew installations for PostgreSQL and Redis. For production (and even consistent development), we *must* introduce Docker and a `docker-compose.yml` file to orchestrate the API, Celery worker, Redis, and Postgres together.
- **Connection Management:** The current implementation creates a new PostgreSQL connection per task via `psycopg2.connect`. At scale, this will exhaust connection limits. We need to implement a connection pool (e.g., using `psycopg2.pool` or `PgBouncer`).
- **Error Resiliency:** If a Celery worker crashes midway (as seen during the PyTorch fork issue), the case gets stuck in `processing`. We need robust retry mechanisms, task timeouts, and a Dead Letter Queue (DLQ) for failed cases.

### Phase 2: Local AI & Ingestion (Rating: 7/10)
**Progress:**
- Successfully integrated the `nielsr/layoutlmv3-finetuned-funsd` model into our `ocr.py` pipeline.
- Achieved local, cloud-free semantic labeling (B-HEADER, I-ANSWER, etc.) mapped directly to bounding boxes and text extracted via PyTesseract.

**Critique & Areas to Improve:**
- **Inference Bottleneck:** Running LayoutLMv3 inference on the CPU inside a Celery worker is computationally expensive and slow. We need to explore optimizations like exporting the model to ONNX Runtime, quantization, or utilizing Apple Silicon (MPS) / dedicated GPUs.
- **Memory Footprint:** Loading a 500MB Transformer model per worker process will scale poorly. If we increase concurrency, we risk OOM errors. A dedicated inference service (like Triton or FastAPI model server) would be a better microservice separation than embedding it directly in the generic Celery worker.
- **OCR Accuracy:** PyTesseract is still the underlying engine for raw text before LayoutLMv3 consumes it. PyTesseract struggles with handwriting or low-quality scans. We should evaluate integrating `docTR` or PaddleOCR as a superior raw-text extractor before the LayoutLM pipeline.

---

## 3. Strategic Action Items
1. **Immediate:** Add a `docker-compose.yml` to standardize the stack.
2. **Short-term:** Optimize the Celery worker pooling and implement PostgreSQL connection pooling.
3. **Mid-term:** Offload LayoutLMv3 to a dedicated microservice running ONNX for faster, parallel inference.

*Overall, excellent progress. The architecture is significantly more mature than last week. Let's harden these systems before scaling.*
