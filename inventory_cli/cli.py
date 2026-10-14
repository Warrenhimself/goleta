"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .store import InventoryError, InventoryStore, Product, parse_price


DEFAULT_DATA_FILE = Path(__file__).resolve().parent.parent / "inventory.json"


def nonnegative_threshold(value: str) -> int:
    try:
        threshold = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("阈值必须是非负整数。") from exc
    if threshold < 0:
        raise argparse.ArgumentTypeError("阈值必须是非负整数。")
    return threshold


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m inventory_cli", description="本地库存管理工具")
    parser.add_argument(
        "--data-file", type=Path, default=DEFAULT_DATA_FILE, help="JSON 数据文件路径"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="添加产品")
    add.add_argument("sku", help="库存编号")
    add.add_argument("name", help="产品名称")
    add.add_argument("quantity", type=int, help="初始数量（可为 0）")
    add.add_argument("price", help="单价，最多两位小数")

    commands.add_parser("list", help="列出所有产品")
    find = commands.add_parser("find", help="按 SKU 搜索")
    find.add_argument("sku")

    for command, description in (("increase", "增加库存"), ("decrease", "减少库存")):
        change = commands.add_parser(command, help=description)
        change.add_argument("sku")
        change.add_argument("amount", type=int, help="正整数数量")

    update_price = commands.add_parser("update-price", help="按 SKU 修改单价")
    update_price.add_argument("sku")
    update_price.add_argument("price", help="新单价，最多两位小数")

    delete = commands.add_parser("delete", help="按 SKU 删除产品")
    delete.add_argument("sku")

    low_stock = commands.add_parser("low-stock", help="列出数量不高于阈值的产品")
    low_stock.add_argument("threshold", type=nonnegative_threshold, help="非负整数阈值")

    commands.add_parser("value", help="显示总库存价值")
    return parser


def format_product(product: Product) -> str:
    return (
        f"SKU: {product.sku} | 名称: {product.name} | 数量: {product.quantity} | "
        f"单价: {product.price:.2f} | 库存价值: {product.value:.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = InventoryStore(args.data_file)
        if args.command == "add":
            product = store.add(args.sku, args.name, args.quantity, parse_price(args.price))
            print(f"已添加：{format_product(product)}")
        elif args.command == "list":
            if not store.products:
                print("库存为空。")
            else:
                for sku in sorted(store.products):
                    print(format_product(store.products[sku]))
        elif args.command == "find":
            print(format_product(store.find(args.sku)))
        elif args.command in ("increase", "decrease"):
            product = store.change_quantity(
                args.sku, args.amount, increase=args.command == "increase"
            )
            print(f"库存已更新：{format_product(product)}")
        elif args.command == "update-price":
            product = store.update_price(args.sku, parse_price(args.price))
            print(f"单价已更新：{format_product(product)}")
        elif args.command == "delete":
            product = store.delete(args.sku)
            print(f"已删除：{product.sku}")
        elif args.command == "low-stock":
            products = store.low_stock(args.threshold)
            if not products:
                print("没有符合条件的产品。")
            else:
                for product in products:
                    print(format_product(product))
        elif args.command == "value":
            print(f"总库存价值：{store.total_value():.2f}")
    except (InventoryError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0
