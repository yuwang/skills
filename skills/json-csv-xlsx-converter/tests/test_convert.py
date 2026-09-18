import csv
import itertools
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "convert.py"
SKILL = SKILL_DIR / "SKILL.md"
FORMATS = ("json", "jsonl", "csv", "xlsx")


def run_converter(source: Path, target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", str(SCRIPT), str(source), str(target), *args],
        text=True,
        capture_output=True,
        check=False,
    )


class ConverterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.records = [
            {
                "id": 1,
                "name": "张三",
                "profile": {"city": "上海"},
                "tags": ["VIP", "新客户"],
                "note": "含,逗号\n和换行",
                "active": True,
                "score": None,
            },
            {
                "id": 2,
                "name": "李四",
                "profile": {"city": "深圳"},
                "tags": [],
                "note": '含"引号"',
                "active": False,
                "score": 98.5,
            },
        ]
        self.inputs = {
            "json": self.root / "input.json",
            "jsonl": self.root / "input.jsonl",
            "csv": self.root / "input.csv",
            "xlsx": self.root / "input.xlsx",
        }
        self.inputs["json"].write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.inputs["jsonl"].write_text(
            "".join(
                json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
                for record in self.records
            ),
            encoding="utf-8",
        )
        with self.inputs["csv"].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=(
                    "id",
                    "name",
                    "profile.city",
                    "tags",
                    "note",
                    "active",
                    "score",
                ),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "1",
                    "name": "张三",
                    "profile.city": "上海",
                    "tags": '["VIP","新客户"]',
                    "note": "含,逗号\n和换行",
                    "active": "true",
                    "score": "",
                }
            )
            writer.writerow(
                {
                    "id": "2",
                    "name": "李四",
                    "profile.city": "深圳",
                    "tags": "[]",
                    "note": '含"引号"',
                    "active": "false",
                    "score": "98.5",
                }
            )

        result = run_converter(self.inputs["json"], self.inputs["xlsx"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def load_records(self, path: Path, fmt: str) -> list[dict]:
        if fmt == "json":
            return json.loads(path.read_text(encoding="utf-8"))
        if fmt == "jsonl":
            return [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if fmt == "csv":
            with path.open(encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))

        exported = self.root / f"verify-{path.stem}.json"
        result = run_converter(path, exported)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(exported.read_text(encoding="utf-8"))

    def assert_semantics(self, rows: list[dict], fmt: str) -> None:
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "张三")
        self.assertEqual(rows[1]["name"], "李四")
        if fmt == "csv":
            self.assertEqual(rows[0]["profile.city"], "上海")
            self.assertEqual(json.loads(rows[0]["tags"]), ["VIP", "新客户"])
            self.assertEqual(rows[0]["note"], "含,逗号\n和换行")
        else:
            self.assertEqual(rows[0]["profile"]["city"], "上海")
            self.assertEqual(rows[0]["tags"], ["VIP", "新客户"])
            self.assertEqual(rows[0]["note"], "含,逗号\n和换行")

    def test_all_twelve_conversion_paths(self) -> None:
        for source_format, target_format in itertools.permutations(FORMATS, 2):
            with self.subTest(source=source_format, target=target_format):
                output = self.root / f"{source_format}-to-{target_format}.{target_format}"
                result = run_converter(self.inputs[source_format], output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_semantics(self.load_records(output, target_format), target_format)

    def test_nested_round_trip_through_csv(self) -> None:
        csv_output = self.root / "round-trip.csv"
        json_output = self.root / "round-trip.json"
        self.assertEqual(run_converter(self.inputs["json"], csv_output).returncode, 0)
        result = run_converter(csv_output, json_output)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(json_output.read_text(encoding="utf-8"))
        self.assertEqual(rows[0]["profile"], {"city": "上海"})
        self.assertEqual(rows[0]["tags"], ["VIP", "新客户"])
        self.assertIsNone(rows[0]["score"])
        self.assertEqual(rows[0]["id"], "1")

    def test_skill_documents_jsonl_count_and_spreadsheet_loss(self) -> None:
        skill_text = SKILL.read_text(encoding="utf-8")
        self.assertIn("不要使用 `wc -l`", skill_text)
        self.assertIn("表头不计入数据记录", skill_text)
        self.assertIn("字段缺失、空字符串和 `null`", skill_text)

    def test_xlsx_header_trailing_line_and_blank_cell_contract(self) -> None:
        source = self.root / "blank-contract.jsonl"
        source.write_text(
            "\n".join(
                (
                    '{"id":1}',
                    '{"id":2,"note":"","amount":{"$numberLong":"2"}}',
                    '{"id":3,"note":null}',
                )
            ),
            encoding="utf-8",
        )
        workbook = self.root / "blank-contract.xlsx"
        exported = self.root / "blank-contract-round-trip.jsonl"

        result = run_converter(source, workbook)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = run_converter(workbook, exported)
        self.assertEqual(result.returncode, 0, result.stderr)

        rows = self.load_records(exported, "jsonl")
        self.assertEqual(
            rows,
            [
                {"id": 1, "note": None, "amount": {"$numberLong": None}},
                {"id": 2, "note": None, "amount": {"$numberLong": "2"}},
                {"id": 3, "note": None, "amount": {"$numberLong": None}},
            ],
        )

    def test_xlsx_sheet_selection_and_name(self) -> None:
        workbook = self.root / "named-sheet.xlsx"
        result = run_converter(self.inputs["json"], workbook, "--sheet", "客户")
        self.assertEqual(result.returncode, 0, result.stderr)

        exported = self.root / "named-sheet.jsonl"
        result = run_converter(workbook, exported, "--sheet", "客户")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_semantics(self.load_records(exported, "jsonl"), "jsonl")

        missing = self.root / "missing.json"
        result = run_converter(workbook, missing, "--sheet", "不存在")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("客户", result.stderr)
        self.assertFalse(missing.exists())

    def test_rejects_existing_output_without_force(self) -> None:
        output = self.root / "existing.csv"
        output.write_text("do not replace", encoding="utf-8")
        result = run_converter(self.inputs["json"], output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), "do not replace")

        result = run_converter(self.inputs["json"], output, "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("name", output.read_text(encoding="utf-8"))

    def test_rejects_invalid_jsonl_without_leaving_output(self) -> None:
        source = self.root / "invalid.jsonl"
        source.write_text('{"id":1}\nnot-json\n', encoding="utf-8")
        output = self.root / "invalid.csv"
        result = run_converter(source, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("2", result.stderr)
        self.assertFalse(output.exists())

    def test_rejects_duplicate_csv_headers(self) -> None:
        source = self.root / "duplicate.csv"
        source.write_text("id,id\n1,2\n", encoding="utf-8")
        output = self.root / "duplicate.json"
        result = run_converter(source, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("id", result.stderr)
        self.assertFalse(output.exists())

    def test_rejects_dotted_path_conflict(self) -> None:
        source = self.root / "conflict.json"
        source.write_text('{"a":{"b":1},"a.b":2}', encoding="utf-8")
        output = self.root / "conflict.csv"
        result = run_converter(source, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("a.b", result.stderr)
        self.assertFalse(output.exists())

    def test_rejects_same_or_unsupported_formats(self) -> None:
        same = self.root / "same.json"
        result = run_converter(self.inputs["json"], same)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(same.exists())

        unsupported = self.root / "output.xml"
        result = run_converter(self.inputs["json"], unsupported)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("xml", result.stderr.lower())
        self.assertFalse(unsupported.exists())

    def test_escapes_formula_like_headers_and_cells(self) -> None:
        source = self.root / "formula.json"
        source.write_text(
            json.dumps([{"=danger": "=1+1", "safe": "@command"}]),
            encoding="utf-8",
        )
        output = self.root / "formula.csv"
        result = run_converter(source, output)
        self.assertEqual(result.returncode, 0, result.stderr)

        with output.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ["'=danger", "safe"])
        self.assertEqual(rows[1], ["'=1+1", "'@command"])

    def test_reports_invalid_xlsx_without_traceback(self) -> None:
        source = self.root / "broken.xlsx"
        source.write_text("not an xlsx archive", encoding="utf-8")
        output = self.root / "broken.json"
        result = run_converter(source, output)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("XLSX", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
