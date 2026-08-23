# Automated tests for the /products endpoint.
# Run from the project root:  python -m pytest

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_all_products():
    response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) == 6


def test_filter_by_category():
    response = client.get("/products?category=phone")
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_filter_budget_phones():
    response = client.get("/products?max_price=1000000&category=phone")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Samsung Galaxy M14" not in names  # ₹12,499 is over budget
    assert len(names) == 3


def test_invalid_max_price_returns_422():
    response = client.get("/products?max_price=abc")
    assert response.status_code == 422
