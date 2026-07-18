# Database Schema — Tariq.lb

Owner: Zahraa · Last updated: Week 4

This document covers the full SQLite schema: both tables, every field,
data types, keys, and constraints. If a change is needed after Week 1,
open a PR with a short migration note (see Section 7 of the project
plan) rather than editing the tables directly.

---

## `reports`

One row per user-submitted road-damage report.

| Field            | Type      | Constraints                          | Notes |
|------------------|-----------|---------------------------------------|-------|
| `id`             | Integer   | Primary key, autoincrement            | |
| `image_path`     | String(255) | Not null                            | Relative path under `static/uploads/`, UUID-based filename |
| `lat`            | Float     | Not null                              | Latitude, either from EXIF GPS or manual pin |
| `lng`            | Float     | Not null                              | Longitude, either from EXIF GPS or manual pin |
| `location_source`| String(10)| Not null, default `"manual"`          | One of: `"gps"`, `"manual"` |
| `status`         | String(20)| Not null, default `"pending"`         | One of: `"pending"`, `"reviewed"`, `"resolved"` |
| `created_at`     | DateTime  | Not null, default `utcnow()`          | Set at insert time |

**Relationships:** `reports.id` → `detections.report_id` (one-to-many,
though in practice each report has at most one detection in this
project's scope). Cascade: deleting a `Report` deletes its `Detection`
rows automatically (`cascade="all, delete-orphan"`).

---

## `detections`

One row per AI detection result, linked to the report it was run on.

| Field                  | Type      | Constraints                              | Notes |
|------------------------|-----------|--------------------------------------------|-------|
| `id`                   | Integer   | Primary key, autoincrement                 | |
| `report_id`            | Integer   | Foreign key → `reports.id`, not null       | |
| `damage_type`          | String(50)| Not null                                    | One of: `Pothole`, `Road Crack`, `Surface Wear`, `Other` (or `"None"` if no damage found) |
| `confidence`           | Float     | Not null                                    | YOLOv8 confidence score, 0.0–1.0 |
| `severity_score`       | Integer   | Not null                                    | 0–100 |
| `severity_label`       | String(20)| Not null                                    | One of: `Low`, `Medium`, `High`, `Critical` |
| `annotated_image_path` | String(255)| Nullable                                   | Path to the YOLOv8 output image with bounding boxes drawn |

---

## Relationship Diagram (text-based)

```
reports (1) ──────< (many) detections
  id                       report_id (FK)
```

In this project's scope each report produces exactly one detection
record, but the relationship is modeled as one-to-many for flexibility
(e.g. re-running detection in the future).

---

## Example rows

**reports**

| id | image_path                     | lat     | lng     | location_source | status   | created_at          |
|----|----------------------------------|---------|---------|------------------|----------|----------------------|
| 1  | static/uploads/seed_1.jpg        | 33.8938 | 35.5018 | gps              | pending  | 2026-06-12T10:03:00 |
| 2  | static/uploads/seed_2.jpg        | 33.8959 | 35.4784 | manual           | reviewed | 2026-06-15T14:21:00 |

**detections**

| id | report_id | damage_type | confidence | severity_score | severity_label | annotated_image_path                          |
|----|-----------|-------------|------------|-----------------|------------------|--------------------------------------------------|
| 1  | 1         | Pothole     | 0.87       | 70              | High             | static/uploads/annotated/seed_1_annotated.jpg   |
| 2  | 2         | Road Crack  | 0.62       | 45              | Medium           | static/uploads/annotated/seed_2_annotated.jpg   |

---

## Shared constants reference

Field value sets (`DAMAGE_TYPES`, `SEVERITY_LEVELS`, `REPORT_STATUSES`,
`LOCATION_SOURCES`) are defined once in `config.py` — import from
there rather than hardcoding strings, so a future change only happens
in one place.

## Possible future migration (flagged, not yet implemented)

Malek's Week 3 task notes a `detection_status` field (e.g. `"pending"`)
on `reports`, used to retry detection if the internal call to
`POST /api/detect` fails during upload. This isn't in the Week 1
schema above — if it's needed, it'll be added as a migration and
announced to the team before merging, per Section 7.
