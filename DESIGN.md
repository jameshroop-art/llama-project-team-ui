# Private local model workspace: architecture and design

This is the canonical design for a private-use, local-first multi-role model workspace. It is an implementation plan, not a claim that the complete pipeline exists. The current Python/PySide6 launcher manages independent local `llama-server` processes and provides conservative, read-only planning. [README.md](README.md) documents what can be run today; [SECURITY.md](SECURITY.md) specifies trust boundaries.

## 1. Scope and product boundaries

Target one user, one selected project, and one active execution thread first. Local role models plan, implement, review, and verify small changes or a scoped Vite application. Optional online research gathers public resources; it never executes workspace tools. An offline path accepts a user-authored concept dossier and local references.

Before work starts, capture:

- Objective, target app type, screens/components, and small-change versus new-app mode.
- Must/should/could features, explicit non-goals, stack constraints, and files in scope.
- Acceptance criteria covering behavior, visual targets, responsiveness, and existing checks.
- Reference priorities, dependency/license constraints, risks, unresolved questions, and approvals.
- Available models, vision capability, context budgets, VRAM headroom, and iteration limits.

Resolve blocking questions before generating executable task cards. Initial non-goals are hosted deployment, remote multi-user access, autonomous host administration, concurrent agent swarms, arbitrary plugins, and training infrastructure.

## 2. Layer separation and data flow

```text
User goal + public context
          |
          v
Optional online research layer (search / fetch / concept synthesis)
          | untrusted concept dossier + immutable source records
          v
Local instruction adapter (schema / policy / decomposition / approval)
          | approved, bounded task cards
          v
Local orchestrator -> Architect / Implementer / Reviewer / Test-Debug
          | proposed diffs -> approval -> confined workspace execution
          v
Local preview -> screenshot -> Vision Specialist -> findings -> repair card
          |
          v
Acceptance checks / stop / checkpoint

Cross-cutting: reference retrieval, audit, token counters, context compaction,
checkpoints, and VRAM-aware model admission / unloading.
```

### Research layer: online gathering, not execution

Use a replaceable provider client and explicit search/fetch tools. Free-tier APIs are optional candidates, not a guaranteed availability, privacy, context-size, or cost contract. Check current terms, retention/training policies, quotas, and suitability before enabling a provider. Network access follows SECURITY.md, including explicit outbound approval and no silent provider fallback.

Produce a **concept dossier** with a run ID, objective, feature priorities and acceptance criteria, architecture/modules/data flow, UI specification, candidate dependencies with rationale, alternatives, risks, open questions, and cited source IDs. Record source URLs, retrieval times, content hashes, and relevant licensing.

Preserve permitted raw sources and provider responses locally with provenance; never overwrite them with summaries. “Non-pruning” means retaining the collected evidence, not promising unlimited provider output or bypassing provider policy. Detect truncation, use bounded continuation/retry with deduplication, and mark incomplete dossiers. Respect rate limits and source access restrictions. Exhausted quota or missing evidence pauses the run rather than silently dropping requirements.

### Instruction adapter: local policy boundary

The instruction adapter translates research into direct instructions using code-first validation and policy checks. An optional local model may help phrase or decompose tasks, but it cannot authorize operations. This adapter is a protocol/policy layer, not an image-conditioning adapter.

1. Validate a versioned dossier schema, source references, required fields, and completeness.
2. Treat every source and model response as untrusted data. Separate quoted evidence from instructions; flag injection attempts and conflicting requirements for review. String filtering alone cannot establish trust.
3. Reconstruct proposed operations from approved tool definitions and argv templates; never pass through commands from research.
4. Enforce workspace policy, permitted paths/tools, outbound restrictions, and dependency/license review.
5. Split features into dependency-ordered task cards that fit each role's input/output budget.
6. Present scope, policy failures, proposed commands, and required permissions for human approval. Block rejected or unresolved cards.
7. Audit dossier/card hashes, policy version, approvals, results, and checkpoints locally without secrets.

Each **task card** must carry:

| Field | Purpose |
| --- | --- |
| ID, dossier ID/hash, policy version | Provenance and reproducible validation |
| Role, objective, ordered instructions | One bounded responsibility |
| Workspace-relative files in scope | Explicit read/write limits |
| Allowed tool operations and command argv | Validated capabilities, not shell text |
| Acceptance criteria and check commands | Observable completion |
| Reference IDs and approved excerpts | Grounding with source traceability |
| Dependencies and expected outputs | Controlled handoffs |
| Input/output token budgets, iteration limit | Resource and stop conditions |
| Approval record and base revision | Bind permission to the exact proposal |

