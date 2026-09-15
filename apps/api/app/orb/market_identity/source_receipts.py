"""Canonical BUILD-2 source-receipt helpers (ingestion/verification seam).

External rule ingestion must never self-activate: receipts are built from
offline artifacts, content-pinned by hash, and start UNVALIDATED. Promotion
to a registry lifecycle that drives resolution is a separate explicit step.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from .contracts import SourceReceiptV1, source_receipt


def receipt_for_bytes(
    *,
    source_id: str,
    source_type: str,
    provider: str,
    document_id: str,
    artifact_identity: str,
    content: bytes,
    parser_version: str,
    **kwargs: object,
) -> SourceReceiptV1:
    digest = hashlib.sha256(content).hexdigest()
    return source_receipt(
        source_id=source_id,
        source_type=source_type,
        provider=provider,
        document_id=document_id,
        artifact_identity=artifact_identity,
        content_hash=digest,
        parser_version=parser_version,
        **kwargs,  # type: ignore[arg-type]
    )


def verify_content(receipt: SourceReceiptV1, content: bytes) -> bool:
    """True only when bytes reproduce the pinned content hash."""
    return hashlib.sha256(content).hexdigest() == receipt.content_hash


def receipt_age_ok(receipt: SourceReceiptV1, knowledge_cutoff: datetime) -> bool:
    """A receipt is usable only when it was available by the cutoff."""
    if knowledge_cutoff.tzinfo is None or knowledge_cutoff.utcoffset() is None:
        raise ValueError("knowledge_cutoff must be timezone-aware")
    return receipt.available_at is not None and receipt.available_at <= knowledge_cutoff
