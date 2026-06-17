# Installation

## From PyPI after release verification

```bash
pip install slate-ai
```

Use this command only after the launch checklist verifies the package from a
clean virtual environment.

## From a local source checkout

```bash
cd slate
pip install -e ".[dev]"
```

## Backend setup

Slate ships with local and cloud VLM provider drivers. You configure the lanes you want.

### Local Gemma via Ollama (free)

1. Install Ollama from <https://ollama.com>
2. Pull the model and start the server:
   ```bash
   ollama pull gemma4:latest
   ollama serve
   ```
3. Slate auto-detects `http://localhost:11434`. Override via the `OLLAMA_URL` env var.

### NVIDIA NIM (cloud, BYO key)

1. Get an API key from <https://build.nvidia.com>
2. Export it:
   ```bash
   export NVIDIA_API_KEY=replace-with-nvidia-api-key
   ```
3. Slate uses these models by default; override with CLI flags:
   - Primary: `nvidia/nemotron-nano-12b-v2-vl`
   - Cross-check: `meta/llama-3.2-90b-vision-instruct`

You pay NVIDIA directly. Slate never sees your key or your frames.

## Verifying the install

```bash
slate --version
slate verify --help
```

If both work, you are ready to verify your first shot — see [quickstart.md](quickstart.md).
