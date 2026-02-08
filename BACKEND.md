# mybro — Backend

## Stack Rules

| Need | Use | Never |
|------|-----|-------|
| Web backend | FastAPI | Flask, Express.js |
| Performance-critical | Rust | — |
| ML inference | MLX (preferred) or PyTorch+MPS | CUDA |
| GPU compute | Metal shaders | CUDA |
| Web DB | PostgreSQL | — |
| Local DB | SQLite | — |
| Cache | Redis | — |
| Payments | Stripe | — |
| AI/Analysis | Anthropic Claude API | — |
| HTTP client | httpx | requests (for async) |
| Serverless | Vercel Edge Functions | — |
| API (lightweight) | Hono + Cloudflare Workers | — |

Forbidden: CUDA, Docker (for dev), Electron, Flask, Express.js, CRA, jQuery, Webpack.

## Core Modules

### Voice Pipeline
| Module | Role |
|--------|------|
| `audio.py` | CoreAudio capture via sounddevice, WebRTC VAD, ring buffer |
| `transcribe.py` | MLX-Whisper large-v3, Metal GPU inference, <500ms latency |
| `brain.py` | Opus 4.6 intent interpretation, structured JSON output |
| `pipeline.py` | Async orchestrator, janus queues, state machine, interrupt handling |
| `executor.py` | Claude Code CLI subprocess management |
| `speak.py` | macOS TTS, interruptible, background tasks |

### Intelligence
| Module | Role |
|--------|------|
| `rules_v2.py` | Technology mandates and forbidden stacks |
| `compute_rules.py` | Hardware detection, workload classification, compute routing |
| `codebase_doctor.py` | 50+ health checks, security scanning, auto-fix |
| `codegen_decision_logic.md` | SSR/static/client, DB selection, API design patterns |
| `instant_codegen_patterns.md` | Pre-configured stacks with copy-paste components |

### Infrastructure
| Module | Role |
|--------|------|
| `shadeform_integration.py` | Cloud GPU selection, price optimization, lifecycle management |
| `github_manager.py` | Repo management, PR automation |
| `github_extraction_system.py` | Cross-repo feature extraction (1M context) |
| `package_manager.py` | UV package management (10-100x faster) |
| `status_server.py` | WebSocket monitoring dashboard (port 7777) |
| `logging_config.py` | Ring buffer, JSONL logs, rotating files (port 7778) |
| `benchmark_suite.py` | Hardware capability assessment |

## Metal Kernel Library (22 Kernels)

| Category | Kernels |
|----------|---------|
| Reductions (7) | sum, mean, min, max, L2, variance, histogram |
| Maps (11) | exp, log, sigmoid, tanh, add/sub/mul/div, relu, abs, neg |
| Transforms (4) | scan, compact, transpose, repack |
| Fused | map_reduce_square_sum, abs_sum, masked_sum, threshold_count |
| Quantization | f32↔i8 |
| Batched | dot product, cosine similarity |

Performance: 500+ GFLOPS on M4 Pro.

## Production Templates (Backend-Heavy)

### vercel-serverless (from EZBTC)
- TypeScript, Vercel Edge Functions
- Crypto integrations, scales to millions
- Zero-config deployment

### photo-analyzer (from eBay)
- Python FastAPI + Claude Vision API
- Perceptual hashing, OCR, object detection
- Similarity search, image cataloging

### research-paper (internal)
- Python + LaTeX + BibTeX
- Web (MDX) and PDF output
- Citation management

### metal-compute (internal)
- Rust + Metal shaders
- 22 optimized kernels
- GPU compute scaffolding

### checkpoint-compute (from milk_sad)
- Rust + Rayon
- Resumable long computations (24+ hours)
- Automatic checkpointing, fault tolerance

## Cloud GPU (Shadeform)

- Price-aware GPU selection (A100, H100, RTX 4090)
- Budget constraints and cost optimization
- Instance lifecycle: provision → run → teardown
- Automatic fallback for workloads exceeding local capacity
- Region preference, NVLink support, multi-GPU

## Dependencies

**Core:** anthropic, mlx, mlx-whisper, sounddevice, webrtcvad, rich, pynput
**Web:** fastapi, uvicorn, flask, flask-cors
**Data:** aiosqlite, pillow, imagehash, numpy
**Cloud:** httpx, paramiko
**Dev:** pytest, black, ruff

## API Design Patterns

- REST for CRUD, WebSocket for real-time
- Structured error responses with codes
- Rate limiting at the edge
- Auth: JWT for APIs, session for web
- Versioning via URL prefix (`/v1/`)
