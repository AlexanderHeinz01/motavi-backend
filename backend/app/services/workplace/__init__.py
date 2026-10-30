"""Arbeitsplatz-Steckbrief module (docs/STECKBRIEF_MODUL.md in the motavi repo).

Reads the per-frame pose data that the analysis pipeline records
(results/{job_id}/pose.npz) and evaluates cycles, reach, process steps,
scores and economics. Never changes result.json of the ergonomics pipeline.
"""
