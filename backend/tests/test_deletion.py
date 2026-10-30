"""Raw video: stored under raw/, deleted right after the analysis, also on
failure (docs/LOESCHKONZEPT.md)."""
import json
from unittest.mock import patch

from backend.app.services import analyzer, gcs
from backend.app.services.workplace.pose_store import PoseRecorder
from backend.tests import golden_run


def test_raw_path():
    assert gcs.raw_video_path("abc") == "raw/abc/video.mp4"


def test_upload_writes_raw_prefix():
    with patch("backend.app.services.gcs._upload") as up:
        assert gcs.upload_video("abc", b"x") == "raw/abc/video.mp4"
        up.assert_called_once()


def test_raw_deleted_after_success_and_media_under_results():
    result, store = golden_run.run(analyzer, gcs, PoseRecorder(), full=True)
    assert "error" not in result
    assert golden_run.deleted == ["raw/golden/video.mp4"]
    assert "results/golden/video_anon.mp4" in store
    assert "results/golden/pose.npz" in store
    assert not any(k.startswith("uploads/") for k in store)


def test_raw_deleted_after_failure():
    result, store = golden_run.run(analyzer, gcs, full=True, fail_at=30)
    assert "error" in result
    assert golden_run.deleted == ["raw/golden/video.mp4"]


def test_failed_deletion_does_not_break_the_result():
    with patch.object(gcs, "delete_blob", side_effect=RuntimeError("gcs down")):
        analyzer._delete_raw("x")  # logged, not raised


def test_lifecycle_file_matches_the_concept():
    from pathlib import Path

    rules = json.loads((Path(__file__).parents[2] / "infra" / "gcs_lifecycle.json").read_text())["rule"]
    by_age = {(tuple(r["condition"].get("matchesPrefix", [])), tuple(r["condition"].get("matchesSuffix", []))): r["condition"]["age"] for r in rules}
    assert by_age[(("raw/",), ())] == 1
    assert by_age[(("results/",), (".mp4", ".jpg", ".npz"))] == 30
    assert by_age[(("results/",), (".json",))] == 365
    assert all(r["action"]["type"] == "Delete" for r in rules)
