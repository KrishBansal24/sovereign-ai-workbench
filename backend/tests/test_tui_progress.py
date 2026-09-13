"""Progress state reflects actual item outcomes without timer-derived counts."""
from pathlib import Path
from tui.state.progress import BatchItem, BatchProgress


def test_batch_progress_counts_and_retryable_failures() -> None:
    items = [BatchItem(Path(f"file-{number}.pdf")) for number in range(3)]
    progress = BatchProgress("Import", items)
    progress.set_current(items[0], "uploaded", "Uploaded")
    progress.set_current(items[1], "failed", "Upload failed", "File exceeds upload limit.")
    assert progress.total == 3 and progress.processed == 2
    assert len(progress.failed) == 1 and progress.counts["queued"] == 1
    rendered = progress.render()
    assert "Uploaded: 1" in rendered and "Failed: 1" in rendered and "file-1.pdf" in rendered


def test_retry_transition_replaces_only_failed_outcome() -> None:
    item = BatchItem(Path("retry.pdf"), "failed", "Temporary backend failure")
    progress = BatchProgress("Import", [item])
    progress.set_current(item, "uploading", "Retrying")
    progress.set_current(item, "uploaded", "Uploaded")
    assert progress.counts["uploaded"] == 1 and not progress.failed
