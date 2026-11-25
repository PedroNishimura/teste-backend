from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_happy_path_normalizes_prices_and_applies_percentage_coupon():
    response = client.post("/cart/total", json={
        "items": [
            {"sku": "CAFE-500G", "unit_price": "R$ 34,90", "quantity": 3},
            {"sku": "MOEDOR-ELET", "unit_price": "R$ 1.299,00", "quantity": 1},
            {"sku": "FILTRO-103", "unit_price": "8,9", "quantity": 2},
        ], "coupon": "DEZ10",
    })
    assert response.status_code == 200
    assert response.json() == {"subtotal_cents": 1421.5, "discount_cents": 142.15, "total_cents": 1279.35}


def test_fixed_coupon():
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "200,00", "quantity": 1}], "coupon": "MENOS25"})
    assert response.status_code == 200
    assert response.json() == {"subtotal_cents": 200.0, "discount_cents": 25.0, "total_cents": 175.0}


def test_expired_coupon_returns_422():
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "10,00", "quantity": 1}], "coupon": "BLACK50"})
    assert response.status_code == 422


def test_below_minimum_returns_422():
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "99,99", "quantity": 1}], "coupon": "DEZ10"})
    assert response.status_code == 422


def test_price_normalization_supports_brazilian_and_dot_decimal_formats():
    response = client.post("/cart/total", json={"items": [
        {"sku": "A", "unit_price": "R$ 1.299,00", "quantity": 1},
        {"sku": "B", "unit_price": "8,9", "quantity": 1},
        {"sku": "C", "unit_price": "100.0", "quantity": 1},
    ]})
    assert response.status_code == 200
    assert response.json() == {"subtotal_cents": 1407.9, "discount_cents": 0.0, "total_cents": 1407.9}


def test_percentage_discount_rounds_down_to_cents():
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "15,55", "quantity": 1}], "coupon": "DEZ10"})
    assert response.status_code == 422  # minimum is checked before discount
    # A qualifying cart ending in 55 cents still rounds the percentage down.
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "100,55", "quantity": 1}], "coupon": "DEZ10"})
    assert response.status_code == 200
    assert response.json()["discount_cents"] == 10.05


def test_discount_never_makes_total_negative():
    response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "10,00", "quantity": 1}], "coupon": "DEZ10"})
    assert response.status_code == 422  # coupon minimum prevents this case
    # Coupon discounts are capped at subtotal; exercise the invariant directly with the fixed coupon.
    from main import COUPONS
    original = COUPONS["MENOS25"]["value"]
    COUPONS["MENOS25"]["value"] = 500.0
    try:
        response = client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "150,00", "quantity": 1}], "coupon": "MENOS25"})
        assert response.status_code == 200
        assert response.json()["total_cents"] >= 0
    finally:
        COUPONS["MENOS25"]["value"] = original


def test_empty_cart_invalid_data_and_unknown_coupon_statuses():
    assert client.post("/cart/total", json={"items": []}).status_code == 400
    assert client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "abc", "quantity": 1}]}).status_code == 400
    assert client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "1,00", "quantity": 0}]}).status_code == 400
    assert client.post("/cart/total", json={"items": [{"sku": "X", "unit_price": "10,00", "quantity": 1}], "coupon": "NOPE"}).status_code == 404
