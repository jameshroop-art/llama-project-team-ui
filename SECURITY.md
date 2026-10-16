# Security and trust boundaries

This project targets private, single-user, local-first use. It is not a hardened remote service or an isolation boundary against a hostile local user. [DESIGN.md](DESIGN.md) defines the target architecture; [README.md](README.md) distinguishes implemented launcher behavior from planned workspace features.

## Current controls and limitations

- The UI blocks execution actions outside a Python virtual environment. A venv isolates dependencies, not filesystem access, processes, or networking.
- Server commands are constructed as argv arrays, not shell-interpolated strings. Validation rejects selected host package-management commands, pip-install patterns, and shell markers; this is not a general-purpose sandbox.
- Profiles default to `127.0.0.1`. Non-loopback binding requires confirmation; private-use deployments should retain loopback and avoid exposing model or preview ports.
- Start/stop/restart/remove actions require confirmation. Process start/stop audit entries record approval and execution details, not every UI/config operation.
- Task Master is read-only discovery/planning: it does not create containers, install dependencies, or launch recommended commands. Container recommendations mount host driver/operational paths read-only.
- GGUF scans use configured roots, and a resolved-path workspace validation helper exists. There is no implemented agent file-editing service or complete workspace confinement sandbox.
- Research networking, task-card approval enforcement, preview isolation, live resource admission, and automatic compaction are design requirements, not current guarantees.

## Required boundaries for workspace implementation

### 1. Online research and outbound policy

Research providers, search results, redirects, fetched pages, repositories, and model responses are untrusted. The research layer must have no workspace write tools, local execution tools, or workspace credentials.

Online access is opt-in per run. Default outbound content is only the user-reviewed goal and public context. Do not send workspace code, private references, screenshots, local paths, logs, checkpoints, or secrets by default. Sharing specific non-secret private material requires explicit, itemized approval of payload and destination. Credentials must never be included in model prompts.

Approve providers and search/fetch destinations explicitly, including their retention/training terms. Provider fallback must remain within the approved destination/data policy; otherwise pause for approval. Offline work must not silently trigger network requests.

Restrict fetch tools to approved HTTP(S) destinations, bound response sizes/time/retries, and validate every redirect and resolved address. Block loopback, private/link-local networks, cloud metadata endpoints, and local file schemes; recheck at connection time to address DNS rebinding. Local model endpoints belong to a separate tool boundary, never the generic web fetcher. Do not execute downloaded scripts, page instructions, or repository hooks. Enforce network restrictions at the execution boundary, not only through prompts.

### 2. Untrusted content and the instruction adapter

Treat web text, docs, code comments, screenshots/OCR, retrieved excerpts, model output, and imported checkpoints as data, never authority. Preserve provenance while separating evidence from policy and instructions.

Validate dossier and task-card schemas, source IDs, policy versions, scope, and budgets locally. Flag conflicting or injected instructions; quarantine unresolved content for review. Sanitization and prompt wording cannot reliably eliminate injection. Deterministic capability checks must reject unauthorized operations even if a model follows malicious content.

Local roles receive only approved task instructions and bounded evidence through controlled retrieval. A reference marked “must-follow” cannot override workspace policy. LoRAs and role prompts confer no extra permissions.

### 3. Approval-gated operations and workspace confinement

Show proposed diffs, paths, command argv, dependencies, network needs, and risks before execution. Bind approval to the exact proposal, workspace/base revision, and policy version. Revalidate immediately before applying; changed proposals or stale revisions require new approval.

Confine reads and writes to explicitly approved project scope, with separate read-only access for approved references/model assets. Resolve paths and check containment; reject traversal, unsafe absolute paths, symlink escapes, and writes through substituted paths. Recheck at use time and use race-resistant filesystem operations. Do not let generated code access launcher configuration, credential stores, other projects, or unrestricted host mounts.

Keep writes staged/reviewable and checkpoint before mutations. Dependency installs, destructive operations, and changes to scope require explicit approval. Do not treat a planning approval as blanket permission for future edits or package scripts. Audit approvals and results with sensitive values redacted.

### 4. No shell interpolation or host administration

Invoke only allowlisted executables with validated argv arrays, a controlled working directory, and a minimal environment. Never pass model text to a shell, `eval`, command substitution, or an interpreter as arbitrary executable code. Argv arrays avoid shell expansion but do not prevent dangerous executable options or malicious package lifecycle scripts; validate semantics too.

No `sudo`, host package management, or global/`--user` pip installs may be agent execution actions. Install application dependencies manually inside the private venv as described in README.md. Future project dependency changes require approval, version/license review, and controlled lifecycle-script/network behavior.

### 5. Local processes, previews, and model assets

Keep model endpoints, the orchestrator, UI, and preview on loopback. A future web UI/API must enforce origin/Host checks and authorization for mutating requests; loopback alone does not prevent malicious websites from targeting local services. No public bind or remote multi-user deployment is supported by this design.

Generated applications, their dependencies, preview servers, and browser pages can execute hostile code. Use least-privilege process/container isolation with bounded resources, no credentials, narrowly scoped mounts, and controlled network access before executing generated code. Read-only driver mounts alone are not a sandbox; avoid privileged containers and host socket mounts. Restrict iframe/browser permissions and block preview/browser access to local control endpoints.

Obtain model weights, projectors, and LoRAs from trusted sources; record hashes, compatibility, and licenses. Treat loaders and custom model code as executable attack surfaces. Model recommendations or successful loading do not establish trust.

### 6. Local storage, checkpoints, and resource safety

Use private XDG config/state/cache locations and project-scoped stores with restrictive permissions. Store API credentials in an OS credential store or a protected configuration outside the repository, never source control, task cards, screenshots, or audit logs. Do not claim local storage is encrypted by the application; use OS disk encryption and appropriate backups if needed.

Research archives, references, logs, and checkpoints may contain sensitive content. Retain provenance without recording secrets, provide deliberate retention/deletion controls, and require consent before dataset export or training. Do not upload diagnostics automatically.

Validate checkpoint provenance, workspace revision, scope, and policy on resume; restoring a checkpoint must not restore stale approvals as new authorization. Persist and validate checkpoints before compaction or model unloading. Fail closed when token budgets, image costs, or VRAM headroom cannot be established conservatively. Resource exhaustion must pause work, not bypass safeguards or discard constraints silently.

## Reporting a security issue

Do not include credentials, private workspace files, or exploit payloads targeting live systems in public issues. Use GitHub private vulnerability reporting for this repository if enabled. Otherwise, open a minimal issue requesting a private contact channel without disclosing vulnerability details.

Privately provide the affected revision, environment, impact, and a minimal reproduction using non-sensitive fixtures. Redact logs, model prompts, paths, and screenshots before sharing. No response-time or supported-version guarantee is currently published.
