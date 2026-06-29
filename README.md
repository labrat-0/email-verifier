# Email Verifier & Deliverability Checker

Bulk email verification actor for Apify.
## Features

- Syntax validation via Python email module
- Disposable domain detection (embedded list, zero network)
- Role account flagging (info, sales, admin, etc.)
- MX record resolution, cached per domain
- Catch-all detection via SMTP probe
- SMTP RCPT TO handshake
- Honesty rule for Gmail, Outlook, Yahoo, iCloud, ProtonMail
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

### Reason codes

- bad_syntax - email fails RFC syntax
- disposable - domain is a known disposable provider
- no_mx - domain has no MX records
- mailbox_not_found - SMTP rejected (5xx)
- catch_all - domain accepts any address
- provider_unverifiable - major provider, SMTP lies
- smtp_timeout - connection timed out or blocked
- smtp_blocked - connection refused or blocked

## Pricing

Pay-per-event (PPE):

- actor-start: charged once per run
- email-verified: charged per email with definitive result
- Unknown results are free

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
6. Catch-all probe - cached per domain
7. SMTP RCPT TO - definitive result
