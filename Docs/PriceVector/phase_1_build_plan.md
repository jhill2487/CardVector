# Price Vector Phase 1 Build Plan

Plan date: 2026-07-17

This is a build plan only. It does not authorize implementation.

## Phase 1 Definition

Build the smallest deterministic Price Vector contract inside the existing
canonical CardVector Pricing Engine.

Phase 1 starts with normalized listing records and fixture-supplied Fair Market
Value records. It applies the Putnam Collectibles business profile and
Competitive Turnover strategy, assigns approval/quality-review state, and
serializes an explainable recommendation.

Phase 1 does not:

- Query TCGplayer, eBay, Card Ladder, Alt, TCGtracking, or any live provider.
- Perform recognition or identity discovery.
- Implement Grade Vector or grading ROI.
- Add a new application, service package, or pricing module.
- Replace Putnam OS export behavior.
- Remove legacy pricing code.
- Change database schemas.
- Add a row-review UI.

## Canonical Implementation Boundary

Extend:

`Platform/Marketplace_Intelligence/marketplace_intelligence`

Reason:

- Project standards identify this as the reusable CardVector Pricing Engine.
- It already owns normalized listings, configurable calculations, decision
  labels, reports, CLI, UI, and provider isolation.
- Price Vector can be added as methods and fields in existing files without a
  competing module.

Market Intelligence remains responsible for evidence normalization and FMV.
Price Vector receives an FMV record and must not call `MarketProvider`.

Putnam OS remains an orchestrator. No production Putnam OS integration is
included in Phase 1.

## Exact Files To Modify

### 1. Domain records

`Platform/Marketplace_Intelligence/marketplace_intelligence/models.py`

Add compatible dataclasses or fields without removing existing constructor
behavior:

- `MarketEvidence`
- `FairMarketValue`
- `PricingContext`
- Price Vector fields on `PriceRecommendation`

Extend `Listing` with optional:

- `acquisition_cost`
- `acquisition_method`
- `acquisition_cost_confidence`
- `acquisition_lot_id`

Required recommendation fields:

- `fair_market_value`
- `original_recommended_price`
- `final_listing_price`
- `strategy`
- `confidence`
- `evidence`
- `reasoning`
- `approval_status`
- `manual_review_required`
- `quality_review_required`
- `override_reason`
- `override_user`
- `override_timestamp`

Existing fields remain available for backward compatibility.

### 2. Price Vector calculation

`Platform/Marketplace_Intelligence/marketplace_intelligence/pricing_engine.py`

Add:

```python
def recommend_from_fmv(
    self,
    listing: Listing,
    fmv: FairMarketValue,
    context: PricingContext,
) -> PriceRecommendation:
    ...
```

Responsibilities:

- Consume FMV only.
- Apply the configured Competitive Turnover rule.
- Preserve FMV separately from recommendation.
- Preserve Decimal arithmetic and existing minimum/rounding/change-limit
  helpers.
- Attach evidence, confidence, and deterministic reasoning.
- Never import or call provider code.

Keep `recommend(listing, market)` working during Phase 1. It may adapt legacy
`MarketPrice` into the new contract only through an explicit compatibility path.

Add an override helper on the existing recommendation record or engine:

```python
def apply_manual_override(
    recommendation: PriceRecommendation,
    final_price: Decimal,
    *,
    reason: str = "",
    user: str,
    timestamp: str,
) -> PriceRecommendation:
    ...
```

It must retain the original recommendation and must not mutate pricing
configuration or evidence.

### 3. Approval decision

`Platform/Marketplace_Intelligence/marketplace_intelligence/decision_engine.py`

Add a deterministic Price Vector decision path:

```python
def decide_price_vector(
    self,
    listing: Listing,
    fmv: FairMarketValue,
    pricing: PriceRecommendation,
) -> Decision:
    ...
```

Rules:

- Recommended price `< 5.00`: auto-approve unless confidence is `very_low`.
- Recommended price `5.00` through `20.00`: auto-approve only for `high`
  confidence.
- Recommended price `> 20.00`: manual review always.
- Recommended price `> 20.00`: `quality_review_required = True`.
- Internal quality review never changes `listing.condition`.

Use exact Decimal boundaries.

### 4. Import metadata

`Platform/Marketplace_Intelligence/marketplace_intelligence/csv_import.py`

Add optional acquisition column candidates and map them into `Listing`.
Absence of those columns must remain valid.

