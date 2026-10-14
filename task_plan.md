# Task Plan: Python CLI 库存管理工具

## Goal
完成可运行的多文件 Python CLI，支持产品管理、库存增减、总价值和本地 JSON 持久化。

## Phases
- [x] 检查空项目与约定
- [x] 实现数据模型、存储和命令行
- [x] 编写 README 与必要测试
- [x] 运行端到端验证并检查结果

## Decisions Made
- 使用 Python 标准库，避免安装第三方依赖。
- 使用 Decimal 计算金额，并在 JSON 中以字符串保存单价。
- 默认数据文件放在项目根目录，可通过 `--data-file` 指定其他路径。

## Status
已完成；3 个测试通过，实际 CLI 操作输出符合预期。

## Extension: update-price / delete / low-stock
- [x] 检查现有 CLI、存储格式和测试
- [x] 在现有代码上添加三个命令
- [x] 扩展测试与 README
- [x] 运行完整测试套件

**当前状态：** 已完成；完整测试套件 8/8 通过，保持现有 JSON `products` 列表格式。
