---
name: json-csv-xlsx-converter
description: Use when 用户需要在 JSON、JSONL、CSV、XLSX 文件之间转换表格数据，或提到 JSON Lines、Excel 导入导出、嵌套 JSON 扁平化、CSV 与 Excel 互转。
---

# JSON、JSONL、CSV、XLSX 格式转换

## 概览

运行本 Skill 自带的 `scripts/convert.py` 完成确定性转换。不要临时拼装 `jq`、csvkit、pandas 或 DuckDB 命令。脚本将输入读入统一的行记录模型，再写成目标格式，因此覆盖四种格式之间的 12 条转换路径。

## 工作流

1. 确认输入文件存在，并根据扩展名确定输入、输出格式。
2. XLSX 默认读取活动工作表；用户指定工作表时传入 `--sheet`。
3. 将本 `SKILL.md` 所在目录设为命令工作目录，运行：

   ```bash
   uv run scripts/convert.py input.json output.xlsx
   ```

4. 输出已存在时，仅在用户允许覆盖后添加 `--force`。
5. 重要数据再反向转换到临时文件：用 JSON 解析器统计非空对象记录，不要使用 `wc -l`；比较扁平列名和关键字段。不要要求 CSV/XLSX 回转后的完整 JSON 对象相等。

## 快速参考

| 任务 | 命令 |
| --- | --- |
| JSON 转 CSV | `uv run scripts/convert.py data.json data.csv` |
| JSONL 转 XLSX | `uv run scripts/convert.py data.jsonl data.xlsx` |
| CSV 转 JSONL | `uv run scripts/convert.py data.csv data.jsonl` |
| XLSX 指定工作表转 JSON | `uv run scripts/convert.py book.xlsx data.json --sheet Sheet1` |
| 创建指定名称的工作表 | `uv run scripts/convert.py data.csv book.xlsx --sheet Data` |
| 覆盖已有输出 | 在命令末尾添加 `--force` |
| 查看参数 | `uv run scripts/convert.py --help` |

`uv` 根据脚本内的依赖声明安装隔离的 `openpyxl`，无需修改用户项目依赖。

## 数据规则

- JSON 顶层接受单个对象或对象数组；JSONL 每个非空行必须是对象。
- JSON 嵌套对象按点号展开：`{"profile":{"city":"上海"}}` 变为列 `profile.city`。
- 数组和作为字段值的复杂对象在 CSV/XLSX 单元格中保存为紧凑 JSON，转回 JSON/JSONL 时自动解析。
- 字段名不得为空或包含点号；`a` 与 `a.b` 同时出现属于路径冲突。
- 列顺序按字段首次出现的顺序取并集；缺失字段写为空值。
- CSV/XLSX 第一行是表头，读取时只用于字段名，表头不计入数据记录。
- CSV/XLSX 空单元格转回 JSON/JSONL 时为 `null`。字段缺失、空字符串和 `null` 写入表格后可能无法区分；列并集产生的缺失嵌套路径可能还原为包含 `null` 叶子的对象。
- JSONL 记录数按成功解析的非空对象行统计，与文件末尾是否有换行无关；不要使用 `wc -l` 验证记录数。
- CSV 没有类型信息。CSV 转 JSON/JSONL 时，普通非空单元格保持字符串；只自动解析数组和对象。
- XLSX 读取缓存值，不保留公式、样式、图表或宏。此 Skill 用于数据转换，不用于完整工作簿迁移。
- 写入 CSV/XLSX 时，以 `= + - @` 开头的表头和文本会添加单引号，防止电子表格公式注入。
- XLSX 输出只创建一个工作表；工作表名称最长 31 个字符，且不能包含 `[]:*?/\\`。
- 所有输出使用临时文件原子写入；转换失败不留下半成品。

## 完整示例

将嵌套 JSON 转为指定工作表的 XLSX，再反向验证为 JSONL：

```bash
uv run scripts/convert.py customers.json customers.xlsx --sheet Customers
uv run scripts/convert.py customers.xlsx /tmp/customers-check.jsonl --sheet Customers
```

用 JSON 解析器确认两份数据的非空对象记录数一致，再比较扁平列名、关键字段和数组内容。表格回转不要求字段缺失、空字符串和 `null` 保持区别。

## 常见错误

| 错误 | 处理 |
| --- | --- |
| `输出文件已存在` | 获得覆盖许可后使用 `--force`，否则换输出路径 |
| `工作表不存在` | 从错误信息列出的工作表中选择，再传 `--sheet` |
| `表头重复` 或 `字段路径冲突` | 修正重复列、包含点号的 JSON 键或 `a`/`a.b` 冲突 |
| `JSONL 第 N 行解析失败` | 单独检查该行是否为完整 JSON 对象 |
| `wc -l` 比预期少 1 | 文件末行可能没有换行；用 JSON 解析器统计非空对象记录 |
| `不支持扩展名` | 只使用 `.json`、`.jsonl`、`.csv`、`.xlsx` |
| 无法下载 `openpyxl` | 检查 PyPI 网络访问；依赖缓存后可离线重复运行 |
