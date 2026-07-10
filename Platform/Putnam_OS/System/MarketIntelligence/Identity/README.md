# Identity Translation Layer

Rule:

**CardUploader is the System of Record for card identity.**

This module never attempts to identify cards.

Its only responsibility is translating CardUploader's canonical identity into
the query format expected by each provider (eBay, TCGTracking, etc.).
