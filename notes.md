# Implementation Notes

- 初始目录只有 `.git`，没有既有源码或 `AGENTS.md`。
- CLI 命令：`add`、`list`、`find`、`increase`、`decrease`、`value`。
- 校验 SKU 唯一、数量和单价范围；库存不能减为负数。
- JSON 写入使用临时文件加原子替换，避免写入中断造成半个文件。
- 验证：`python3 -m unittest discover -s tests -v` 通过 3 个测试。
- 实际命令链：添加 10 件、增加 5 件、减少 3 件、查询和汇总，最终数量 12、价值 30.00。
- 扩展后验证：完整测试套件 8/8 通过；覆盖新增命令成功/失败、只读筛选、旧 JSON 格式兼容及原有命令。
