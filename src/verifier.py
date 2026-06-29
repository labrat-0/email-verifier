"""
Core email verification logic.
Chains checks in order: syntax → disposable → role → major provider → MX → catch-all → SMTP.
Caches MX and catch-all results per domain.
"""

import asyncio
import logging
import time
from typing import Optional

from . import checks
from .models import OutputModel

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
CHARGE_UNKNOWN: bool = False

# Score constants
SCORE_BAD_SYNTAX = 0
SCORE_NO_MX = 0
SCORE_MAILBOX_NOT_FOUND = 0
SCORE_SMTP_TIMEOUT = 0
SCORE_SMTP_BLOCKED = 0
SCORE_DISPOSABLE = 15
SCORE_CATCH_ALL = 45
SCORE_PROVIDER_UNVERIFIABLE = 65
SCORE_ROLE_ACCOUNT_VALID = 85
SCORE_CLEAN_VALID = 95
SCORE_DEFAULT = 50  # fallback for truly unknown


class DomainCache:
    """
    Per-domain cached results for MX and catch-all.
    One instance shared across all verifications in a run.
    """

    def __init__(self):
        self.mx_cache: dict[str, Optional[list[str]]] = {}
        self.catch_all_cache: dict[str, bool] = {}


async def verify_email(
    email: str,
    caches: DomainCache,
    per_email_timeout_ms: int = 8000,
    verify_catch_all: bool = True,
) -> OutputModel:
    """
    Verify a single email address through all checks.
    Short-circuits on the first definitive failure.

    Returns:
        OutputModel with full result fields.
    """
    timeout_seconds = per_email_timeout_ms / 1000.0
    deadline = time.monotonic() + timeout_seconds

    # ── Stage 1: Syntax check ──────────────────────────────────────────────
    is_valid_syntax, normalized_email = checks.syntax_check(email)
    if not is_valid_syntax:
        return OutputModel(
            email=email,
            status="invalid",
            reason="bad_syntax",
            score=SCORE_BAD_SYNTAX,
            mxFound=False,
            isDisposable=False,
            isRoleAccount=False,
            isFreeProvider=False,
            isCatchAll=False,
        )

    # Extract local part and domain from normalized email
    local, domain = normalized_email.rsplit("@", 1)

    # ── Stage 2: Disposable domain check ───────────────────────────────────
    domain_lower = domain.lower()
    is_disposable = checks.is_disposable_domain(domain_lower)
    if is_disposable:
        return OutputModel(
            email=normalized_email,
            status="risky",
            reason="disposable",
            score=SCORE_DISPOSABLE,
            mxFound=False,
            isDisposable=True,
            isRoleAccount=checks.is_role_account(local),
            isFreeProvider=False,
            isCatchAll=False,
        )

    # ── Stage 3: Role account check (flag only) ────────────────────────────
    is_role = checks.is_role_account(local)

    # ── Stage 4: Major provider check (honesty rule) ───────────────────────
    is_major = checks.is_major_provider(domain_lower)
    if is_major:
        return OutputModel(
            email=normalized_email,
            status="risky",
            reason="provider_unverifiable",
            score=SCORE_PROVIDER_UNVERIFIABLE,
            mxFound=False,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=True,
            isCatchAll=False,
        )

    is_free = checks.is_free_provider(domain_lower)

    # ── Stage 5: MX DNS lookup (cached per domain) ─────────────────────────
    remaining = max(0.1, deadline - time.monotonic())
    mx_hosts = caches.mx_cache.get(domain_lower)
    if mx_hosts is None and domain_lower not in caches.mx_cache:
        try:
            mx_hosts = await asyncio.wait_for(
                asyncio.to_thread(checks.resolve_mx, domain_lower),
                timeout=min(remaining, 5.0),
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.debug("MX resolve timeout/fail for %s: %s", domain_lower, exc)
            mx_hosts = None
        caches.mx_cache[domain_lower] = mx_hosts

    if not mx_hosts:
        # No MX records found
        return OutputModel(
            email=normalized_email,
            status="invalid",
            reason="no_mx",
            score=SCORE_NO_MX,
            mxFound=False,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=is_free,
            isCatchAll=False,
        )

    mx_found = True

    # ── Stage 6: Catch-all probe (cached per domain) ───────────────────────
    is_catch_all = False
    if verify_catch_all:
        if domain_lower in caches.catch_all_cache:
            is_catch_all = caches.catch_all_cache[domain_lower]
        else:
            remaining = max(0.1, deadline - time.monotonic())
            try:
                # Probe the first MX host
                probe_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        checks.probe_catch_all,
                        mx_hosts[0],
                        domain_lower,
                        min(remaining, 5.0),
                    ),
                    timeout=min(remaining, 5.5),
                )
                is_catch_all = probe_result
            except (asyncio.TimeoutError, Exception) as exc:
                logger.debug("Catch-all probe fail for %s: %s", domain_lower, exc)
                is_catch_all = False
            caches.catch_all_cache[domain_lower] = is_catch_all

    if is_catch_all:
        return OutputModel(
            email=normalized_email,
            status="risky",
            reason="catch_all",
            score=SCORE_CATCH_ALL,
            mxFound=True,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=is_free,
            isCatchAll=True,
        )

    # ── Stage 7: SMTP RCPT TO verification ─────────────────────────────────
    remaining = max(1.0, deadline - time.monotonic())
    smtp_result = None  # True=valid, False=invalid, None=unknown

    for mx_host in mx_hosts[:3]:  # Try up to 3 MX hosts
        remaining_host = remaining / len(mx_hosts[:3])
        try:
            host_result = await asyncio.wait_for(
                asyncio.to_thread(
                    checks.smtp_verify_sync,
                    normalized_email,
                    mx_host,
                    min(remaining_host, timeout_seconds * 0.8),
                ),
                timeout=min(remaining_host, timeout_seconds * 0.85),
            )
            if host_result is not None:
                smtp_result = host_result
                break
        except (asyncio.TimeoutError, Exception) as exc:
            logger.debug("SMTP timeout/error for %s on %s: %s",
                         normalized_email, mx_host, exc)
            continue

    # ── Determine final result ─────────────────────────────────────────────
    if smtp_result is True:
        # SMTP accepted → valid
        final_score = SCORE_ROLE_ACCOUNT_VALID if is_role else SCORE_CLEAN_VALID
        return OutputModel(
            email=normalized_email,
            status="valid",
            reason="",
            score=final_score,
            mxFound=True,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=is_free,
            isCatchAll=False,
        )
    elif smtp_result is False:
        # SMTP rejected → invalid
        return OutputModel(
            email=normalized_email,
            status="invalid",
            reason="mailbox_not_found",
            score=SCORE_MAILBOX_NOT_FOUND,
            mxFound=True,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=is_free,
            isCatchAll=False,
        )
    else:
        # SMTP temp fail / timeout → unknown
        return OutputModel(
            email=normalized_email,
            status="unknown",
            reason="smtp_timeout",
            score=SCORE_SMTP_TIMEOUT,
            mxFound=True,
            isDisposable=False,
            isRoleAccount=is_role,
            isFreeProvider=is_free,
            isCatchAll=False,
        )
