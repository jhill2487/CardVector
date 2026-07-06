from __future__ import annotations


MODULE_NAME = "marketplace"


def evaluate(context, profile):
    marketplace = profile.get("default_marketplace", "ebay")
    return {
        "module_name": MODULE_NAME,
        "status": "active",
        "score": 1.0,
        "confidence": 0.9,
        "notes": [f"Default marketplace: {marketplace}"],
    }