Source IDs are pointers to controlled retrieval, not permission to fetch arbitrary URLs or inline entire documents. Revalidate cards after edits to scope or policy. Planning approval is not blanket authorization for later writes.

### Local roles and orchestration

The proposed Node/TypeScript orchestrator owns routing, tool validation, approval state, task transitions, and streaming events to a proposed Vite UI. The Python launcher remains responsible for model process lifecycle; reuse validated profile configuration instead of maintaining a second model map. Version any cross-process interface explicitly.

Roles communicate through task cards, results, and checkpoints—not by assuming independent server ports coordinate:

| Role | Responsibility and handoff |
| --- | --- |
| Task Master | Schedule ready cards, track budgets/approvals, checkpoint and stop |
| Architect | Decompose scope, define interfaces, record decisions and risks |
| Implementer | Propose minimal scoped diffs, identify affected checks |
| Reviewer | Find defects/regressions, check policy and acceptance criteria |
| Test/Debug | Interpret local check results and produce bounded repair requests |
| Vision Specialist | Compare screenshots to references and return visual findings |

Configure each role's model/profile, fallback, prompt, context budget, sampling, maximum output, and allowed modalities. One capable coding model may serve several roles serially; distinct roles do not require simultaneous model residency. Verify endpoint health and actual capabilities before dispatch. Missing vision support blocks visual verification rather than reporting a text-only pass.

Use explicit states: scoped → adapted → approved → running → awaiting-write-approval → verifying → completed/blocked/cancelled. Stop on acceptance, cancellation, policy failure, resource pressure, repeated failed repairs, or the iteration/time budget. Checkpoint before switching roles or models.

## 3. References and grounding

Keep project-scoped reference records with ID, type, local location or source URL, hash, timestamp/version, provenance/license, sensitivity, tags, and intended use:

- **Screenshots/sketches:** retain originals, dimensions, viewport, and user notes; derive OCR/captions with provenance.
- **Docs/Markdown/PDFs:** extract bounded text with headings/page locations; preserve source versions.
- **URLs:** fetch only through the research boundary; store approved snapshots so local work can continue offline.
- **Code samples/repositories:** import selected files read-only, record revision/license, and never execute examples or install hooks automatically.
- **Style guides/design tokens:** extract explicit typography, color, spacing, component, and accessibility constraints.

Mark references as hard/must-follow, soft/inspiration, negative/avoid, or historical. Ask the user to resolve conflicts. Start with explicit IDs/tags and bounded excerpts; add semantic retrieval only when justified. Local roles receive adapter-approved excerpts, not raw web instructions. Record what was retrieved and why, including what to emulate or avoid. Retrieve within the role budget and retain links to originals outside active context.

## 4. Screenshot-based visual QA loop

For each approved code revision:

1. Run the local preview on loopback with controlled dependencies and network access.
2. Capture deterministic viewport(s) using a planned browser automation tool such as Playwright. Record route, revision, timestamp, viewport, and screenshot hash.
3. Confirm the VLM's image capability and compatible GGUF/projector setup. The launcher can pass `--mmproj`; filename/metadata heuristics alone do not verify image support.
4. Send a bounded image payload plus a specific question, reference IDs, and visual acceptance criteria to the local VLM. Account for image tokens; crop/tile large images and preserve coordinates.
5. Return structured findings: criterion, region, expected versus observed result, severity, uncertainty, and suggested file/component.
6. Route actionable findings into a repair card, obtain approval for changes, rerun checks, and recapture after the revision changes.

Bound repair passes and stop if evidence is stale or inconclusive. VLM findings are advisory; they do not replace functional tests, accessibility checks, or human acceptance. Screenshots and rendered page text remain untrusted inputs.

## 5. Context compaction, counters, and checkpoints

Existing foundations are `ContextPolicy`, percentage-derived role budgets with guardrail warnings, and the Pydantic `StructuredCheckpoint` schema. They do not currently collect live usage, persist checkpoints automatically, or enforce execution budgets.

The orchestrator must track per role/session:

- Tokenized input including system prompt, tools, checkpoint, card, retrieved references, history, and image cost.
- Output usage, reserved output, safety margin, and remaining effective context capacity.
- Per-card cumulative tokens and turns since checkpoint (distinct from currently occupied context).
- Server slot/KV occupancy when supported, plus free/used GPU memory and model residency.

Use the active model's tokenizer and response usage where available. Capability-check version-dependent server APIs such as `/tokenize`, `/slots`, and `/props`; unavailable measurements must be shown as unknown or conservative estimates, never exact counters. GPU telemetry is hardware-specific. Context length alone is not a VRAM measurement.

