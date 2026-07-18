"""Pure comparable-sale evidence interpretation.

External data acquisition is injected. This module performs no HTTP, file,
credential, browser, UI, or database work.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable, Iterable, Mapping
from decimal import Decimal
from typing import Any


NAME_MATCH_SCORE_THRESHOLD = 90
PUTNAM_EXCLUDE_TERMS = (
    "world championship",
    "worlds",
    "world championship deck",
    " deck",
    "theme deck",
    "battle deck",
    "starter deck",
    "psa",
    "bgs",
    "cgc",
    "sgc",
    "ace",
    "tag",
    "slab",
    "graded",
    "lot",
    "bundle",
    "playset",
    "4x",
    "x4",
    "pack",
    "booster",
    "wrapper",
    "sealed",
    "proxy",
    "custom",
    "reprint",
    "metal",
    "gold foil",
    "jumbo",
    "oversized",
    "complete set",
    "binder",
    "master set",
)
GRADED_EXCLUDE_TERMS = frozenset({"psa", "bgs", "cgc", "tag", "sgc"})
NON_SINGLE_EXCLUDE_TERMS = frozenset(
    {"lot", "lots", "playset", "pack", "packs", "booster", "box", "deck", "sealed", "case"}
)
COMP_ANALYTICS_FIELDS = (
    "Card Name",
    "Set Name",
    "Card Number",
    "Search Query Used",
    "Total Candidates Returned",
    "Accepted Candidates",
    "Rejected Candidates",
    "Rejected: card name mismatch",
    "Rejected: card number mismatch",
    "Rejected: excluded graded term",
    "Rejected: excluded lot/pack/playset/booster/deck/sealed term",
    "Rejected: other reason",
)
REJECTION_DIAGNOSTIC_FIELDS = (
    "card_name_expected",
    "candidate_title",
    "normalized_card_name",
    "normalized_candidate_title",
    "name_match_score",
    "matched_name_tokens",
    "missing_name_tokens",
    "card_number_expected",
    "card_number_found",
    "card_number_match",
    "set_expected",
    "set_match_score",
    "excluded_terms_found",
    "final_rejection_reason",
    "rejection_details",
)

CardFieldsParser = Callable[[Mapping[str, Any]], tuple[str, str, str, str, Decimal]]
QueryBuilder = Callable[[Mapping[str, Any]], str]
SalesFetcher = Callable[[str], Mapping[str, Any]]
MoneyParser = Callable[[Any], Decimal]


def normalize_match_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_tokens(value: Any) -> list[str]:
    return [token for token in normalize_match_text(value).split() if token]


def token_match_score(expected: Any, candidate: Any) -> tuple[int, list[str], list[str]]:
    expected_tokens = match_tokens(expected)
    candidate_tokens = set(match_tokens(candidate))
    if not expected_tokens:
        return 100, [], []
    matched = [token for token in expected_tokens if token in candidate_tokens]
    missing = [token for token in expected_tokens if token not in candidate_tokens]
    score = round((len(matched) / len(expected_tokens)) * 100)
    return score, matched, missing


def normalized_card_number(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def find_card_number(title: Any, number: Any) -> tuple[Any, bool]:
    expected = normalized_card_number(number)
    if not expected:
        return "", True
    normalized_title = normalized_card_number(title)
    candidates = {expected}
    if expected.startswith("0"):
        candidates.add(expected.lstrip("0"))
    for candidate in candidates:
        if candidate and candidate in normalized_title:
            return number, True
    found = re.findall(
        r"[a-z]{1,5}\s*-?\s*\d{1,5}|\d{1,5}\s*/\s*\d{1,5}",
        str(title or "").lower(),
    )
    return "; ".join(dict.fromkeys(item.strip() for item in found)), False


def excluded_terms_found(
    title: Any,
    terms: Iterable[str] = PUTNAM_EXCLUDE_TERMS,
) -> list[str]:
    normalized_title = f" {normalize_match_text(title)} "
    found = []
    for term in terms:
        normalized_term = normalize_match_text(term)
        if normalized_term and f" {normalized_term} " in normalized_title:
            found.append(normalized_term)
    return sorted(set(found))


def build_rejection_details(
    card_name: str,
    matched: list[str],
    missing: list[str],
    score: int,
    reason: str,
    card_number: str,
    found_number: str,
    set_name: str,
    set_score: int,
    excluded: list[str],
) -> str:
    details = []
    if card_name:
        details.append(
            f'Expected "{card_name}"; matched token(s): {", ".join(matched) or "none"}; '
            f'missing token(s): {", ".join(missing) or "none"}; name score {score}'
        )
        if score < NAME_MATCH_SCORE_THRESHOLD:
            details[-1] += f" below threshold {NAME_MATCH_SCORE_THRESHOLD}."
        else:
            details[-1] += f" meets threshold {NAME_MATCH_SCORE_THRESHOLD}."
    if card_number:
        details.append(
            f'Expected card number "{card_number}"; found "{found_number or "none"}".'
        )
    if set_name:
        details.append(f'Set "{set_name}" title-token score: {set_score}.')
    if excluded:
        details.append(f"Excluded term(s) found: {', '.join(excluded)}.")
    if reason and reason != "accepted":
        details.append(f"Final rejection reason: {reason}.")
    return " ".join(details)


def comp_match_diagnostics(
    title: str,
    name: str,
    set_name: str,
    number: str,
) -> dict[str, Any]:
    normalized_name = normalize_match_text(name)
    normalized_title = normalize_match_text(title)
    name_score, matched, missing = token_match_score(name, title)
    set_score, _set_matched, _set_missing = token_match_score(set_name, title)
    found_number, number_match = find_card_number(title, number)
    excluded = excluded_terms_found(title)
    excluded_set = set(excluded)
    final_reason = "accepted"
    if excluded_set.intersection(GRADED_EXCLUDE_TERMS):
        final_reason = "excluded graded term"
    elif excluded_set.intersection(NON_SINGLE_EXCLUDE_TERMS):
        final_reason = "excluded lot/pack/playset/booster/deck/sealed term"
    elif any(term in excluded_set for term in ("graded", "slab", "ace")):
        final_reason = "excluded graded term"
    elif excluded:
        final_reason = f"excluded term: {excluded[0]}"
    elif name and name_score < NAME_MATCH_SCORE_THRESHOLD:
        final_reason = "card name mismatch"
    elif number and not number_match:
        final_reason = "card number mismatch"
    elif set_name:
        words = [
            word
            for word in re.split(r"\W+", str(set_name).lower())
            if len(word) > 3
        ]
        if words and not any(word in str(title or "").lower() for word in words):
            final_reason = "set not evident in title"
    details = build_rejection_details(
        name,
        matched,
        missing,
        name_score,
        final_reason,
        number,
        found_number,
        set_name,
        set_score,
        excluded,
    )
    return {
        "card_name_expected": name,
        "candidate_title": title,
        "normalized_card_name": normalized_name,
        "normalized_candidate_title": normalized_title,
        "name_match_score": name_score,
        "matched_name_tokens": "; ".join(matched),
        "missing_name_tokens": "; ".join(missing),
        "card_number_expected": number,
        "card_number_found": found_number,
        "card_number_match": "yes" if number_match else "no",
        "set_expected": set_name,
        "set_match_score": set_score,
        "excluded_terms_found": "; ".join(excluded),
        "final_rejection_reason": final_reason,
        "rejection_details": details,
    }


def comparable_reason(
    title: str,
    name: str,
    set_name: str,
    number: str,
) -> tuple[bool, str, dict[str, Any]]:
    diagnostics = comp_match_diagnostics(title, name, set_name, number)
    reason = diagnostics["final_rejection_reason"]
    return reason == "accepted", reason, diagnostics


def analytics_bucket(reason: str) -> str:
    if reason == "card name mismatch":
        return "Rejected: card name mismatch"
    if reason == "card number mismatch":
        return "Rejected: card number mismatch"
    if reason == "excluded graded term":
        return "Rejected: excluded graded term"
    if reason == "excluded lot/pack/playset/booster/deck/sealed term":
        return "Rejected: excluded lot/pack/playset/booster/deck/sealed term"
    return "Rejected: other reason"


def provider_comparable_reason(
    title: str,
    name: str,
    set_name: str,
    number: str,
) -> tuple[bool, str]:
    from Platform.Marketplace_Intelligence.marketplace_intelligence.providers import (
        comparable_reason as proven_provider_comparable_reason,
    )

    return proven_provider_comparable_reason(title, name, set_name, number)


def analyze_sales_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    parse_card_fields: CardFieldsParser,
    build_query: QueryBuilder,
    fetch_sales: SalesFetcher,
    parse_money: MoneyParser,
    floor: Decimal,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    reports: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    analytics: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        title, name, set_name, number, current = parse_card_fields(row)
        query = build_query(row)
        report = {
            "row": index,
            "title": title,
            "card_name": name,
            "set": set_name,
            "number": number,
            "current_price": current,
            "query": query,
            "status": "NO_DATA",
            "accepted_count": 0,
            "rejected_count": 0,
            "last_sale": "",
            "last3_avg": "",
            "median": "",
            "confidence": 0,
            "reason": "",
        }
        try:
            data = fetch_sales(query)
            results = data.get("results", [])
            accepted = []
            rejection_counts = {
                "Rejected: card name mismatch": 0,
                "Rejected: card number mismatch": 0,
                "Rejected: excluded graded term": 0,
                "Rejected: excluded lot/pack/playset/booster/deck/sealed term": 0,
                "Rejected: other reason": 0,
            }
            for candidate in results:
                ok, reason, diagnostics = comparable_reason(
                    candidate.get("title", ""),
                    name,
                    set_name,
                    number,
                )
                if ok:
                    accepted.append(candidate)
                else:
                    rejection_counts[analytics_bucket(reason)] += 1
                    rejected_row = dict(report)
                    rejected_row.update(
                        {
                            "candidate_title": candidate.get("title", ""),
                            "candidate_price": candidate.get("price", ""),
                            "reject_reason": reason,
                        }
                    )
                    rejected_row.update(diagnostics)
                    rejected.append(rejected_row)
            prices = [
                parse_money(candidate.get("price"))
                for candidate in accepted
                if parse_money(candidate.get("price")) > 0
            ]
            report["accepted_count"] = len(accepted)
            report["rejected_count"] = max(0, len(results) - len(accepted))
            analytics_row = {
                "Card Name": name,
                "Set Name": set_name,
                "Card Number": number,
                "Search Query Used": query,
                "Total Candidates Returned": len(results),
                "Accepted Candidates": len(accepted),
                "Rejected Candidates": report["rejected_count"],
            }
            analytics_row.update(rejection_counts)
            analytics.append(analytics_row)
            if prices:
                last_three = prices[:3]
                report["last_sale"] = prices[0]
                report["last3_avg"] = round(
                    sum(last_three) / len(last_three),
                    2,
                )
                report["median"] = round(
                    statistics.median(prices[: min(20, len(prices))]),
                    2,
                )
                count_score = min(40, len(prices) * 4)
                spread_score = 20
                if len(last_three) == 3:
                    average = report["last3_avg"]
                    spread = max(last_three) - min(last_three)
                    spread_score = max(
                        0,
                        25 - int((spread / max(average, Decimal("0.01"))) * 25),
                    )
                query_score = 20 if (name and number and set_name) else 10
                report["confidence"] = min(
                    100,
                    count_score + spread_score + query_score,
                )
                if (
                    current <= floor
                    and len(prices) >= 3
                    and report["last3_avg"] >= 2 * floor
                    and report["confidence"] >= 70
                ):
                    report["status"] = "MARKET_OPPORTUNITY_REVIEW"
                    report["reason"] = (
                        f"Last 3 avg ${report['last3_avg']:.2f} is >= 2x floor "
                        "after validation."
                    )
                else:
                    report["status"] = "NO_CHANGE"
                    report["reason"] = (
                        "Market data did not exceed opportunity threshold."
                    )
            else:
                report["reason"] = "No accepted comparables after validation."
        except Exception as exc:
            report["status"] = "ERROR"
            report["reason"] = str(exc)[:200]
            analytics.append(
                {
                    "Card Name": name,
                    "Set Name": set_name,
                    "Card Number": number,
                    "Search Query Used": query,
                    "Total Candidates Returned": 0,
                    "Accepted Candidates": 0,
                    "Rejected Candidates": 0,
                    "Rejected: card name mismatch": 0,
                    "Rejected: card number mismatch": 0,
                    "Rejected: excluded graded term": 0,
                    "Rejected: excluded lot/pack/playset/booster/deck/sealed term": 0,
                    "Rejected: other reason": 0,
                }
            )
        reports.append(report)
    return reports, rejected, analytics


def comp_search_analytics_summary_lines(
    analytics: Iterable[Mapping[str, Any]],
    *,
    engine_version: str,
    engine_subtitle: str,
    generated_at: str,
) -> list[str]:
    rows = list(analytics)
    total_candidates = sum(int(row.get("Total Candidates Returned") or 0) for row in rows)
    total_accepted = sum(int(row.get("Accepted Candidates") or 0) for row in rows)
    total_rejected = sum(int(row.get("Rejected Candidates") or 0) for row in rows)
    reason_totals = {
        field: sum(int(row.get(field) or 0) for row in rows)
        for field in COMP_ANALYTICS_FIELDS
        if field.startswith("Rejected:")
    }
    top_reasons = sorted(reason_totals.items(), key=lambda item: item[1], reverse=True)
    lines = [
        engine_version,
        engine_subtitle,
        f"Generated: {generated_at}",
        "",
        f"Searches: {len(rows)}",
        f"Total candidates reviewed: {total_candidates}",
        f"Total accepted: {total_accepted}",
        f"Total rejected: {total_rejected}",
        "",
        "Top rejection reasons:",
    ]
    for reason, count in top_reasons:
        if count:
            lines.append(f"- {reason}: {count}")
    if not any(count for _reason, count in top_reasons):
        lines.append("- None")
    return lines


__all__ = [
    "COMP_ANALYTICS_FIELDS",
    "GRADED_EXCLUDE_TERMS",
    "NAME_MATCH_SCORE_THRESHOLD",
    "NON_SINGLE_EXCLUDE_TERMS",
    "PUTNAM_EXCLUDE_TERMS",
    "REJECTION_DIAGNOSTIC_FIELDS",
    "analytics_bucket",
    "analyze_sales_rows",
    "build_rejection_details",
    "comp_match_diagnostics",
    "comp_search_analytics_summary_lines",
    "comparable_reason",
    "excluded_terms_found",
    "find_card_number",
    "match_tokens",
    "normalize_match_text",
    "normalized_card_number",
    "provider_comparable_reason",
    "token_match_score",
]
