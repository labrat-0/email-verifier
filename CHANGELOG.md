# Changelog

All notable changes to the Email Verifier & Deliverability Checker actor.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions track the
Apify actor version.

## [0.2] — 2026-06-29

First hardened public release. Consolidates the correctness, cost, and clarity work
done over the 0.1.x build series into a single stable version.

### Added
- **MX-host honesty rule.** Custom domains whose MX points to a provider that blocks
  external mailbox verification (Google Workspace, Microsoft 365, Tutanota, Proton,
  Zoho, Proofpoint, Mimecast, NetEase, Yandex, Mail.ru, Tencent QQ) now return
  `risky/provider_unverifiable` deterministically via DNS, instead of a slow `unknown`.
- **Fail-fast SMTP.** Short (~3s) connect timeout and single primary-MX probe, so
  blocked or slow servers return `unknown` quickly instead of burning the full per-email
  timeout. Keeps the compute cost of unavoidable `unknown` results low.
- **Buyer-facing README.** "Understanding your results" status table, FAQ on why real
  Gmail/Outlook addresses are `risky`, explicit billing (which statuses charge), and a
  0–100 score guide.

### Fixed
- **Role-account false positives.** Prefix matching now requires a separator boundary, so
  real names are no longer flagged as role accounts (`priya` via `pr`, `newsom` via
  `news`, `president` via `pr`).
- **`outlook.com` / `mail.ru` mis-flagged as disposable.** Removed from the disposable
  set; they no longer short-circuit to `risky/disposable`.
- **Leading/trailing dot in local part** (`.user@`, `user.@`) now correctly returns
  `invalid/bad_syntax` instead of a charged `risky`.
- **`mxFound` correctness** for major providers (now `true`; they have MX).
- **Crash on the charge-limit early-stop path** (`task.cancel()` on raw coroutines).
- **Empty MAIL FROM (`<>`)** for SMTP probes per RFC 5321.

### Changed
- Charging unchanged and explicit: `valid` / `invalid` / `risky` are charged
  (`email-verified`), `unknown` is always free.
- Build tag pinned to `latest`; stale Version 0.0 removed so every run uses current code.
