# Email Verifier & Deliverability Checker

Bulk email verification actor for Apify.

## Understanding your results (read this first)

Every email returns one of four statuses. Here is what each means and what to do:

| status | Meaning | What to do | Billed? |
|--------|---------|-----------|---------|
| **valid** | Mailbox exists and accepts mail (confirmed by SMTP). | Safe to send. | ✅ Yes |
| **invalid** | Address is bad — syntax error, no mail server, or the mailbox was rejected. | Do not send. Remove it. | ✅ Yes |
| **risky** | Real domain, but the mailbox can't be confirmed — it's a catch-all, disposable, or hosted on a provider that blocks verification (see below). | Your call. Often deliverable, but lower confidence. | ✅ Yes |
| **unknown** | We couldn't reach the mail server to get an answer (timeout/blocked). | Re-run later, or treat as unverified. | ❌ **Free** |

**You are only charged for `valid`, `invalid`, and `risky` (plus one `actor-start` per run). `unknown` is always free.**

### "My real Gmail / Outlook / company address came back `risky` — is that a bug?"

No. Large providers — **Gmail, Outlook/Microsoft 365, Yahoo, iCloud, Proton, Tutanota, Zoho, and any custom domain hosted on them** — deliberately refuse external mailbox checks. They answer "maybe" to every probe to stop spammers from harvesting valid addresses. **No verification service on earth can return a definitive `valid`/`invalid` for these** — anyone claiming otherwise is guessing. We return `risky` with reason `provider_unverifiable`, which is the honest answer: the domain is real and likely deliverable, we just can't confirm the individual mailbox. These addresses are generally safe to email.

### "Why did I get `unknown`? Did the tool fail?"

`unknown` means the destination mail server didn't give us a usable answer in time (it timed out, greylisted us, or blocked the connection). It is **not** a failure or an error, and it is **never charged**. Re-running later sometimes resolves it. It's most common for small self-hosted mail servers.

## Features

- Syntax validation via Python email module
- Disposable domain detection (embedded list, zero network)
- Role account flagging (info, sales, admin, etc.)
- MX record resolution, cached per domain
- Catch-all detection via SMTP probe
- SMTP RCPT TO handshake
- Honesty rule for Gmail, Outlook, Yahoo, iCloud, ProtonMail
- MX-host honesty rule: detects custom domains hosted on Google Workspace,
  Microsoft 365, Tutanota, Proton, Zoho, Proofpoint, Mimecast, NetEase, Yandex,
  Mail.ru, Tencent QQ, etc.
- Fail-fast SMTP: short connect timeout and single primary-MX probe so blocked
  or slow servers return `unknown` quickly instead of burning the full timeout
- Bounded concurrency (1-50)
- Per-email timeout
- Pay-per-event pricing

## Input

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| emails | array[string] | - | List of emails (1-100,000) |
| concurrency | int | 10 | Parallel emails (1-50) |
| perEmailTimeoutMs | int | 8000 | Hard timeout per email (ms) |
| verifyCatchAll | bool | true | Probe for catch-all domains |

## Output

| Field | Type | Description |
|-------|------|-------------|
| email | string | Verified email address |
| status | string | valid, invalid, risky, or unknown |
| reason | string | Machine-readable reason code |
| score | int | Deliverability score 0-100 |
| mxFound | bool | Domain has valid MX records |
| isDisposable | bool | Known disposable provider |
| isRoleAccount | bool | Role/function address |
| isFreeProvider | bool | Free consumer provider |
| isCatchAll | bool | Domain accepts all mail |

`score` is a 0–100 deliverability confidence: roughly 90+ confirmed valid, 45–85
deliverable-but-unconfirmed (`risky`), 0 invalid/undeliverable. Use it to rank or
threshold a list; the `status` field is the headline verdict.

### Reason codes

- bad_syntax - email fails RFC syntax
- disposable - domain is a known disposable provider
- no_mx - domain has no MX records
- mailbox_not_found - SMTP rejected (5xx)
- catch_all - domain accepts any address
- provider_unverifiable - major provider or MX hosted on one (Google Workspace,
  M365, Tutanota, Proton, etc.); mailbox can't be verified externally
- smtp_timeout - connection timed out or blocked
- smtp_blocked - connection refused or blocked

## Notes & limitations

- **SMTP from cloud IPs**: outbound port 25 is often blocked and many MX servers
  greylist or refuse unknown senders, so SMTP probes may return `unknown`
  (`smtp_timeout`). Unknown results are not charged. Domains hosted on major
  providers (Google Workspace, M365, Tutanota, Proton, Zoho, Proofpoint,
  Mimecast, NetEase, Yandex, Mail.ru, Tencent QQ) are short-circuited to
  `risky/provider_unverifiable` before the SMTP step, since those providers block
  external mailbox verification regardless of source IP — no provider, IP, or
  tool can confirm those mailboxes externally.
- **Fail-fast & cost**: blocked/slow SMTP aborts at a short connect timeout (~3s)
  and only the primary MX is probed, so `unknown` results resolve quickly. The
  MX-host list is intentionally conservative — when a provider can't be confirmed
  to block verification, the address is left to a real SMTP probe and may come
  back `unknown` (free) rather than being wrongly charged as `risky`.
- **mxFound semantics**: reflects whether an MX lookup ran and succeeded. Stages that
  short-circuit before the MX lookup (disposable) report `false` even though the domain
  may have MX. Major providers report `true` (known to have MX; not SMTP-probed).
- **Catch-all detection**: a single random-address RCPT probe. A server that accepts
  then later bounces will be reported as catch-all.

## Pricing

Pay-per-event (PPE) — you only pay for results, not for runtime:

- **actor-start** — charged once per run.
- **email-verified** — charged once per email that returns `valid`, `invalid`, or
  `risky` (any conclusive answer, including `provider_unverifiable` and `catch_all`).
- **`unknown` results are always free** — if we can't reach the server to get an
  answer, you pay nothing for that email.

So a run of 1,000 emails where 50 come back `unknown` bills `actor-start` + 950
`email-verified` events, not 1,000.

## Development

```
# Install dependencies
pip install -r requirements.txt

# Run locally
ACTOR_TEST_PAY_PER_EVENT=1 python3 -m src

# Build Docker image
docker build -t email-verifier .
```

## Architecture

src/
  __init__.py     Package marker
  __main__.py     Entry point + logging
  main.py         Actor orchestration
  models.py       Pydantic input/output models
  verifier.py     verify_email() chains all checks
  checks.py       Pure helpers

### Verification stages

1. Syntax check - RFC validation, no network
2. Disposable domain - in-memory set lookup
3. Role account - prefix match (flag only)
4. Major provider - honesty rule (risky)
5. MX DNS lookup - cached per domain
5b. MX-host honesty rule - if MX is a verification-blocking provider, stop (risky)
6. Catch-all probe - cached per domain
7. SMTP RCPT TO - definitive result
