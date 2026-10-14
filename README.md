# 本地库存管理 CLI

一个使用 Python 标准库编写的小型库存管理工具。产品包含 SKU、名称、数量和单价；数据保存在本地 JSON 文件中。

## 安装

需要 Python 3.10 或更新版本。进入项目目录即可运行，无需安装依赖：

```bash
cd /path/to/goleta_final
python3 -m inventory_cli --help
```

## 使用

```bash
# 添加产品：SKU、名称、初始数量、单价
python3 -m inventory_cli add PEN-001 "蓝色圆珠笔" 10 2.50

# 查看全部产品、按 SKU 查询
python3 -m inventory_cli list
python3 -m inventory_cli find PEN-001

# 增加或减少库存（数量必须为正整数）
python3 -m inventory_cli increase PEN-001 5
python3 -m inventory_cli decrease PEN-001 3

# 修改单价、删除产品
python3 -m inventory_cli update-price PEN-001 3.20
python3 -m inventory_cli delete PEN-001

# 列出数量小于或等于阈值的产品（按 SKU 排序）
python3 -m inventory_cli low-stock 5

# 查看所有产品的总库存价值（数量 × 单价之和）
python3 -m inventory_cli value
```

例如，添加上述产品后立即运行 `value`，输出为 `总库存价值：25.00`。单价最多保留两位小数；添加产品时数量可以是 0。`update-price` 使用与添加时相同的单价规则。`low-stock` 的阈值必须是非负整数，没有匹配产品时会显示提示。重复 SKU、未知 SKU、无效价格或阈值、库存不足等错误会显示在终端，并返回非零退出码。

默认数据文件是项目根目录的 `inventory.json`。首次添加或修改库存时自动创建；之后每次运行都会从这个文件读取数据。可以在**子命令前**指定其他文件：

```bash
python3 -m inventory_cli --data-file ./my-inventory.json add BOOK-01 "笔记本" 4 12.00
python3 -m inventory_cli --data-file ./my-inventory.json list
```

请备份需要长期保存的 JSON 文件。程序不会覆盖格式错误的现有数据文件。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
