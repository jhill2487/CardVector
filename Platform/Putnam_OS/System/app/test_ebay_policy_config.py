from putnam_os import ExportCancelled, prepare_listing_export_rows


def sample_rows():
    return [
        {
            "Title": "Test Card",
            "*StartPrice": "1.00",
            "*CustomLabel": "",
        }
    ]


def test_export_requires_all_business_policies() -> None:
    try:
        prepare_listing_export_rows(
            sample_rows(),
            "ETB-01-A",
            policies={
                "shipping_policy": "Configured Shipping",
                "payment_policy": "",
                "return_policy": "Configured Returns",
            },
        )
    except ExportCancelled as exc:
        assert "payment policy" in str(exc)
    else:
        raise AssertionError("Missing payment policy should stop export.")


def test_export_stamps_configured_business_policies() -> None:
    out_rows, _review_rows, _prices, _changes, _batch_cols, ship_col, pay_col, ret_col, _promo_col = prepare_listing_export_rows(
        sample_rows(),
        "ETB-01-A",
        policies={
            "shipping_policy": "Configured Shipping",
            "payment_policy": "Configured Payment",
            "return_policy": "Configured Returns",
        },
    )
    row = out_rows[0]
    assert ship_col == "*ShippingProfileName"
    assert pay_col == "*PaymentProfileName"
    assert ret_col == "*ReturnProfileName"
    assert row["*ShippingProfileName"] == "Configured Shipping"
    assert row["*PaymentProfileName"] == "Configured Payment"
    assert row["*ReturnProfileName"] == "Configured Returns"


if __name__ == "__main__":
    test_export_requires_all_business_policies()
    test_export_stamps_configured_business_policies()
    print("eBay policy config smoke test passed")
