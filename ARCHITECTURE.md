# mybro — Architecture & Orchestration

## Intent

mybro is a voice-driven development environment for Apple Silicon Macs. It transforms spoken English into working software by orchestrating a multi-stage pipeline of audio capture, transcription, AI reasoning, and code execution — all optimized for local hardware.

## Pipeline

```
Audio → MLX-Whisper → Haiku Classification → Model Routing → Template Selection
  → Compute Planning → Execution → TTS Feedback
```

### Pipeline Stages

1. **Audio Capture** — CoreAudio via `sounddevice`, WebRTC VAD, 16kHz mono, 30ms frames, ring buffer for pre-speech capture
2. **Transcription** — MLX-Whisper (large-v3) on Metal GPU, <500ms latency on M4 Pro, technical term hints, silence hallucination rejection
3. **Brain** — Claude Opus 4.6 interprets intent, maintains rolling history (30 exchanges), outputs structured JSON (speak/action/confidence/needs_input)
4. **Execution** — Claude Code CLI subprocess, auto-accept mode, 120s timeout, streaming output
5. **Speech** — macOS system TTS (Samantha, 210 WPM), interruptible

### Async Architecture

- janus queues bridge sync sounddevice callback → async event loop
- Three worker tasks: transcription → brain → dispatcher
- State machine: `IDLE → LISTENING → TRANSCRIBING → THINKING → EXECUTING → IDLE`
- Signal-based graceful shutdown
- Status dashboard on port 7777 (WebSocket)

## Three-Tier Model Routing

| Tier | Model | Cost | Latency | Role |
|------|-------|------|---------|------|
| 1 | Haiku 4.5 | ~$0.07/session | ~200ms | Classification, confidence scoring, parameter extraction, interrupt detection |
| 2 | Sonnet 4.5 | ~$1.53/session | ~2s | Template-guided codegen, modifications, docs, error interpretation |
| 3 | Opus 4.6 | Variable | Highest | Ambiguous commands, novel scaffolding, multi-step orchestration, debugging |

```
if trivial_task → Haiku
elif template_match → Sonnet (template constrains output space)
elif novel_architecture → Opus (needs reasoning)
  if opus_46_mode → adaptive_thinking, agent_teams, 1m_context
```

## Compute Routing

Hardware-aware routing across five compute targets:

- **LOCAL_CPU** — Rayon parallelization across P+E cores
- **LOCAL_GPU** — Metal compute shaders (22 prebuilt kernels, 500+ GFLOPS on M4 Pro)
- **LOCAL_ANE** — Neural Engine via CoreML for inference
- **REMOTE_CUDA** — Shadeform cloud GPU for training and large jobs
- **WASM_BROWSER** — Client-side Rust→WASM

Decision thresholds: GPU >50k elements, SIMD >1k elements, checkpointing >10 min, cloud offload >30 min.

## Opus 4.6 Exclusive Features

- **Adaptive Thinking** — Dynamic reasoning budget (low/medium/high/max)
- **Agent Teams** — Parallel Claude Code instances with lead coordinator + specialists
- **1M Context Window** — Full project analysis, cross-repo reasoning
- **128K Output** — Complete scaffolds in a single response
- **Structured Outputs** — JSON schema validation with Pydantic integration

## Monitoring & Diagnostics

- **Status Server** (port 7777) — Real-time WebSocket updates, performance metrics
- **Log Server** (port 7778) — Ring buffer (5000 entries), JSONL, rotating files (50MB × 10)
- **Codebase Doctor** — 50+ automated health checks, security scanning, Opus 4.6 diagnosis, auto-apply fixes

## Configuration Defaults

| Component | Setting |
|-----------|---------|
| Audio | 16kHz mono, 30ms frames, VAD aggressiveness 0-3, 800ms silence timeout |
| Brain | claude-opus-4-6, max_tokens 1024, temperature 0.3 |
| TTS | Samantha voice, 210 WPM |
| Pipeline | Queue sizes: raw=5, transcript=10, action=10 |
| Executor | 120s timeout, auto-accept mode |

## Running

```bash
# Standard mode
python preparation/claude_code_dual.py --mode standard

# Opus 4.6 mode
python preparation/claude_code_dual.py

# Specific command
python preparation/claude_code_dual.py --command "Build a payment processor"

# Codebase Doctor
python preparation/codebase_doctor.py --issue "fix auth bug"
```
