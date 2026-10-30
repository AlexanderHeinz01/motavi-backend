"""Read-only inventory of the analysis bucket: number, age and size of the
objects per area. Deletes nothing.

    gcloud auth application-default login
    python infra/gcs_inventory.py BUCKET_NAME

Areas follow docs/LOESCHKONZEPT.md: raw/ (raw videos), results/ media
(.mp4, .jpg, .npz), results/ JSON, and the old layout uploads/ (raw video
video.mp4 and anonymised video video_anon.mp4 before 30.10.2026).
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone

from google.cloud import storage

AGE_BINS = [(1, "< 1 Tag"), (30, "1 bis 30 Tage"), (365, "30 bis 365 Tage"), (10**9, "> 365 Tage")]


def area(name: str) -> str:
    if name.startswith("raw/"):
        return "raw/ (Rohvideo)"
    if name.startswith("uploads/"):
        if name.endswith("/video.mp4"):
            return "uploads/ Rohvideo (alt)"
        if name.endswith("/video_anon.mp4"):
            return "uploads/ anonymisiertes Video (alt)"
        return "uploads/ sonstiges"
    if name.startswith("results/"):
        if name.endswith(".json"):
            return "results/ JSON"
        if name.endswith((".mp4", ".jpg", ".npz")):
            return "results/ Medien und pose.npz"
        return "results/ sonstiges"
    return "sonstiges"


def mb(n: int) -> str:
    return f"{n / 1e6:,.1f} MB".replace(",", ".")


def main(bucket_name: str) -> None:
    now = datetime.now(timezone.utc)
    stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "bytes": 0, "oldest": None, "newest": None, "bins": defaultdict(int)})
    jobs: dict[str, set[str]] = defaultdict(set)
    for blob in storage.Client().list_blobs(bucket_name):
        a = area(blob.name)
        s = stats[a]
        s["n"] += 1
        s["bytes"] += blob.size or 0
        created = blob.time_created
        s["oldest"] = min(filter(None, [s["oldest"], created]))
        s["newest"] = max(filter(None, [s["newest"], created]))
        age_days = (now - created).total_seconds() / 86400
        for limit, label in AGE_BINS:
            if age_days < limit:
                s["bins"][label] += 1
                break
        parts = blob.name.split("/")
        if len(parts) > 2:
            jobs[a].add(parts[1])

    print(f"Bucket {bucket_name}, Stand {now:%d.%m.%Y %H:%M} UTC\n")
    for a in sorted(stats):
        s = stats[a]
        print(f"{a}")
        print(f"  Objekte {s['n']}, Jobs {len(jobs[a])}, Größe {mb(s['bytes'])}")
        print(f"  ältestes {s['oldest']:%d.%m.%Y}, neuestes {s['newest']:%d.%m.%Y}")
        print("  Alter: " + ", ".join(f"{label} {s['bins'][label]}" for _, label in AGE_BINS))
        print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
