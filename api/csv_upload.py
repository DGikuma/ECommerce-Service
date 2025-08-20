import csv
from io import TextIOWrapper
from decimal import Decimal, InvalidOperation
from typing import List, Dict

from django.db import transaction
from .models import Product
from .utils_hierarchy import get_or_create_category_by_path


def parse_category_path(raw: str) -> list:
    """Accept 'A>B>C' or 'A/B/C' or 'A|B|C' -> [A, B, C]."""
    if not raw:
        return []
    for sep in [">", "/", "|"]:
        if sep in raw:
            return [seg.strip() for seg in raw.split(sep) if seg.strip()]
    return [raw.strip()]


@transaction.atomic
def import_products_csv(file_obj) -> Dict[str, list]:
    """Import products from a CSV file-like.

    Required columns: name, price, category_path
    Optional columns: description, stock_quantity

    Returns dict with created_ids and errors (row-indexed).
    """
    created_ids: List[int] = []
    errors: List[Dict] = []

    reader = csv.DictReader(TextIOWrapper(file_obj, encoding="utf-8"))
    required = {"name", "price", "category_path"}
    missing = required - set([h.strip() for h in reader.fieldnames or []])
    if missing:
        return {"created_ids": [], "errors": [{"index": -1, "errors": f"Missing columns: {', '.join(sorted(missing))}"}]}

    for idx, row in enumerate(reader, start=2):  # 1-based header, so first data row is 2
        try:
            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError("name is required")
            price_raw = (row.get("price") or "").strip()
            try:
                price = Decimal(price_raw)
            except (InvalidOperation, TypeError):
                raise ValueError("price must be a decimal number")
            category_path = parse_category_path(row.get("category_path") or "")
            if not category_path:
                raise ValueError("category_path is required")
            description = (row.get("description") or "").strip()
            stock_quantity = row.get("stock_quantity")
            stock_quantity = int(stock_quantity) if stock_quantity not in (None, "") else 0

            category = get_or_create_category_by_path(category_path)
            product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                category=category,
                stock_quantity=stock_quantity,
            )
            created_ids.append(product.id)
        except Exception as e:
            errors.append({"index": idx, "errors": str(e)})
    return {"created_ids": created_ids, "errors": errors}