Do not change required eBay or CardUploader columns.

### 5. Reports

`Platform/Marketplace_Intelligence/marketplace_intelligence/reports.py`

Append Price Vector fields to analysis/recommendation output:

- Fair Market Value.
- Original recommendation.
- Final listing price.
- Strategy.
- Confidence.
- Evidence summary.
- Reasoning.
- Approval status.
- Manual-review flag.
- Internal quality-review flag.
- Acquisition metadata.
- Override reason/user/timestamp.

Do not remove existing report fields or change existing eBay bulk-revise
columns in Phase 1.

### 6. Orchestrator compatibility

`Platform/Marketplace_Intelligence/marketplace_intelligence/engine.py`

Add a fixture/stored-data entry point that accepts already-built FMV records,
for example:

```python
def analyze_fmv_records(
    self,
    listings: list[Listing],
    fair_market_values: dict[str, FairMarketValue],
) -> list[AnalysisResult]:
    ...
```

The method must not construct or call a provider.

Keep `analyze_import()` and `analyze_file()` behavior compatible.

### 7. Configuration

`Platform/Marketplace_Intelligence/config/business_profile.json`

Set the approved v1 business facts:

- Business name: Putnam Collectibles.
- Inventory ownership: 100% Putnam Collectibles.
- Active marketplaces: eBay and TCGplayer.
- Inactive marketplaces: Whatnot and direct website.
- Pricing strategy: Competitive Turnover.
- Acquisition cost optional.
- Supported acquisition method and confidence fields.

`Platform/Marketplace_Intelligence/config/pricing_profile.json`

Add configuration for:

- Competitive Turnover.
- Confidence vocabulary.
- `< $5`, `$5-$20`, and `> $20` approval rules.
- `$20` quality-review threshold.

Preserve existing minimum, shipping, rounding, and change-limit fields unless
an approved Price Vector rule explicitly supersedes one.

### 8. Existing smoke coverage

`Platform/Marketplace_Intelligence/tests/test_marketplace_intelligence_v1.py`

Add compatibility assertions proving the current import/provider/report path
still works after model extensions.

`Platform/Marketplace_Intelligence/README.md`

Document the boundary:

`Market Intelligence -> Fair Market Value -> Price Vector -> listing recommendation`

State explicitly that Price Vector does not query providers and that overrides
do not retrain rules.

## Exact Files To Create

`Platform/Marketplace_Intelligence/tests/test_price_vector_phase_1.py`

Focused standard-library `unittest` coverage for the new contract.

`Platform/Marketplace_Intelligence/tests/fixtures/price_vector_fmv_cases.json`

Stored raw-card FMV/evidence cases. Include:

- High-confidence value under `$5`.
- Very-low-confidence value under `$5`.
- High- and medium-confidence values between `$5` and `$20`.
- High-confidence value exactly `$20`.
- Value above `$20`.
- Missing acquisition cost.
- Acquisition method and confidence present.
- Supporting TCGplayer Market Price evidence.
- Active-listing competition evidence.
- A rejected PriceCharting raw-card evidence row to verify it cannot
  participate in raw FMV.

No other production module or folder is required.

## Model Contracts

Recommended minimal records:

```python
@dataclass(frozen=True)
class MarketEvidence:
    source: str
    evidence_type: str
    marketplace: str
    condition: str
    value: Decimal
    occurred_at: str = ""
    source_reference: str = ""
    accepted: bool = True
    reason: str = ""
    weight: Decimal = Decimal("0")


@dataclass(frozen=True)
class FairMarketValue:
    value: Decimal
    currency: str
    confidence: str
    methodology: str
    evidence: tuple[MarketEvidence, ...]
    calculated_at: str
    card_type: str = "raw"


@dataclass(frozen=True)
class PricingContext:
    marketplace: str
    business_profile: dict
    acquisition_cost: Decimal | None = None
    acquisition_method: str = ""
    acquisition_cost_confidence: str = ""
```

Confidence should use one normalized vocabulary in Phase 1:

- `high`
- `medium`
- `low`
- `very_low`

The compatibility adapter may translate existing integer or string confidence
values, but the Price Vector core must receive the normalized vocabulary.

## Competitive Turnover Rule Boundary

The approved repository prompt fixes the strategy name and approval policy but
does not define a complete formula for deriving recommendation from FMV.

Therefore Phase 1 should:

1. Express Competitive Turnover parameters in `pricing_profile.json`.
2. Use the existing configurable market strategy, minimum, shipping, change
   limits, and rounding helpers to derive the recommendation.
