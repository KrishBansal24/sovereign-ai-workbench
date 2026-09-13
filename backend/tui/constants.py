"""Centralized constants for the TUI."""

NAV = [("home", "Home"), ("agent", "Agent"), ("data", "Data"), ("documents", "Documents"), ("knowledge", "Knowledge"), ("artifacts", "Artifacts"), ("vision", "OCR / Vision"), ("sandbox", "Sandbox"), ("jobs", "Jobs")]
NAV_GROUPS = [
    ("WORKSPACE", [("home", "Home"), ("agent", "Agent"), ("data", "Data")]),
    ("LIBRARY", [("documents", "Documents"), ("knowledge", "Knowledge"), ("artifacts", "Artifacts")]),
    ("TOOLS", [("vision", "OCR / Vision"), ("sandbox", "Sandbox"), ("jobs", "Jobs")])
]
ALL_NAV_KEYS = [key for _, items in NAV_GROUPS for key, _ in items] + ["models", "settings", "help"]

RELIABILITY = {
    "accepted": "Ready",
    "accepted_with_warnings": "Ready with Warnings",
    "user_confirmation_required": "Needs Confirmation",
    "review_required": "Needs Review",
    "reupload_required": "Needs Clearer Scan",
}

TYPE_LABELS = {
    "py": "Python",
    "md": "Markdown",
    "csv": "CSV",
    "xlsx": "Excel",
    "docx": "Word",
    "pdf": "PDF",
    "txt": "Text",
    "png": "Image",
    "jpg": "Image",
    "jpeg": "Image",
}
