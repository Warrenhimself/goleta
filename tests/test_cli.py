"""CLI 的关键操作与跨进程持久化测试。"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InventoryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_file = Path(self.temp_dir.name) / "inventory.json"

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "inventory_cli", "--data-file", str(self.data_file), *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_persistence_search_changes_and_total_value(self) -> None:
        self.assertEqual(self.run_cli("add", "P-1", "钢笔", "10", "2.50").returncode, 0)
        self.assertEqual(self.run_cli("add", "P-2", "纸张", "3", "1.20").returncode, 0)
        self.assertIn("钢笔", self.run_cli("find", "P-1").stdout)
        self.assertEqual(self.run_cli("increase", "P-1", "5").returncode, 0)
        self.assertEqual(self.run_cli("decrease", "P-1", "3").returncode, 0)
        self.assertIn("数量: 12", self.run_cli("list").stdout)
        self.assertIn("总库存价值：33.60", self.run_cli("value").stdout)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["products"][0]["quantity"], 12)

    def test_invalid_operations_do_not_change_stock(self) -> None:
        self.run_cli("add", "P-1", "钢笔", "2", "2.50")
        self.assertNotEqual(self.run_cli("add", "P-1", "重复", "1", "1.00").returncode, 0)
        self.assertNotEqual(self.run_cli("decrease", "P-1", "3").returncode, 0)
        self.assertNotEqual(self.run_cli("increase", "P-1", "0").returncode, 0)
        self.assertIn("数量: 2", self.run_cli("find", "P-1").stdout)
        self.assertNotEqual(self.run_cli("add", "P-2", "无效", "1", "1.234").returncode, 0)

    def test_corrupt_data_is_reported_without_overwrite(self) -> None:
        self.data_file.write_text("{broken", encoding="utf-8")
        result = self.run_cli("add", "P-1", "钢笔", "1", "2.50")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("数据文件格式错误", result.stderr)
        self.assertEqual(self.data_file.read_text(encoding="utf-8"), "{broken")

    def test_update_price_success_and_failures(self) -> None:
        self.assertEqual(self.run_cli("add", "P-1", "钢笔", "2", "2.50").returncode, 0)
        self.assertEqual(self.run_cli("add", "P-2", "纸张", "4", "1.20").returncode, 0)
        result = self.run_cli("update-price", "P-1", "3.75")
        self.assertEqual(result.returncode, 0)
        self.assertIn("单价: 3.75", self.run_cli("find", "P-1").stdout)
        self.assertIn("总库存价值：12.30", self.run_cli("value").stdout)
        before = self.data_file.read_bytes()

        for sku, price, message in (
            ("P-1", "-1", "单价必须是非负数"),
            ("P-1", "1.234", "最多保留两位小数"),
            ("P-1", "abc", "单价必须是数字"),
            ("missing", "4.00", "找不到 SKU"),
        ):
            with self.subTest(sku=sku, price=price):
                result = self.run_cli("update-price", sku, price)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertEqual(self.data_file.read_bytes(), before)

    def test_delete_success_and_missing_sku(self) -> None:
        self.run_cli("add", "P-1", "钢笔", "2", "2.50")
        self.run_cli("add", "P-2", "纸张", "4", "1.20")
        other_before = json.loads(self.data_file.read_text(encoding="utf-8"))["products"][1]

        result = self.run_cli("delete", "P-1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("已删除：P-1", result.stdout)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))["products"]
        self.assertEqual(saved, [other_before])
        self.assertIn("总库存价值：4.80", self.run_cli("value").stdout)
        before = self.data_file.read_bytes()

        result = self.run_cli("delete", "P-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("找不到 SKU", result.stderr)
        self.assertEqual(self.data_file.read_bytes(), before)

    def test_low_stock_matches_empty_invalid_and_read_only(self) -> None:
        self.run_cli("add", "B", "中库存", "3", "1.00")
        self.run_cli("add", "A", "零库存", "0", "2.00")
        self.run_cli("add", "C", "高库存", "10", "3.00")
        before = self.data_file.read_bytes()

        result = self.run_cli("low-stock", "3")
        self.assertEqual(result.returncode, 0)
        self.assertEqual([line.split(" | ")[0] for line in result.stdout.splitlines()], ["SKU: A", "SKU: B"])
        self.assertEqual(self.data_file.read_bytes(), before)

        result = self.run_cli("low-stock", "0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("SKU: A", result.stdout)
        self.assertNotIn("SKU: B", result.stdout)

        self.assertEqual(self.run_cli("decrease", "B", "1").returncode, 0)
        before = self.data_file.read_bytes()
        result = self.run_cli("low-stock", "0")
        self.assertEqual(result.returncode, 0)
        self.assertIn("SKU: A", result.stdout)
        result = self.run_cli("low-stock", "1")
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("SKU: B", result.stdout)

        for threshold in ("-1", "abc", "1.5"):
            with self.subTest(threshold=threshold):
                result = self.run_cli("low-stock", threshold)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("阈值必须是非负整数", result.stderr)
                self.assertEqual(self.data_file.read_bytes(), before)

    def test_low_stock_no_matches(self) -> None:
        self.run_cli("add", "P-1", "钢笔", "2", "2.50")
        before = self.data_file.read_bytes()
        result = self.run_cli("low-stock", "1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("没有符合条件的产品", result.stdout)
        self.assertEqual(self.data_file.read_bytes(), before)

    def test_existing_json_format_remains_compatible(self) -> None:
        self.data_file.write_text(
            json.dumps(
                {"products": [{"sku": "OLD-1", "name": "旧产品", "quantity": 2, "price": "4.50"}]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.assertIn("旧产品", self.run_cli("find", "OLD-1").stdout)
        self.assertIn("总库存价值：9.00", self.run_cli("value").stdout)
        self.assertEqual(self.run_cli("update-price", "OLD-1", "5.00").returncode, 0)
        saved = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(
            saved,
            {"products": [{"sku": "OLD-1", "name": "旧产品", "quantity": 2, "price": "5.00"}]},
        )


if __name__ == "__main__":
    unittest.main()
