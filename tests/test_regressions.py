"""Dependency-free checks: python -m unittest discover -s tests -v."""
import ast
import math
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]

class Regressions(unittest.TestCase):
    def test_python_sources_compile(self):
        for path in (ROOT / "backend").rglob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_collect_stores_zero_and_preserves_missing(self):
        tree = ast.parse((ROOT / "backend/app/climate_data.py").read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "collect")
        fn.decorator_list = []
        cur = Mock()
        cur.fetchone.side_effect = [{"source_id": 1}, {"region_id": 1}]
        conn = Mock()
        conn.cursor.return_value.__enter__ = Mock(return_value=cur)
        conn.cursor.return_value.__exit__ = Mock(return_value=False)
        records = [
            {"tm": "2024-01-01", "maxTa": "20", "minTa": "10", "avgTa": "15", "sumRn": "0"},
            {"tm": "2024-01-02", "maxTa": "34", "minTa": "26", "avgTa": "30", "sumRn": "NaN"},
            {"tm": "2024-01-03", "maxTa": "", "minTa": None},
        ]
        requests = Mock()
        requests.get.return_value.json.return_value = {"response": {"body": {"items": {"item": records}, "totalCount": 3}}}
        ns = dict(os=Mock(), datetime=datetime, math=math, Query=lambda x, **kw: x,
                  connect_db=lambda: conn, requests=requests, logger=Mock(), HTTPException=Exception,
                  STATIONS={"11": ("Seoul", "108")}, SOURCE_NAME="KMA", SOURCE_URL="https://data.kma.go.kr", KMA_URL="test")
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "collect", "exec"), ns)
        result = ns["collect"]("20240101", "20240103", "11")
        rows = [call.args[1] for call in cur.execute.call_args_list if "INSERT INTO climate_observations" in call.args[0]]
        self.assertEqual([r[5] for r in rows if r[3] == "heat_day"], [0.0, 1.0])
        self.assertEqual([r[5] for r in rows if r[3] == "tropical_day"], [0.0, 1.0])
        self.assertTrue(all(math.isfinite(r[5]) for r in rows))
        self.assertEqual(result["api_days_processed"], 3)
        conn.commit.assert_called_once()
        conn.close.assert_called_once()

if __name__ == "__main__":
    unittest.main()
