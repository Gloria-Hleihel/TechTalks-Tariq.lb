# Admin Workflow Sections

This change turns the admin status workflow into three clear sections instead of one mixed "all statuses" list.

## Sections

- Live: reports with internal status `pending`. New reports start here by default.
- Under Review: reports with internal status `reviewed`.
- Done: reports with internal status `resolved` or `rejected`.

## Public Live Map

The public `/map` page uses `/api/reports`. Done reports are now hidden from that API, so completed or rejected reports stay in admin history but no longer appear on the live public map.

## Admin Behavior

- The dashboard opens on Live by default.
- Changing a report to Done removes it from Live immediately.
- The Done count remains visible.
- Clicking Done shows completed/rejected reports.
- Clicking Under Review shows reports being checked.
- Existing severity, damage type, location, date, search, table, map, update, and delete behavior stays intact.

## QA Checklist

1. Open `/admin/dashboard`.
2. Confirm the default section is Live.
3. Mark one report as Done.
4. Confirm it disappears from Live.
5. Click Done and confirm the report is there.
6. Open `/map` and confirm the Done report is not visible.
7. Mark another report as Under Review and confirm it appears in the Under Review section.