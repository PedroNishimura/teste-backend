from datetime import date
import math
import re
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="API de Carrinho com Cupons")

COUPONS = {
    "DEZ10": {"type": "percentual", "value": 10.0, "minimum_price": 100.0, "max_date": date(2030, 12, 31)},
    "MENOS25": {"type": "fixo", "value": 25.0, "minimum_price": 150.0, "max_date": date(2030, 12, 31)},
    "BLACK50": {"type": "percentual", "value": 50.0, "minimum_price": 0.0, "max_date": date(2025, 11, 30)},
}


def parse_price(raw: Any) -> float:
    """Normalize supported price strings to a float amount in reais."""
    if isinstance(raw, bool) or raw is None:
        raise ValueError("preço inválido")
    text = str(raw).strip().replace("R$", "").replace(" ", "")
    if not text:
        raise ValueError("preço inválido")
    if "," in text:
        if text.count(",") != 1 or not re.fullmatch(r"-?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})|-?\d+(?:,\d{1,2})", text):
            raise ValueError("formato de preço inválido")
        text = text.replace(".", "").replace(",", ".")
    elif not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", text):
        raise ValueError("formato de preço inválido")
    try:
        value = float(text)
    except ValueError:
        raise ValueError("formato de preço inválido") from None
    if not (value == value and abs(value) != float("inf")):
        raise ValueError("formato de preço inválido")
    return value


class CartItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku: str = Field(min_length=1)
    unit_price: str | int | float
    quantity: int


class CartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CartItem]
    coupon: str | None = None


@app.exception_handler(RequestValidationError)
async def validation_error_as_bad_request(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": "Formato de dados inválido."})


@app.post("/cart/total")
def calculate_total(payload: CartRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="A lista do carrinho não pode ser vazia.")
    subtotal = 0.0
    for item in payload.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="A quantidade deve ser maior que zero.")
        try:
            unit_price = parse_price(item.unit_price)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        if unit_price < 0:
            raise HTTPException(status_code=400, detail="O preço não pode ser negativo.")
        subtotal += unit_price * item.quantity

    discount = 0.0
    if payload.coupon:
        coupon = COUPONS.get(payload.coupon.upper())
        if coupon is None:
            raise HTTPException(status_code=404, detail="Cupom não encontrado.")
        if date.today() > coupon["max_date"]:
            raise HTTPException(status_code=422, detail="Cupom expirado.")
        if subtotal < coupon["minimum_price"]:
            raise HTTPException(status_code=422, detail="O subtotal está abaixo do mínimo para este cupom.")
        if coupon["type"] == "percentual":
            discount = math.floor((subtotal * coupon["value"] / 100) * 100) / 100
        else:
            discount = coupon["value"]
        discount = min(discount, subtotal)

    discount = round(discount, 2)
    total = round(subtotal - discount, 2)
    return {"subtotal_cents": round(subtotal, 2), "discount_cents": discount, "total_cents": total}