Before every request, ensure input + reserved output + safety margin fits the hard-stop budget and effective server context. Compact at the configured role threshold; hard stop before overflow. Existing defaults and role percentages differ: roughly 60–70% compaction and 74–80% hard stop are starting points for role budgets, not replacements for the current `ContextPolicy` defaults or universal accuracy guarantees. Surface guardrail warnings and validate threshold ordering.

Compaction must:

1. Persist a structured checkpoint containing objective, completed work, decisions, current state, relevant files, commands/results, remaining work, risks/questions, and next-agent instruction.
2. Associate it with card/source IDs, policy/model versions, approvals, and workspace revision.
3. Validate it before replacing active history. Retain originals locally; compaction is not deletion of evidence.
4. Resume with system policy + checkpoint + current card + bounded retrieved context; re-tokenize before dispatch.

If the checkpoint cannot be produced or the fresh request still cannot fit, pause and split the card or request human guidance. Never silently truncate policy, acceptance criteria, or unresolved risks.

## 6. VRAM-aware local model management

Admit work only with sufficient measured/estimated headroom for model weights, KV cache, image/projector buffers, output, and adapters. Queue work or unload idle roles before loading another model; avoid repeated out-of-memory retries. Preserve checkpoints before unloading.

Start with serial execution and small per-role context allocations. Load the VLM on demand. Evaluate quantization, KV-cache formats, flash attention, and slot persistence only when the selected backend/model supports them; measure accuracy and memory before enabling. Do not assume fixed flags or a universal slot/context allocation formula across server versions. Show configured budgets, measured consumption, estimate confidence, and reasons for admission failure.

The launcher's GPU-layer and context settings are existing controls; automatic residency scheduling, live VRAM telemetry, and idle unloading remain planned.

## 7. Role specialization and LoRAs

Start with role prompts, retrieval, schemas, and evaluations. LoRAs are optional behavioral specialization for decomposition, scoped patch generation, defect detection, domain style, or visual critique—not storage for project state, references, secrets, or policy.

When justified by evaluation, register each adapter with its hash/version, license, base-model/tokenizer compatibility, role, training provenance, resource cost, and evaluation results. Verify runtime adapter support; vision tuning also requires compatible multimodal components. Switch only between tasks, checkpoint first, and fall back to the validated prompt-only configuration if incompatible.

Collect only explicitly approved, locally retained examples: input context, role instructions, desired output, accepted result, and optional rejected-output critique. Remove secrets and confirm reuse rights before export/training. Keep held-out projects separate from training data. Compare role-specific metrics (plan completeness, patch/test correctness, review precision, visual finding accuracy), resource use, and policy compliance against the base model. Promote versioned adapters only after review, with rollback available. No adapter or model can bypass approval or tool policy.

## 8. Security boundaries

Apply [SECURITY.md](SECURITY.md) at each tool boundary, independent of prompts or LoRAs. Research has no workspace credentials or tools; the adapter cannot grant itself permissions; local roles propose operations; deterministic tools enforce approved scope. Local-only execution is compatible with optional online research, but does not mean the entire system is always offline.

## 9. Phased implementation and exit criteria

| Phase | Deliverable | Exit criteria / exclusions |
| --- | --- | --- |
| 0 — current foundation | Python launcher, profiles, read-only discovery, context/checkpoint schemas | Verify local launch and safety checks; no autonomous execution claims |
| 1 — local vertical slice | One project, offline dossier intake, adapter/task-card validation, approval UI, local role routing, scoped diffs, Node/Vite preview, checkpoint persistence | One small change completes existing checks and can resume; writes denied outside scope; no online provider or training required |
| 2 — references and visual QA | Project reference store, bounded retrieval, verified image input, screenshots and bounded repair loop | Trace findings to source and revision; report unsupported/inconclusive QA honestly |
| 3 — optional online research and resource controls | Approved provider/search/fetch clients, retained dossiers, outbound policy, live counters, compaction and VRAM admission | Demonstrate injection rejection at tool boundaries, no default private-data egress, quota/truncation handling, and safe resource-pressure pause/resume |
| 4 — measured specialization | Role evaluation, optional adapter registry, curated dataset export and local training workflow | Held-out improvement, compatibility/license checks, explicit data consent, and rollback |

Each phase must preserve offline operation and include regression tests for its new interfaces and trust boundaries. Basic budget admission is required before execution in phase 1; richer telemetry arrives in phase 3. Defer multi-project scheduling, collaboration, plugins, and broad indexing until the single-project workflow is reliable. This documentation change does not scaffold these future components or alter current runtime behavior.
