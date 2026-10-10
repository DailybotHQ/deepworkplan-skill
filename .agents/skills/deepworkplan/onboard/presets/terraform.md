# Preset — Terraform / IaC (Terraform / OpenTofu)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `*.tf` files (HCL) — conventionally split into `main.tf`, `variables.tf`,
  `outputs.tf`, and `providers.tf`/`versions.tf` — plus a committed
  `.terraform.lock.hcl` (provider lock).
- Reusable code under `modules/`, each module exposing `variables.tf` and
  `outputs.tf`; root configs that call modules with `module "x" { source = ... }`.
- A `terraform { backend "..." }` block declaring **remote state** (S3 +
  DynamoDB lock, GCS, azurerm, Terraform Cloud / HCP, or a Tofu equivalent), and
  one or more `provider` blocks with version constraints.
- Variable inputs via `*.tfvars` / `*.auto.tfvars`; the `.terraform/` directory
  is local cache and is git-ignored. **Infer the real backend from the code.**
- **OpenTofu** variant: the same `.tf`/HCL files but driven by the `tofu` CLI
  (often a `.terraform-version`/`.tool-versions` or CI hints at which binary).

## What to look for in recon

- The **real** validation gate: `terraform fmt -check -recursive`,
  `terraform validate`, `tflint` (read `.tflint.hcl`), and `terraform plan`
  (read-only). Security/policy scanners may be present: `tfsec`, `checkov`,
  `terraform-compliance`. Substitute `tofu` for `terraform` if OpenTofu is used.
- **Never** treat `terraform apply` as a validation gate — it mutates real
  infrastructure. `plan` is the safe, read-only check.
- How **environments** are separated: workspaces (`terraform workspace`), or
  per-environment directories (`envs/dev`, `envs/staging`, `envs/prod`), or
  layered `*.tfvars`. Identify which pattern this repo uses.
- Backend/state location and locking, provider/version pinning, and where
  **secrets** live (never in state-readable plaintext — vars, a secrets manager,
  Vault, env). `terraform init` is required before validate/plan.

## Stack-specific skills/agents/commands to generate

- Skills: `module-add` (new reusable module with `variables.tf`/`outputs.tf`),
  `resource-add` (resource + variables + outputs wired in), `env-add` (new
  environment dir/workspace + tfvars), optionally `provider-pin` and a
  `plan-review` helper that summarizes a `plan` diff.
- Agents: baseline roles + a `iac-reviewer` / `state-safety` persona aware of
  state mutation, drift, blast radius, and least-privilege provider creds.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — module composition, root configs vs modules, the
  provider/backend topology, environment separation strategy.
- `SECURITY.md` — state secrecy (remote state can contain secrets), least-
  privilege provider credentials, secrets handling, policy scanning
  (`tfsec`/`checkov`), and who can `apply`.
- `OPERATIONS.md`/runbook — the init → fmt → validate → plan → (gated) apply
  flow, state locking, and rollback/import procedures.
- Per-module docs: one per reusable module (its inputs, outputs, side effects).

## Typical validation command (FIND the real one)

Often `terraform init -backend=false && terraform fmt -check -recursive &&
terraform validate && tflint`, with `terraform plan` as the change preview
(substitute `tofu` for OpenTofu). **Do not assume** the backend, environment
layout, or scanner set — read the `Makefile`/`.tflint.hcl`/CI and capture the
exact command.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; items marked *documented example* were **not** run here —
confirm the exit code and the selection count in the target repo before trusting
them in a gate.

### 1. Full commands
- Validation (there is no unit suite in the usual sense): `terraform fmt -check -recursive` from the repo root; per **root module** directory (cwd matters): `terraform init -backend=false` then `terraform validate`; `tflint --recursive` (or per dir); `terraform plan` read-only per environment (needs credentials/backend — often CI-only; **never** `apply` as a gate).
- Tests where present: `terraform test` (≥ 1.6, `*.tftest.hcl`), Terratest (`go test ./test/...`), policy/security scanners (`checkov -d .`, `tfsec .`, `trivy config .`). Substitute `tofu` for OpenTofu.

### 2. Scoped invocation
**Scoping is per directory / root module** (inherent — documented example, Terraform is not available in the contributor environment): `cd modules/orders && terraform init -backend=false && terraform validate`; `tflint --chdir=modules/orders` (≥ 0.47; older: `tflint modules/orders`); `terraform fmt -check modules/orders`; `terraform test -filter=tests/orders.tftest.hcl` (one test file; `-filter` may repeat); Terratest: `go test ./test -run TestOrdersModule`; `checkov -d modules/orders`. `terraform plan` in `envs/<env>/` scopes to that root's state. **Evidence:** `Success! The configuration is valid.`, tflint's issue count, `terraform test` pass/fail counts, Terratest's `ok`.

### 3. Scoped static checks
- `fmt`, `validate`, `tflint`, `checkov`/`tfsec` all accept a directory — that *is* the scoped form; there is no per-file validate (HCL files in a module are one configuration). `terraform validate` requires `init` (providers/modules) even with `-backend=false`.

### 4. Source-to-test mapping
`modules/<name>/` ↔ `modules/<name>/tests/*.tftest.hcl` (native tests) or `test/<name>_test.go` (Terratest); environments/roots under `envs/<env>/` or `live/<env>/` (Terragrunt) call modules by `source`. A module change maps to its own tests **and** to a `validate`/`plan` of every root that calls it.

### 5. Affected consumers
Find callers with `grep -rn 'source *= *"[^"]*modules/orders' --include='*.tf'` (or `terragrunt graph-dependencies`); `terraform graph` inside a root shows resource/module edges. **Blind spots:** provider version pins and `.terraform.lock.hcl`, backend/remote-state configuration, `*.tfvars`/`*.auto.tfvars`, workspaces, data sources reading live infrastructure, registry module versions, variable defaults, `terraform.tf` required_version. A shared module or provider-pin change ⇒ `validate` (and ideally `plan`) on **every** calling root.

### 6. Escalation and fallback
Shared/core: `modules/` used by several roots, provider/version constraints, backend config, shared `locals`/naming modules. Always full run (every root): `versions.tf`/`providers.tf`, `.terraform.lock.hcl`, backend blocks, `.tflint.hcl`, `.terraform-version`, CI workflow that runs plans. **Fallback:** `terraform fmt -check -recursive && for every root: terraform init -backend=false && terraform validate && tflint` (+ `plan` in CI).

### 7. Layers and posture
Static checks (`fmt`, `validate`, `tflint`, policy scanners) — the fast base; `terraform test` with `mock_provider` (≥ 1.7) / Terratest with mocks as the unit-like layer; `terraform test`/Terratest against real providers and `plan` against the real backend as the slow integration layer (credentials, CI); `apply` is never a test. Static-first; keep real-provider tests few and isolated.

### 8. Zero-selection behavior
`terraform validate` in a directory with **no** `.tf` files prints `Success!` and exits **0** — a silent empty run: confirm the directory has configuration (`ls *.tf`). `terraform test -filter=<missing file>` errors out (documented; confirm). `tflint --chdir` on an empty dir reports no issues (exit 0). Terratest follows `go test` semantics (`-run` miss → `no tests to run`, exit 0).
