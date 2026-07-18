from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from .models import AnalysisResult, PersistedPricingRecord


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "001_price_vector_pricing_decisions.sql"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def decimal_text(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def pricing_record_from_result(
    result: AnalysisResult,
    *,
    decision_id: str | None = None,
    created_at: str | None = None,
) -> PersistedPricingRecord:
    fmv = result.fair_market_value
    return PersistedPricingRecord(
        decision_id=decision_id or str(uuid4()),
        listing_reference=(
            result.listing.item_id
            or result.listing.sku
            or f"row:{result.listing.row_number}"
        ),
        fair_market_value=(
            fmv.value if fmv is not None else result.pricing.fair_market_value
        ),
        fair_market_value_confidence=(
            fmv.confidence
            if fmv is not None
            else result.pricing.fair_market_value_confidence
        ),
        recommended_listing_price=result.pricing.recommended_listing_price,
        final_listing_price=result.pricing.final_listing_price,
        pricing_reasoning=result.pricing.pricing_reason,
        market_evidence_reference=(
            fmv.evidence_reference
            if fmv is not None
            else result.pricing.market_evidence_reference
        ),
        created_at=created_at or (fmv.calculated_at if fmv is not None else "") or utc_now(),
    )


class PricingDecisionRepository:
    """SQLite persistence for explicit Price Vector decision values."""

    def __init__(
        self,
        database_path: Path,
        migration_path: Path = MIGRATION_PATH,
    ) -> None:
        self.database_path = Path(database_path)
        self.migration_path = Path(migration_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def migrate(self) -> None:
        migration = self.migration_path.read_text(encoding="utf-8")
        with closing(self.connect()) as connection:
            with connection:
                connection.executescript(migration)

    def save(self, record: PersistedPricingRecord) -> PersistedPricingRecord:
        self.migrate()
        with closing(self.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    insert into price_vector_pricing_decisions (
                      decision_id,
                      listing_reference,
                      fair_market_value,
                      fair_market_value_confidence,
                      recommended_listing_price,
                      final_listing_price,
                      pricing_reasoning,
                      market_evidence_reference,
                      created_at
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.decision_id,
                        record.listing_reference,
                        decimal_text(record.fair_market_value),
                        record.fair_market_value_confidence,
                        decimal_text(record.recommended_listing_price),
                        decimal_text(record.final_listing_price),
                        record.pricing_reasoning,
                        record.market_evidence_reference,
                        record.created_at or utc_now(),
                    ),
                )
        return record

    def get(self, decision_id: str) -> PersistedPricingRecord | None:
        self.migrate()
        with closing(self.connect()) as connection:
            row = connection.execute(
                """
                select
                  decision_id,
                  listing_reference,
                  fair_market_value,
                  fair_market_value_confidence,
                  recommended_listing_price,
                  final_listing_price,
                  pricing_reasoning,
                  market_evidence_reference,
                  created_at
                from price_vector_pricing_decisions
                where decision_id = ?
                """,
                (decision_id,),
            ).fetchone()
        if row is None:
            return None
        return PersistedPricingRecord(
            decision_id=row["decision_id"],
            listing_reference=row["listing_reference"],
            fair_market_value=(
                Decimal(row["fair_market_value"])
                if row["fair_market_value"] is not None
                else None
            ),
            fair_market_value_confidence=row["fair_market_value_confidence"],
            recommended_listing_price=Decimal(row["recommended_listing_price"]),
            final_listing_price=Decimal(row["final_listing_price"]),
            pricing_reasoning=row["pricing_reasoning"],
            market_evidence_reference=row["market_evidence_reference"],
            created_at=row["created_at"],
        )
