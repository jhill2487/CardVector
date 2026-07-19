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
BUSINESS_COLUMNS = {
    "marketplace": "text not null default ''",
    "estimated_fees": "text",
    "estimated_shipping": "text",
    "estimated_packaging": "text",
    "acquisition_cost": "text",
    "other_costs": "text",
    "estimated_net_profit": "text",
    "profit_margin": "text",
    "minimum_viable_price": "text",
    "business_rule_adjustments": "text not null default ''",
    "business_recommendation": "text not null default ''",
    "business_profile_version": "text not null default ''",
}


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
    profitability = result.pricing.profitability
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
        marketplace=result.pricing.marketplace,
        estimated_fees=(
            profitability.estimated_fees if profitability is not None else None
        ),
        estimated_shipping=(
            profitability.estimated_shipping if profitability is not None else None
        ),
        estimated_packaging=(
            profitability.estimated_packaging if profitability is not None else None
        ),
        acquisition_cost=(
            profitability.acquisition_cost if profitability is not None else None
        ),
        other_costs=(
            profitability.other_costs if profitability is not None else None
        ),
        estimated_net_profit=(
            profitability.estimated_net_profit if profitability is not None else None
        ),
        profit_margin=(
            profitability.profit_margin if profitability is not None else None
        ),
        minimum_viable_price=(
            profitability.minimum_viable_price if profitability is not None else None
        ),
        business_rule_adjustments=";".join(
            result.pricing.business_rule_adjustments
        ),
        business_recommendation=result.pricing.business_recommendation,
        business_profile_version=result.pricing.business_profile_version,
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
                existing = {
                    row["name"]
                    for row in connection.execute(
                        "pragma table_info(price_vector_pricing_decisions)"
                    )
                }
                for name, declaration in BUSINESS_COLUMNS.items():
                    if name not in existing:
                        connection.execute(
                            f"alter table price_vector_pricing_decisions "
                            f"add column {name} {declaration}"
                        )

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
                      created_at,
                      marketplace,
                      estimated_fees,
                      estimated_shipping,
                      estimated_packaging,
                      acquisition_cost,
                      other_costs,
                      estimated_net_profit,
                      profit_margin,
                      minimum_viable_price,
                      business_rule_adjustments,
                      business_recommendation,
                      business_profile_version
                    )
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        record.marketplace,
                        decimal_text(record.estimated_fees),
                        decimal_text(record.estimated_shipping),
                        decimal_text(record.estimated_packaging),
                        decimal_text(record.acquisition_cost),
                        decimal_text(record.other_costs),
                        decimal_text(record.estimated_net_profit),
                        decimal_text(record.profit_margin),
                        decimal_text(record.minimum_viable_price),
                        record.business_rule_adjustments,
                        record.business_recommendation,
                        record.business_profile_version,
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
                  created_at,
                  marketplace,
                  estimated_fees,
                  estimated_shipping,
                  estimated_packaging,
                  acquisition_cost,
                  other_costs,
                  estimated_net_profit,
                  profit_margin,
                  minimum_viable_price,
                  business_rule_adjustments,
                  business_recommendation,
                  business_profile_version
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
            marketplace=row["marketplace"],
            estimated_fees=(
                Decimal(row["estimated_fees"])
                if row["estimated_fees"] is not None
                else None
            ),
            estimated_shipping=(
                Decimal(row["estimated_shipping"])
                if row["estimated_shipping"] is not None
                else None
            ),
            estimated_packaging=(
                Decimal(row["estimated_packaging"])
                if row["estimated_packaging"] is not None
                else None
            ),
            acquisition_cost=(
                Decimal(row["acquisition_cost"])
                if row["acquisition_cost"] is not None
                else None
            ),
            other_costs=(
                Decimal(row["other_costs"])
                if row["other_costs"] is not None
                else None
            ),
            estimated_net_profit=(
                Decimal(row["estimated_net_profit"])
                if row["estimated_net_profit"] is not None
                else None
            ),
            profit_margin=(
                Decimal(row["profit_margin"])
                if row["profit_margin"] is not None
                else None
            ),
            minimum_viable_price=(
                Decimal(row["minimum_viable_price"])
                if row["minimum_viable_price"] is not None
                else None
            ),
            business_rule_adjustments=row["business_rule_adjustments"],
            business_recommendation=row["business_recommendation"],
            business_profile_version=row["business_profile_version"],
        )