3. Record every applied parameter in reasoning.
4. Avoid inventing acquisition-profit floors or marketplace fees that have not
   been approved.
5. Keep FMV unchanged even when the listing recommendation is adjusted.

Any additional Competitive Turnover formula must be approved as a business
rule before implementation.

## Database Migrations

Required for Phase 1: **none**.

Reason:

- The repository has no canonical pricing database or repository.
- Phase 1 explicitly uses fixtures or existing stored data.
- Reports already provide the current durable recommendation artifact.
- Adding a new database in this phase would create architecture beyond the
  smallest implementation.

Phase 1 report rows must preserve override provenance. A later production
persistence phase may add versioned database migrations after the canonical
inventory/pricing database owner is approved. Existing Supabase capture and
location tables must not be repurposed.

## Unit Tests

`test_price_vector_phase_1.py` must cover:

1. FMV and recommendation remain separate.
2. Price Vector receives an FMV object and never calls a provider.
3. Under `$5`, high/medium/low confidence auto-approves.
4. Under `$5`, very-low confidence requires review.
5. Exactly `$5`, high confidence auto-approves.
6. `$5-$20`, medium/low/very-low confidence requires review.
7. Exactly `$20`, high confidence can auto-approve.
8. Above `$20`, every confidence requires manual review.
9. Above `$20`, internal quality review is set.
10. Internal quality review does not change marketplace condition.
11. Missing acquisition cost is accepted.
12. Acquisition method and cost confidence are preserved.
13. Evidence, confidence, and reasoning are always recorded.
14. Raw PriceCharting evidence cannot be accepted into FMV input.
15. Original recommendation survives a manual override.
16. Final listing price, optional reason, user, and timestamp are stored.
17. Applying an override does not mutate profile/rules.
18. Decimal boundaries and rounding are exact.

## Integration Tests

Extend the existing Marketplace Intelligence smoke test to verify:

1. Fixture listings can be paired with fixture FMV records.
2. `analyze_fmv_records()` returns `AnalysisResult` rows.
3. Analysis CSV contains the new fields.
4. Changed-only eBay export remains unchanged in column structure.
5. CardUploader/custom source modes still do not create eBay revise CSVs.
6. Legacy `analyze_file()` remains functional.
7. No live network access is required.

## Test Commands

From the repository root:

```powershell
py -m unittest Platform.Marketplace_Intelligence.tests.test_price_vector_phase_1
```

```powershell
py Platform\Marketplace_Intelligence\tests\test_marketplace_intelligence_v1.py
```

```powershell
py -m Platform.Putnam_OS.System.MarketIntelligence.Pricing.test_pricing_engine
```

```powershell
py -m py_compile ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\models.py ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\pricing_engine.py ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\decision_engine.py ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\csv_import.py ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\reports.py ^
  Platform\Marketplace_Intelligence\marketplace_intelligence\engine.py
```

```powershell
git diff --check
```

The Phase 1 test must fail if a live provider call is attempted.

## Acceptance Criteria

Phase 1 is complete when:

- Putnam Collectibles business facts are loaded from configuration.
- A normalized raw-card FMV fixture can be passed to Price Vector.
- Price Vector produces a separate, Decimal-safe listing recommendation.
- Competitive Turnover is recorded as the applied strategy.
- Every result includes evidence, normalized confidence, and reasoning.
- The approved three-tier approval matrix passes boundary tests.
- Recommendations above `$20` require both manual and internal quality review.
- Marketplace condition is unchanged by internal quality review.
- Acquisition cost remains optional.
- Acquisition method and cost confidence survive into the result when present.
- A manual override preserves original recommendation, final price, optional
  reason, user, and timestamp.
- Overrides do not change configuration or retrain any rule.
- Raw PriceCharting evidence is rejected by contract.
- Existing Marketplace Intelligence smoke behavior remains compatible.
- Existing eBay bulk-revise columns remain unchanged.
- No live external integration, recognition, or Grade Vector code is added.
- No database migration is applied.

## Deferred After Phase 1

- Live TCGplayer recent sales and Market Price.
- Live or supported eBay sold evidence.
- Card Ladder and Alt.
- Graded-card FMV.
- Production recommendation/override database.
- Row-level desktop approval UI.
- Putnam OS production integration.
- Marketplace fee/profit modeling not yet approved.
- Grade Vector and grading ROI.
