"""UTF-8 must not depend on Windows ANSI/GBK locale."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_all_project_python_text_reads_state_utf8_explicitly():
    for folder in ("app", "tests", "scripts"):
        for script in (ROOT / folder).rglob("*.py"):
            code = script.read_text(encoding="utf-8")
            assert (".read_text(" + ")") not in code, f"Locale-dependent read: {script}"
