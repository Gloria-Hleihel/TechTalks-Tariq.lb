# Completed Reports and the Live Map

This change keeps completed reports in the admin dashboard while removing them from the public live map.

## Behavior

- Public live map (`/map`) reads from `/api/reports`.
- `/api/reports` now excludes reports whose internal status is `resolved`.
- Admin dashboard still loads every report, including completed ones.
- The admin UI displays the existing `resolved` status as `Completed` so administrators can understand it clearly.
- No database migration is required.

## Why this is safe

The project already uses these status values internally:

- `pending`
- `reviewed`
- `resolved`
- `rejected`

This patch does not rename the database status value. It only changes public map visibility and admin labels.

## Manual QA

1. Start the Flask app.
2. Open `/admin/dashboard`.
3. Mark a report as `Completed`.
4. Confirm the completed count increases in the admin dashboard.
5. Open `/map`.
6. Confirm the completed report no longer appears on the public live map.
7. Return to `/admin/dashboard` and confirm the report is still visible when filtering by Completed.