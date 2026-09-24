# llama-project-team-ui

Host-only PySide6 launcher + conservative Task Master planning scaffold for running multiple independent `llama-server` instances safely.

## Architecture boundary

- **Launcher/UI boundary:** manages launcher profiles and process lifecycle (`start/stop/restart/status`) for independent `llama-server` processes and log streams.
- **Task Master boundary:** read-only discovery/planning only. It never auto-creates containers, installs dependencies, or starts servers.
- Independent `llama-server` ports do **not** communicate by themselves. Coordination is handled by Task Master/orchestrator logic.

## Threat model & safety invariants

- No host package management actions (`sudo`, `rpm-ostree`, `dnf`, `apt`, global or `--user` pip installs) are allowed.
- The app detects venv execution. If not in venv, execution actions are blocked and remediation guidance is shown.
- Commands are built as argv arrays, never shell-interpolated strings.
- Default bind host is `127.0.0.1`; non-loopback binding requires explicit confirmation.
- Start/stop/restart/remove are explicit confirmation-gated actions.
- Task Master only proposes command argv and rationale.
- State/config/cache/logs are stored under XDG user directories.
- Audit log captures timestamp, action, argv, approval, exit status, workspace/container references.

## Install (private venv only)

```bash
python -m venv ~/.local/venvs/llama-project-team-ui
~/.local/venvs/llama-project-team-ui/bin/python -m pip install -e .[dev]
```

Run:

```bash
~/.local/venvs/llama-project-team-ui/bin/llama-project-team-ui
```

## Configure

- Copy `examples/config.example.json` into your config path:
  - `${XDG_CONFIG_HOME:-~/.config}/llama-project-team-ui/config.json`
- Fresh profiles should use the portable default `~/.local/bin/llama-server-cuda13` for **llama-server Binary**.
- Set your own model roots and workspace roots.
- Model scanning for `.gguf` is limited to configured roots only.
- Existing saved profiles keep their current `llama_server_path`; update older profiles through the UI if they still point at an LM Studio backend.

Create the expected wrapper at `~/.local/bin/llama-server-cuda13`:

```bash
cat <<'EOF' > "$HOME/.local/bin/llama-server-cuda13"
#!/usr/bin/env bash
set -euo pipefail

CUDA_HOME="$HOME/.local/cuda-13.4.1/linux-x86_64"
BUILD="$HOME/Projects/llama.cpp/build-cuda-5090"

export LD_LIBRARY_PATH="$CUDA_HOME/lib:$BUILD/bin${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

exec "$BUILD/bin/llama-server" "$@"
EOF

chmod +x "$HOME/.local/bin/llama-server-cuda13"
```

This repository does not bundle user-specific CUDA installs, model paths, or build directories beyond that per-user wrapper example; the saved launcher path should point to the wrapper, not directly to an LM Studio backend under `.lmstudio/extensions/backends/...`.

## Multi-port profiles and roles

Available role presets:
- Task Master
- Architect
- Implementer
- Reviewer
- Test/Debug
- Vision Specialist
- Custom

Each profile stores role/model/host/port/context/gpu layers/start mode/idle policy separately.
Use **Open Another Window** to run additional independent launcher windows.

## Task Master behavior (toggle)

When enabled, Task Master performs **read-only**:
1. workspace discovery and language/tooling hints,
2. isolation option detection (`.venv`, Podman, Distrobox availability/containers),
3. recommendation + exact proposed command argv,
4. GGUF inventory scan from configured roots,
5. explainable role recommendations with confidence + missing metadata.

No side effects are executed automatically.
When proposing container creation, host driver/operational paths are mounted as read-only (`:ro`) only.

## Context quality safeguards

`ContextPolicy` supports:
- `ctx_size`, output reserve, safety margin,
- compact threshold and hard-stop threshold.

`StructuredCheckpoint` (Pydantic schema) includes objective, completed work, decisions, current state, relevant files, commands/results, remaining work, risks/questions, and next-agent instruction.
Role suggestions also include a context budget breakdown from role-specific percentages of model context capacity (`reserve_output_tokens`, `compact_at_tokens`, `hard_stop_at_tokens`, `max_response_tokens`).
Each model/role budget includes guardrail checks derived from global percentages (not hardcoded absolute constants) to flag common misconfiguration risks such as threshold ordering errors or oversized response limits.

## Autostart example

Use `examples/llama-launcher-autostart.desktop.example` and point `Exec/TryExec` to your private venv Python. It starts GUI only and does not auto-start servers.

## Limitations in this MVP

- Container actions are recommendation-only (no automatic create/enter).
- GGUF metadata extraction prefers `gguf` Python package when available, otherwise heuristic fallback with lower confidence.
- Role recommendations are deterministic heuristics and intended to be conservative and explainable.
