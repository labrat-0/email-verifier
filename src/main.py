"""
Actor orchestration for email-verifier.
Handles input, validation, charging, processing, dataset push, and limit guarding.
"""

import asyncio
import logging
import os
import sys
from typing import Any

from apify import Actor

from .models import InputModel, OutputModel
from .verifier import verify_email, DomainCache, CHARGE_UNKNOWN

logger = logging.getLogger(__name__)


async def run_actor() -> None:
    """Main actor entry point — orchestrates the entire run."""

    async with Actor:
        actor_input = await Actor.get_input() or {}
        logger.info("Actor input received: %s", {k: v for k, v in actor_input.items() if k != "emails"})

        # ── Validate input with Pydantic ───────────────────────────────────
        try:
            validated = InputModel(**actor_input)
        except Exception as exc:
            logger.error("Input validation failed: %s", exc)
            await Actor.fail(status_message=f"Invalid input: {exc}")
            return

        emails = validated.emails
        concurrency = validated.concurrency
        per_email_timeout_ms = validated.perEmailTimeoutMs
        verify_catch_all = validated.verifyCatchAll

        # ── Deduplicate ────────────────────────────────────────────────────
        unique_emails: list[str] = []
        seen: set[str] = set()
        for e in emails:
            e_stripped = e.strip()
            if e_stripped and e_stripped.lower() not in seen:
                seen.add(e_stripped.lower())
                unique_emails.append(e_stripped)

        deduped_count = len(emails) - len(unique_emails)
        if deduped_count > 0:
            logger.info("Deduplicated %d email(s), %d unique remaining",
                        deduped_count, len(unique_emails))
        else:
            logger.info("No duplicates found, verifying %d email(s)", len(unique_emails))

        if not unique_emails:
            logger.warning("No unique emails to verify after dedup")
            Actor.log.info("No unique emails provided")
            await Actor.exit()
            return

        # ── Initialize domain cache (shared across all verifications) ───────
        domain_cache = DomainCache()

        # ── Helper to check charge limit ────────────────────────────────────
        def charge_limit_reached() -> bool:
            try:
                mgr = Actor.get_charging_manager()
                return mgr.is_event_charge_limit_reached("email-verified")
            except Exception:
                return False

        # ── Charge actor-start ──────────────────────────────────────────────
        start_charge = await Actor.charge(event_name="actor-start")
        if start_charge and start_charge.event_charge_limit_reached:
            logger.warning("Event charge limit reached after actor-start charge")
            Actor.log.info("Event charge limit reached")
            await Actor.exit()
            return

        # ── Process emails with bounded concurrency ─────────────────────────
        semaphore = asyncio.Semaphore(concurrency)
        results: list[OutputModel] = []
        chargeable_count = 0
        unknown_count = 0
        stop_processing = False

        async def process_one(email_addr: str) -> OutputModel | None:
            nonlocal chargeable_count, unknown_count, stop_processing

            if stop_processing:
                return None

            async with semaphore:
                try:
                    result = await verify_email(
                        email=email_addr,
                        caches=domain_cache,
                        per_email_timeout_ms=per_email_timeout_ms,
                        verify_catch_all=verify_catch_all,
                    )
                except Exception as exc:
                    logger.error("Unhandled error verifying %s: %s", email_addr, exc)
                    return None

            return result

        # Run verification for all unique emails
        tasks = [process_one(email) for email in unique_emails]
        completed = 0
        total = len(tasks)

        for coro in asyncio.as_completed(tasks):
            if stop_processing:
                break

            result = await coro
            if result is None:
                completed += 1
                continue

            results.append(result)
            completed += 1

            # ── Push data per email ────────────────────────────────────────
            push_result = await Actor.push_data(result.model_dump())

            # ── Charge for definitive results only ─────────────────────────
            if result.status in ("valid", "invalid", "risky"):
                chargeable_count += 1
                charge_result = await Actor.charge(event_name="email-verified")
            else:
                unknown_count += 1
                charge_result = None

            # ── Guard: check eventChargeLimitReached AFTER each charge+push ─
            exhausted = False
            if charge_result and charge_result.event_charge_limit_reached:
                exhausted = True
            if push_result and push_result.event_charge_limit_reached:
                exhausted = True
            if charge_limit_reached():
                exhausted = True

            if exhausted:
                logger.warning(
                    "Event charge limit reached after %d / %d emails. Stopping.",
                    completed, total,
                )
                stop_processing = True
                break

        # ── Final summary ───────────────────────────────────────────────────
        logger.info(
            "Verification complete. %d processed, %d charged, %d unknown (not charged).",
            len(results),
            chargeable_count,
            unknown_count,
        )

        # Handle remaining tasks if we stopped early
        if stop_processing and completed < total:
            remaining_count = total - completed
            logger.info(
                "%d email(s) skipped due to event charge limit.",
                remaining_count,
            )
            for t in tasks:
                t.cancel()

        Actor.log.info("Email verification completed successfully")
