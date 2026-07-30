# Database Schema — Tariq.lb

Owner: Zahraa  
Last updated: Week 3 integration

## Reports table

One row is created for each uploaded road report.

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | Integer | Yes | Primary key |
| `image_path` | String(255) | Yes | Relative static path such as `uploads/photo.jpg` |
| `lat` | Float | Yes | Report latitude |
| `lng` | Float | Yes | Report longitude |
| `location_source` | String(10) | Yes | `gps` or `manual` |
| `status` | String(20) | Yes | `pending`, `reviewed`, or `resolved` |
| `detection_status` | String(20) | Yes | `pending` or `completed` |
| `detection_error` | String(500) | No | Latest timeout or detection failure |
| `created_at` | DateTime | Yes | Creation date and time |

A failed detection does not delete the report. The report remains saved
with `detection_status="pending"` and can be retried.

## Detections table

| Field | Type | Required | Description |
|---|---|---:|---|
| `id` | Integer | Yes | Primary key |
| `report_id` | Integer | Yes | Foreign key to `reports.id` |
| `damage_type` | String(50) | Yes | `Pothole`, `Road Crack`, `Surface Wear`, `Other`, or `None` |
| `confidence` | Float | Yes | Detection confidence from 0 to 1 |
| `severity_score` | Integer | Yes | Score from 0 to 100 |
| `severity_label` | String(20) | Yes | `Low`, `Medium`, `High`, or `Critical` |
| `annotated_image_path` | String(255) | No | Relative path to annotated output image |

## Relationship

```text
Report 1 -------- many Detection rows
```

The current application normally keeps one Detection per Report.

## Week 3 migration

Existing databases created before Week 3 must run:

```powershell
python scripts/migrate_add_detection_status.py
```

This adds:

```text
reports.detection_status
reports.detection_error
```

Reports that already have a Detection are marked as `completed`.