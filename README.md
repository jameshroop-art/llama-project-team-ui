# llama-project-team-ui

Private-use, local-first multi-role model workspace. Local models perform workspace execution; optional online research supplies concepts through a local instruction adapter, never direct tool access.

## Architecture and current status

[DESIGN.md](DESIGN.md) is the canonical architecture and phased implementation plan. [SECURITY.md](SECURITY.md) defines trust boundaries, safety requirements, and reporting guidance.

```text
Optional online research → concept dossier → local instruction adapter
  → approved task cards → local role models → proposed changes → approval
  → local preview → screenshot / VLM visual QA loop → review / checkpoint
```

**Implemented today:** a host-only PySide6 launcher for independent `llama-server` processes, profile configuration, start/stop/restart/status and logs, read-only Task Master discovery/planning, GGUF inventory and role recommendations, context-budget helpers, and a structured checkpoint schema.

**Planned, not implemented:** online research clients, concept dossiers and task-card adaptation, automated role handoffs, workspace editing, Node orchestration and Vite preview, reference retrieval, screenshot-based verification, live token/VRAM counters, automatic compaction, and role LoRA management/training. Independent server ports do not coordinate themselves. No online research provider is required or configured by this launcher.

Also planned: keyword noun/action extraction, ordered request **CHUNKS**, mount-time diagnostics cached in recallable profiles keyed by model hash-ID, step-by-step research coverage and concept approval, and optional sandboxed VSCodium editing/terminal collaboration. These are design requirements, not available launcher operations.

## Install and run (private venv only)

From the repository root, with Python 3.11 or newer:

```bash
python -m venv ~/.local/venvs/llama-project-team-ui
~/.local/venvs/llama-project-team-ui/bin/python -m pip install -e '.[dev]'
~/.local/venvs/llama-project-team-ui/bin/llama-project-team-ui
```

Install a compatible `llama-server` and obtain local GGUF models separately; the app does not download them or install host packages.

## Configure and use the launcher

1. Copy [`examples/config.example.json`](examples/config.example.json) to `${XDG_CONFIG_HOME:-$HOME/.config}/llama-project-team-ui/config.json` (create the parent directory if needed).
2. Set your own model roots, workspace roots, and approved workspace roots. GGUF scanning is limited to configured model roots.
3. Set each profile's `llama_server_path`, `model_path`, host, port, context size, and GPU layers. The server path is empty by default and must point to your installed executable.
4. For a compatible vision model, also set `projector_path`. This enables the launcher's `--mmproj` argument, not a complete visual QA workflow.
5. Start the GUI in its venv, review the profile, and explicitly approve process actions. Enable Task Master for read-only workspace/tooling discovery and model recommendations.

Role presets are Task Master, Architect, Implementer, Reviewer, Test/Debug, Vision Specialist, and Custom. Multiple roles may use the same model; each profile has independent process settings. **Open Another Window** opens another launcher window, not a coordinated agent team.

Task Master only proposes isolation choices and command argv with rationale. It never creates containers, installs dependencies, or starts servers automatically. Container recommendations use read-only mounts for host driver/operational paths. Start-mode and idle-policy fields are configuration scaffolding, not an implemented automatic model scheduler.

Config, state, cache, and logs use XDG user directories. Process start/stop audit records include approval and execution details; they are not yet a full task or research audit trail.

## Intended workspace workflow

The phased workflow in DESIGN.md starts with one user, one project, and one active task:

1. Preserve the original request; extract keyword nouns/actions and a concept summary, retaining every constraint in ordered requirement-linked chunks.
2. Diagnose mounted models, recall hash-keyed profiles, and budget/re-tokenize chunks against current effective limits. Relay context incrementally in request order.
3. Optionally search approved public keywords and extract text/relevant images into a cited dossier. Track coverage of every requested step; research gaps within bounded budgets or report blockers. Offline intake remains possible.
4. Obtain user verification of the concept, then collaborate with local LLM/VLM roles on a plan for the specified sandbox. Approve task cards separately from writes, dependency changes, and terminal operations; optional VSCodium integration uses the same sandbox and approval broker.
5. Verify with existing checks and a bounded screenshot-based visual QA loop.
6. Save checkpoints before context pressure or model swaps; track tokens and VRAM rather than silently dropping history.

References include screenshots, docs, URLs, code samples, and style guides. Keep their provenance and distinguish must-follow constraints from inspiration or negative examples. Role specialization begins with prompts and retrieval; optional LoRAs change behavior, not workspace policy or project memory.

## Context quality safeguards

`ContextPolicy` evaluates caller-supplied token usage against output reserve, safety margin, compaction, and hard-stop thresholds. Role suggestions derive budgets from context capacity and percentages, with warnings for threshold ordering and response-limit misconfiguration. These helpers do not measure a running server's context or automatically compact it.

`StructuredCheckpoint` defines objective, completed work, decisions, current state, relevant files, commands/results, remaining work, risks/questions, and next-agent instruction. Live counters, checkpoint persistence/resume, and VRAM admission controls are planned in DESIGN.md.

## Safety and limitations

- Always run locally in a private venv. The UI's Start action checks for one, but Restart currently does not repeat that check. A venv is not a security sandbox.
- Commands use argv arrays without shell interpolation. Host package management and global/`--user` pip installs are prohibited execution actions.
- Default bind host is `127.0.0.1`; non-loopback binding requires explicit confirmation and is outside the intended private-use deployment.
- Start/stop/restart/remove actions require confirmation. Future writes must be approval-gated and confined to the selected workspace.
- Treat web content, model output, and reference files as untrusted. No secrets or workspace content should leave the machine by default.
- GGUF metadata uses the optional `gguf` package when available, otherwise lower-confidence heuristics. Recommendations are not proof of vision support or memory fit.

For GUI autostart, adapt [`examples/llama-launcher-autostart.desktop.example`](examples/llama-launcher-autostart.desktop.example) to your private venv Python. It does not auto-start servers.

## Development checks

The existing tests run with `~/.local/venvs/llama-project-team-ui/bin/python -m pytest`. There is no dedicated documentation test or lint configuration; documentation-only changes require link, terminology, and implementation-accuracy review.
