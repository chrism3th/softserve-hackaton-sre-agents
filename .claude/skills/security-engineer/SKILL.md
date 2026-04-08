---
name: security-engineer
description: Use when reviewing code for vulnerabilities, designing auth, handling secrets, threat-modeling a feature, or hardening a service. Focus on defensive security and safe defaults.
---

# Security Engineer Skill

Assume breach. Design so that when — not if — something goes wrong, the blast radius is small.

## Principles

1. **Least privilege.** Every user, service, and token has the minimum permissions it needs.
2. **Defense in depth.** No single control is sufficient. Stack them.
3. **Fail secure.** On error, deny access, not grant it.
4. **Secure by default.** The safe option should be the default option.
5. **Visible and auditable.** Security events are logged, alertable, and reviewable.
6. **Simple.** Complexity is the enemy of security.

## Threat Modeling (STRIDE, lightweight)

Before building a feature, ask:
- **S**poofing: can someone pretend to be another user or service?
- **T**ampering: can data be modified in transit or at rest?
- **R**epudiation: can a user deny having done something?
- **I**nformation disclosure: can secrets or PII leak?
- **D**enial of service: can an attacker exhaust our resources?
- **E**levation of privilege: can a low-priv user gain high-priv access?

One paragraph per letter per feature. You'll catch 80% of issues.

## OWASP Top 10 — the ones you actually hit

1. **Broken access control** — enforce auth checks on *every* endpoint, not just the UI. IDOR is the #1 real-world bug.
2. **Cryptographic failures** — use TLS everywhere; never roll your own crypto; prefer libsodium/cryptography over low-level primitives.
3. **Injection** — parameterized queries only. No string concatenation into SQL / shell / LDAP / HTML.
4. **Insecure design** — missing rate limits, missing MFA on admin, missing lockout.
5. **Security misconfiguration** — default creds, verbose errors in prod, open S3 buckets.
6. **Vulnerable components** — dependency scanning in CI (Snyk, Dependabot, Trivy).
7. **Auth failures** — weak password policy, session fixation, predictable tokens.
8. **Software and data integrity failures** — unsigned packages, CI/CD pipeline tampering.
9. **Logging and monitoring failures** — you can't respond to what you can't see.
10. **SSRF** — validate outbound URLs; block link-local and private ranges (169.254/16, 10/8, etc.).

## Authentication

- **Passwords**: `argon2id` (preferred) or `bcrypt`. Never MD5/SHA1/SHA256 alone.
- **Session tokens**: random (≥128 bits from CSPRNG), stored server-side or as signed JWT with short TTL.
- **JWTs**: verify signature *and* algorithm (reject `none`), validate `exp`, `iss`, `aud`. Use asymmetric keys (RS256/EdDSA) for multi-service setups.
- **MFA**: TOTP (RFC 6238) or WebAuthn. SMS is deprecated for anything that matters.
- **Password reset**: single-use, short-lived tokens sent to verified email.
- **Rate-limit** login by IP *and* by username.
- **Generic error messages**: "Invalid credentials", never "User not found".

## Authorization

- **RBAC** for simple cases, **ABAC** for complex (per-resource rules).
- Check permission **at the server**, even if the UI hides the button.
- Default deny. Whitelist specific allows.
- Tenant isolation: every DB query must include `tenant_id`. Enforce with Row-Level Security in Postgres if possible.

## Secrets Management

- **Never in git.** Use `gitleaks` in pre-commit and CI.
- **Never in logs.** Redact before logging.
- **Never in env vars on shared machines** — use a secret manager (Vault, AWS Secrets Manager, Doppler).
- **Rotate** on a schedule and on any suspected exposure.
- **Short-lived credentials** where possible (STS tokens, OIDC federation in CI).

## Input Validation

- Validate at the **edge**, as early as possible (request parsing).
- **Allowlist > denylist**: specify what's allowed, reject everything else.
- **Type + shape + value**: JSON schema or Pydantic models catch most issues.
- **Size limits** on every input (body, headers, URL, file upload).
- **Reject unknown fields** when deserializing — prevents mass-assignment.

## Output Encoding

- **HTML**: escape with the framework's templating (Jinja2 autoescape, React `{}`). Never concatenate strings.
- **SQL**: parameterized queries (`WHERE id = $1`), never f-strings.
- **Shell**: avoid entirely; if unavoidable, `subprocess.run([...], shell=False)` with list args.
- **JSON**: use the library, don't build by hand.

## Transport

- **TLS 1.2+** everywhere, including internal.
- **HSTS** header with a long max-age.
- **HTTPS redirect** for any HTTP request.
- **Secure cookies**: `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict`).
- **CSP**: default-src 'self'; no inline scripts unless nonce'd. Start strict, loosen only with evidence.

## CORS

- Do **not** use `Access-Control-Allow-Origin: *` for authenticated APIs.
- Whitelist specific origins.
- Never reflect the request's `Origin` without validation.

## Rate Limiting & Abuse

- Per-user, per-IP, per-endpoint limits.
- Stricter limits on auth endpoints (login, reset, signup).
- CAPTCHA or proof-of-work for public forms.
- Resource limits: max payload size, max query depth (GraphQL), max concurrent connections.

## Logging for Security

Log these, redact PII:
- All auth events (success, failure, logout, MFA, password reset)
- Privilege changes (role assignments)
- Access to sensitive resources
- Admin actions
- All errors with stack traces (server-side only, never to the client)

**Never log**: passwords, tokens, full credit cards, secrets, full auth headers.

Ship logs to a central store with retention ≥ 90 days.

## Dependencies

- Automated scanning (Dependabot, Snyk, Trivy) in CI, blocking on high/critical.
- Lock files committed.
- Prefer well-maintained libraries (check last commit, open issues, maintainers).
- Avoid `curl | bash` installs.
- Sign and verify artifacts in CI/CD.

## Container Security

- Non-root user inside the container.
- Minimal base image (`distroless`, `alpine`, `-slim`).
- Read-only root filesystem where possible.
- Drop Linux capabilities (`--cap-drop=ALL`, add only what's needed).
- Scan images (Trivy, Grype) in CI.
- No secrets in layers (use build secrets or runtime injection).

## LLM / AI-Specific

- **Prompt injection**: treat user input as untrusted; never give the LLM authority to execute destructive actions without human confirmation.
- **Output validation**: validate LLM outputs against schemas before acting on them.
- **PII in prompts**: redact before sending to external APIs.
- **Tool scoping**: tools the agent can call must be narrowly permissioned.
- **Rate limit** per user per model to prevent cost abuse.
- **Output leakage**: ensure one user's data can't appear in another user's context (careful with shared caches).

## Incident Response (minimum viable)

- **Contact list**: who to reach, 24/7.
- **Runbook**: detect → contain → eradicate → recover → post-mortem.
- **Comms plan**: who tells users, legal, leadership.
- **Post-mortem**: blameless, focus on systemic fixes.

## Anti-Patterns

- "We'll add auth later."
- Storing passwords reversible ("we need to email them").
- Trusting the client — any client-side check must be duplicated server-side.
- Big green "allow everything" security group.
- Verbose stack traces returned to the user.
- Debug mode in production.
- Writing your own crypto.
- Shared service accounts for multiple humans.
- Long-lived personal access tokens committed to repos.
- Ignoring dependency alerts as "low risk" without reading them.
