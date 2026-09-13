"""Folder scan safeguards for the terminal client's local upload workflow."""
from tui.services.file_ingest import normalize_path, scan_folder


def test_scan_folder_collects_supported_files_and_skips_dev_directories(tmp_path) -> None:
    (tmp_path / "report.pdf").write_bytes(b"%PDF-")
    (tmp_path / "notes.tmp").write_text("skip")
    venv = tmp_path / "venv"; venv.mkdir(); (venv / "hidden.pdf").write_bytes(b"%PDF-")
    scan = scan_folder(str(tmp_path))
    assert [path.name for path in scan.files] == ["report.pdf"]
    assert scan.skipped_unsupported == 1 and scan.skipped_hidden >= 1


def test_normalize_path_strips_terminal_drop_quotes(tmp_path) -> None:
    assert normalize_path(f'"{tmp_path}"') == tmp_path


def test_scan_folder_recognizes_python_markdown_and_csv(tmp_path) -> None:
    for name in ("analysis.py", "procedure.md", "readings.csv", "skip.xyz"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    scan = scan_folder(str(tmp_path))
    assert {path.suffix for path in scan.files} == {".py", ".md", ".csv"}
    assert scan.types == {"py": 1, "md": 1, "csv": 1}
