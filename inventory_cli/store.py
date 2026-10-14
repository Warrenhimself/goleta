"""库存规则和 JSON 持久化。"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


class InventoryError(Exception):
    """用户可理解的库存操作错误。"""


def parse_price(value: str) -> Decimal:
    try:
        price = Decimal(value)
    except InvalidOperation as exc:
        raise InventoryError("单价必须是数字。") from exc
    if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
        raise InventoryError("单价必须是非负数，最多保留两位小数。")
    try:
        return price.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise InventoryError("单价超出可计算范围。") from exc


@dataclass
class Product:
    sku: str
    name: str
    quantity: int
    price: Decimal

    @property
    def value(self) -> Decimal:
        return self.quantity * self.price

    def to_json(self) -> dict[str, str | int]:
        return {
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
            "price": str(self.price),
        }


class InventoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.products = self._load()

    def _load(self) -> dict[str, Product]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise InventoryError(f"数据文件格式错误：{self.path}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("products"), list):
            raise InventoryError("数据文件缺少 products 列表。")

        products: dict[str, Product] = {}
        for item in data["products"]:
            if not isinstance(item, dict):
                raise InventoryError("数据文件包含无效产品。")
            sku = item.get("sku")
            name = item.get("name")
            quantity = item.get("quantity")
            raw_price = item.get("price")
            if (
                not isinstance(sku, str)
                or not sku.strip()
                or not isinstance(name, str)
                or not name.strip()
                or type(quantity) is not int
                or quantity < 0
                or not isinstance(raw_price, str)
            ):
                raise InventoryError("数据文件包含无效产品。")
            try:
                price = parse_price(raw_price)
            except InventoryError as exc:
                raise InventoryError("数据文件包含无效单价。") from exc
            if sku in products:
                raise InventoryError(f"数据文件中 SKU 重复：{sku}")
            products[sku] = Product(sku, name, quantity, price)
        return products

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"products": [self.products[sku].to_json() for sku in sorted(self.products)]}
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(data, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def add(self, sku: str, name: str, quantity: int, price: Decimal) -> Product:
        sku = sku.strip()
        name = name.strip()
        if not sku or not name:
            raise InventoryError("SKU 和名称不能为空。")
        if sku in self.products:
            raise InventoryError(f"SKU 已存在：{sku}")
        if quantity < 0:
            raise InventoryError("数量不能为负数。")
        product = Product(sku, name, quantity, price)
        self.products[sku] = product
        self._save()
        return product

    def find(self, sku: str) -> Product:
        try:
            return self.products[sku.strip()]
        except KeyError as exc:
            raise InventoryError(f"找不到 SKU：{sku}") from exc

    def change_quantity(self, sku: str, amount: int, *, increase: bool) -> Product:
        if amount <= 0:
            raise InventoryError("变更数量必须是正整数。")
        product = self.find(sku)
        if not increase and amount > product.quantity:
            raise InventoryError(f"库存不足：当前只有 {product.quantity} 件。")
        product.quantity += amount if increase else -amount
        self._save()
        return product

    def update_price(self, sku: str, price: Decimal) -> Product:
        product = self.find(sku)
        product.price = price
        self._save()
        return product

    def delete(self, sku: str) -> Product:
        product = self.find(sku)
        del self.products[product.sku]
        self._save()
        return product

    def low_stock(self, threshold: int) -> list[Product]:
        if threshold < 0:
            raise InventoryError("阈值必须是非负整数。")
        return [
            self.products[sku]
            for sku in sorted(self.products)
            if self.products[sku].quantity <= threshold
        ]

    def total_value(self) -> Decimal:
        return sum((product.value for product in self.products.values()), Decimal("0.00"))
