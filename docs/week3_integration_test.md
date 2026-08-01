# Week 3 — End-to-End Upload Integration Test

## Scope

Verify the complete merged upload flow:

1. Upload a real road photo.
2. Confirm GPS is extracted or choose a manual location.
3. Confirm `POST /api/detect` is triggered.
4. Confirm the Report remains saved if detection fails.
5. Confirm a successful Detection is linked to the Report.
6. Confirm the report pin appears on the map.
7. Confirm the upload form works at a 375px viewport.

## Required merged components

- Malek: upload and report flow
- Majd: `POST /api/detect`
- Gloria: `/map` and `GET /api/reports`
- Zahraa: shared database models

## Setup

```powershell
python scripts/migrate_add_detection_status.py
python -m pytest -q
python run.py
```

Open:

```text
http://127.0.0.1:5000/upload
```

## Manual test record

| Field | Result |
|---|---|
| Date | Not run yet |
| Tester | Malek |
| Branch or commit | Add after testing |
| Browser | Add after testing |
| Road photo | Add filename |
| Location source | GPS / manual |
| Report ID | Add after testing |
| Detection request fired | Pass / Fail |
| Detection status | completed / pending |
| Detection row saved | Pass / Fail / N/A |
| Pin visible on `/map` | Pass / Fail |
| 375px mobile layout | Pass / Fail |
| Notes or bugs | Add observations |

## Failure-mode checklist

| Case | Expected result | Actual result |
|---|---|---|
| Wrong extension | Reject with JPG or PNG guidance; no Report created | Not run |
| Corrupted image | Reject invalid image; no Report created | Not run |
| File larger than 5MB | Reject with compression guidance; no Report created | Not run |
| No GPS and no map pin | Ask user to select location; no Report created | Not run |
| GPS exception with manual pin | Save Report using manual coordinates | Not run |
| Detection timeout | Save Report with `detection_status="pending"` | Not run |
| Detection API error | Save Report with `detection_status="pending"` | Not run |
| Retry succeeds | Create Detection and mark status `completed` | Not run |

## Completion note

Do not mark the end-to-end integration test as complete until Majd's
detection endpoint and Gloria's map branch are merged.

The automated tests verify Malek's upload-side behavior. A real
detection request and visible map pin require all related branches