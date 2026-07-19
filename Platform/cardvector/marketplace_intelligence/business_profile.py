"""Canonical Putnam Collectibles business-pricing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


def _decimal(value: Any, default: str = "0.00") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _money(value: Any, default: str = "0.00") -> Decimal:
    return _decimal(value, default).quantize(MONEY)


@dataclass(frozen=True)
class PackagingProfile:
    key: str
    components: dict[str, Decimal]

    @property
    def total_cost(self) -> Decimal:
        return sum(self.components.values(), Decimal("0.00")).quantize(MONEY)

    @classmethod
    def from_mapping(cls, key: str, data: Mapping[str, Any]) -> "PackagingProfile":
        components = {
            str(name): _money(value)
            for name, value in dict(data.get("components") or {}).items()
        }
        return cls(key=str(key), components=components)


@dataclass(frozen=True)
class ShippingProfile:
    key: str
    service: str
    weight_oz: int
    postage_cost: Decimal
    packaging_profile: str
    enabled: bool = True

    @classmethod
    def from_mapping(cls, key: str, data: Mapping[str, Any]) -> "ShippingProfile":
        return cls(
            key=str(key),
            service=str(data.get("service") or key),
            weight_oz=int(data.get("weight_oz") or 0),
            postage_cost=_money(data.get("postage_cost")),
            packaging_profile=str(data.get("packaging_profile") or ""),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass(frozen=True)
class FeeTier:
    rate: Decimal
    up_to: Decimal | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "FeeTier":
        raw_limit = data.get("up_to")
        return cls(
            rate=_decimal(data.get("rate"), "0.00").quantize(RATE),
            up_to=None if raw_limit in {None, ""} else _money(raw_limit),
        )


@dataclass(frozen=True)
class MarketplaceProfile:
    key: str
    active: bool
    account_type: str
    commission_tiers: tuple[FeeTier, ...]
    commission_cap_per_item: Decimal | None
    processing_rate: Decimal
    fixed_order_fee: Decimal
    fixed_order_fee_over_threshold: Decimal
    fixed_fee_threshold: Decimal
    fee_rounding: str
    default_shipping_profile: str
    packaging_profile: str
    seller_pays_shipping_below_threshold: bool
    free_shipping_threshold: Decimal
    pricing_overrides: dict[str, Any]

    @classmethod
    def from_mapping(cls, key: str, data: Mapping[str, Any]) -> "MarketplaceProfile":
        raw_cap = data.get("commission_cap_per_item")
        tiers = tuple(
            FeeTier.from_mapping(item)
            for item in list(data.get("commission_tiers") or [])
        )
        if not tiers:
            tiers = (FeeTier(rate=Decimal("0.0000")),)
        fixed_fee = _money(data.get("fixed_order_fee"))
        return cls(
            key=str(key).lower(),
            active=bool(data.get("active", False)),
            account_type=str(data.get("account_type") or ""),
            commission_tiers=tiers,
            commission_cap_per_item=(
                None if raw_cap in {None, ""} else _money(raw_cap)
            ),
            processing_rate=_decimal(
                data.get("processing_rate"),
                "0.00",
            ).quantize(RATE),
            fixed_order_fee=fixed_fee,
            fixed_order_fee_over_threshold=_money(
                data.get("fixed_order_fee_over_threshold"),
                str(fixed_fee),
            ),
            fixed_fee_threshold=_money(
                data.get("fixed_fee_threshold"),
                "999999.00",
            ),
            fee_rounding=str(data.get("fee_rounding") or "half_up").lower(),
            default_shipping_profile=str(
                data.get("default_shipping_profile") or ""
            ),
            packaging_profile=str(data.get("packaging_profile") or ""),
            seller_pays_shipping_below_threshold=bool(
                data.get("seller_pays_shipping_below_threshold", False)
            ),
            free_shipping_threshold=_money(
                data.get("free_shipping_threshold"),
                "0.00",
            ),
            pricing_overrides=dict(data.get("pricing_overrides") or {}),
        )

    def commission_rate_for(self, sale_price: Decimal) -> Decimal:
        for tier in self.commission_tiers:
            if tier.up_to is None or sale_price <= tier.up_to:
                return tier.rate
        return self.commission_tiers[-1].rate

    def commission_fee_for(self, sale_price: Decimal) -> Decimal:
        remaining = sale_price
        lower_bound = Decimal("0.00")
        total = Decimal("0.00")
        for tier in self.commission_tiers:
            if remaining <= 0:
                break
            if tier.up_to is None:
                amount = remaining
            else:
                amount = min(remaining, max(Decimal("0.00"), tier.up_to - lower_bound))
            total += amount * tier.rate
            remaining -= amount
            if tier.up_to is not None:
                lower_bound = tier.up_to
        return total

    def fixed_fee_for(self, sale_price: Decimal) -> Decimal:
        if sale_price > self.fixed_fee_threshold:
            return self.fixed_order_fee_over_threshold
        return self.fixed_order_fee


@dataclass(frozen=True)
class PricingPolicy:
    minimum_price: Decimal
    minimum_profit: Decimal
    minimum_profit_margin: Decimal
    other_costs: Decimal
    rounding_rule: str
    default_marketplace: str
    price_vector: dict[str, Any]

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
        legacy_pricing: Mapping[str, Any] | None = None,
    ) -> "PricingPolicy":
        legacy = dict(legacy_pricing or {})
        vector = dict(data.get("price_vector") or legacy)
        minimum_price = _money(
            data.get("minimum_price", vector.get("minimum_price")),
            "0.01",
        )
        rounding_rule = str(
            data.get("rounding_rule")
            or vector.get("rounding_rule")
            or "nearest_cent"
        )
        vector.setdefault("minimum_price", str(minimum_price))
        vector.setdefault("rounding_rule", rounding_rule)
        return cls(
            minimum_price=minimum_price,
            minimum_profit=_money(data.get("minimum_profit"), "0.00"),
            minimum_profit_margin=_decimal(
                data.get("minimum_profit_margin"),
                "0.00",
            ),
            other_costs=_money(data.get("other_costs"), "0.00"),
            rounding_rule=rounding_rule,
            default_marketplace=str(
                data.get("default_marketplace") or "ebay"
            ).lower(),
            price_vector=vector,
        )


@dataclass(frozen=True)
class BusinessProfile:
    """Single normalized source for business-aware pricing decisions."""

    schema_version: str
    profile_version: str
    business_name: str
    currency: str
    tax_configuration: dict[str, Any]
    seller_preferences: dict[str, Any]
    default_acquisition_cost: Decimal
    acquisition_cost_confidence: str
    acquisition_override_precedence: tuple[str, ...]
    packaging_profiles: dict[str, PackagingProfile]
    shipping_profiles: dict[str, ShippingProfile]
    marketplace_profiles: dict[str, MarketplaceProfile]
    pricing_policy: PricingPolicy
    business_rules_enabled: bool
    compatibility_source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any] | None,
        legacy_pricing: Mapping[str, Any] | None = None,
    ) -> "BusinessProfile":
        values = dict(data or {})
        nested = bool(
            values.get("schema_version")
            and values.get("pricing_policy")
            and values.get("marketplaces")
        )
        acquisition = dict(values.get("acquisition") or {})
        packaging = dict(values.get("packaging") or {})
        shipping = dict(values.get("shipping_profiles") or {})
        marketplaces = dict(values.get("marketplaces") or {})
        pricing = dict(values.get("pricing_policy") or {})

        packaging_profiles = {
            str(key): PackagingProfile.from_mapping(str(key), profile)
            for key, profile in dict(packaging.get("profiles") or {}).items()
        }
        shipping_profiles = {
            str(key): ShippingProfile.from_mapping(str(key), profile)
            for key, profile in shipping.items()
        }
        marketplace_profiles = {
            str(key).lower(): MarketplaceProfile.from_mapping(str(key), profile)
            for key, profile in marketplaces.items()
        }

        return cls(
            schema_version=str(values.get("schema_version") or "legacy"),
            profile_version=str(values.get("profile_version") or "legacy"),
            business_name=str(
                values.get("business_name") or "Putnam Collectibles"
            ),
            currency=str(values.get("currency") or "USD").upper(),
            tax_configuration=dict(values.get("tax_configuration") or {}),
            seller_preferences=dict(values.get("seller_preferences") or {}),
            default_acquisition_cost=_money(
                acquisition.get("default_cost_per_card"),
                "0.00" if not nested else "0.05",
            ),
            acquisition_cost_confidence=str(
                acquisition.get("default_cost_confidence") or "default"
            ),
            acquisition_override_precedence=tuple(
                str(item)
                for item in list(
                    acquisition.get("override_precedence")
                    or ["card", "batch", "supplier", "default"]
                )
            ),
            packaging_profiles=packaging_profiles,
            shipping_profiles=shipping_profiles,
            marketplace_profiles=marketplace_profiles,
            pricing_policy=PricingPolicy.from_mapping(pricing, legacy_pricing),
            business_rules_enabled=bool(
                values.get("business_rules_enabled", nested)
            ),
            compatibility_source=(
                "" if nested else "legacy_business_and_pricing_profiles"
            ),
            metadata=dict(values.get("metadata") or {}),
        )

    def marketplace(self, key: str | None) -> MarketplaceProfile | None:
        name = str(key or self.pricing_policy.default_marketplace).lower()
        return self.marketplace_profiles.get(name)

    def packaging_cost(self, key: str | None) -> Decimal:
        profile = self.packaging_profiles.get(str(key or ""))
        return profile.total_cost if profile else Decimal("0.00")

    def shipping(self, key: str | None) -> ShippingProfile | None:
        return self.shipping_profiles.get(str(key or ""))

    def price_vector_profile(self) -> dict[str, Any]:
        return dict(self.pricing_policy.price_vector)

    def to_dict(self) -> dict[str, Any]:
        def money(value: Decimal) -> str:
            return format(value, "f")

        return {
            "schema_version": self.schema_version,
            "profile_version": self.profile_version,
            "business_name": self.business_name,
            "currency": self.currency,
            "business_rules_enabled": self.business_rules_enabled,
            "tax_configuration": dict(self.tax_configuration),
            "seller_preferences": dict(self.seller_preferences),
            "acquisition": {
                "default_cost_per_card": money(self.default_acquisition_cost),
                "default_cost_confidence": self.acquisition_cost_confidence,
                "override_precedence": list(self.acquisition_override_precedence),
            },
            "packaging": {
                "profiles": {
                    key: {
                        "components": {
                            name: money(value)
                            for name, value in profile.components.items()
                        }
                    }
                    for key, profile in self.packaging_profiles.items()
                }
            },
            "shipping_profiles": {
                key: {
                    "service": profile.service,
                    "weight_oz": profile.weight_oz,
                    "postage_cost": money(profile.postage_cost),
                    "packaging_profile": profile.packaging_profile,
                    "enabled": profile.enabled,
                }
                for key, profile in self.shipping_profiles.items()
            },
            "marketplaces": {
                key: {
                    "active": profile.active,
                    "account_type": profile.account_type,
                    "commission_tiers": [
                        {
                            "rate": str(tier.rate),
                            "up_to": (
                                None if tier.up_to is None else money(tier.up_to)
                            ),
                        }
                        for tier in profile.commission_tiers
                    ],
                    "commission_cap_per_item": (
                        None
                        if profile.commission_cap_per_item is None
                        else money(profile.commission_cap_per_item)
                    ),
                    "processing_rate": str(profile.processing_rate),
                    "fixed_order_fee": money(profile.fixed_order_fee),
                    "fixed_order_fee_over_threshold": money(
                        profile.fixed_order_fee_over_threshold
                    ),
                    "fixed_fee_threshold": money(profile.fixed_fee_threshold),
                    "fee_rounding": profile.fee_rounding,
                    "default_shipping_profile": profile.default_shipping_profile,
                    "packaging_profile": profile.packaging_profile,
                    "seller_pays_shipping_below_threshold": (
                        profile.seller_pays_shipping_below_threshold
                    ),
                    "free_shipping_threshold": money(
                        profile.free_shipping_threshold
                    ),
                    "pricing_overrides": dict(profile.pricing_overrides),
                }
                for key, profile in self.marketplace_profiles.items()
            },
            "pricing_policy": {
                "minimum_price": money(self.pricing_policy.minimum_price),
                "minimum_profit": money(self.pricing_policy.minimum_profit),
                "minimum_profit_margin": str(
                    self.pricing_policy.minimum_profit_margin
                ),
                "other_costs": money(self.pricing_policy.other_costs),
                "rounding_rule": self.pricing_policy.rounding_rule,
                "default_marketplace": self.pricing_policy.default_marketplace,
                "price_vector": dict(self.pricing_policy.price_vector),
            },
            "metadata": dict(self.metadata),
        }


__all__ = [
    "BusinessProfile",
    "FeeTier",
    "MarketplaceProfile",
    "PackagingProfile",
    "PricingPolicy",
    "ShippingProfile",
]
