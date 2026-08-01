# Tariq.lb Production Readiness Audit

Prepared as a safe staging patch. The patch does not redesign the UI or remove existing functionality.

## Executive Summary

Tariq.lb is a solid MVP Flask application with clear blueprints for reports, detection, and admin workflows. The main pre-submission risks are security hardening, upload/inference path validation, public-map scalability, and admin dashboard database efficiency. The staged patch improves those areas while preserving the current pages and user flows.

## Security Audit

### Findings Fixed

- Admin login, status update, delete, and upload POST routes had no CSRF protection. The patch adds a lightweight CSRF helper, hidden form fields, and fetch headers for admin AJAX actions.
- Admin login used direct string comparison and kept the existing session. The patch uses constant-time comparison, optional `ADMIN_PASSWORD_HASH`, clears the session on login, and marks the admin session permanent.
- Cookies were not explicitly hardened. The patch sets `HttpOnly`, `SameSite=Lax`, configurable `Secure`, and a two-hour session lifetime.
- The detection API accepted paths that could resolve outside the project. The patch restricts detection to `static/uploads` and `test_images`.
- Uploaded images were extension-checked and Pillow-verified, but not checked for browser MIME type, true format, or pixel bomb size. The patch adds MIME/type checks and `MAX_IMAGE_PIXELS` validation.
- Security headers were missing. The patch adds CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and HTTPS-only HSTS.
- Admin pages could be browser-cached. The patch sets `Cache-Control: no-store` for `/admin` responses.
- Basic in-memory rate limiting now protects admin login, upload, feedback, detection, and locality search endpoints.
- Production mode now fails fast if the default Flask secret or demo admin password is still active.

### Remaining Security Recommendations

- Replace the fallback `ADMIN_PASSWORD=changeme` before any public demo or deployment.
- Prefer `ADMIN_PASSWORD_HASH` generated with Werkzeug instead of a plaintext environment password.
- Use a shared external rate limiter, such as Redis-backed Flask-Limiter, when deploying with multiple workers.
- Move from SQLite to PostgreSQL for multi-user deployment.
- Consider nonce-based CSP after inline CSS/JS is moved into static files.

## Performance Audit

### Findings Fixed

- The admin dashboard queried each report's detections lazily. The patch uses `selectinload` to reduce N+1 queries.
- Dashboard counts were computed through many repeated queries. The patch uses grouped aggregate queries.
- Public `/api/reports` returned all live reports without validating filters or supporting viewport bounds. The patch validates filters, supports `north/south/east/west`, applies a configurable cap, and updates the Leaflet page to send bounds.
- The public map could duplicate reports if multiple detections existed. The patch uses one report payload with the best detection.
- Models lacked useful indexes. The patch adds indexes on report status, created date, latitude, longitude, location source, detection report ID, damage type, and severity.
- The landing hero PNG was about 2.8 MB. The patch adds a WebP version around 301 KB and uses it through a `<picture>` fallback.
- Static cache headers were missing. The patch adds browser cache headers for `/static` responses.
- Compression was not configured. The patch adds optional Flask-Compress support and requirements for gzip/Brotli.
- Locality search rebuilt normalized village/city names repeatedly while users typed. The patch caches a reusable search index and preloads it at startup.
- YOLO inference now supports configurable production warmup through `DETECTION_PRELOAD_MODEL=1` and suppresses verbose inference logging during web requests.

### Remaining Performance Recommendations

- Move large inline CSS/JS from templates into page-specific static files once the UI stabilizes.
- Add hashed filenames or a manifest before increasing static cache lifetimes beyond one day.
- Store uploaded images outside the repository folder for production and serve through a static/media service.
- Add pagination/server-side filtering to the admin table if reports grow into the thousands.
- Move asynchronous detection jobs from in-memory storage to Redis/Celery for production.

## Accessibility Review

Fixed items:

- Shared navigation modal buttons now expose dialog controls with `aria-haspopup`, `aria-controls`, and `aria-expanded`.
- Modal JavaScript updates opener state, restores focus, and keeps the page header/footer hidden from assistive tech while a modal is active.
- The upload locality search now announces loading/results, supports `aria-activedescendant`, marks selected options, and aborts stale searches while typing.
- The report-location map is keyboard-focusable and described as a map region with concise instructions.
- The admin dashboard tabs now use `aria-controls`, `aria-labelledby`, hidden inactive panels, arrow-key navigation, and reduced-motion-safe statistics.
- Admin table rows are keyboard-focusable, and update/delete actions have specific labels.
- Admin login fields now have explicit labels, autocomplete hints, and alert semantics for errors.

Remaining accessibility recommendations:

- Run Lighthouse and a screen-reader pass after the final UI freeze.
- Move inline CSS/JS into static files so a stricter CSP can be used without `unsafe-inline`.
- Add automated browser accessibility checks, such as axe-core through Playwright, if the project adds end-to-end tests.

## Database Review

The schema is appropriate for the current MVP: one `Report` with zero or more linked `Detection` records, cascade delete enabled. The patch improves lookup performance with indexes and switches relationship loading to `selectin`, which is a better fit for pages that render many reports.

For production, use migrations rather than relying on `db.create_all()`. The patch makes auto-create configurable through `AUTO_CREATE_DATABASE` so it can remain convenient locally and be disabled in production.

## API Review

Fixed items:

- `/api/reports` now validates severity and damage filters.
- `/api/reports` now validates bounds and limit parameters.
- `/api/lebanon-localities/search` now rejects overly long queries.
- `/api/detect` is safer because detector path validation now blocks paths outside allowed folders.
- Public abuse-sensitive endpoints now return `429 Too Many Requests` when local rate limits are exceeded.
- Repeated detection calls for the same report now update the existing detection result instead of creating duplicates.

Recommended next items:

- Add authentication or a signed internal token for detection APIs if they are exposed beyond local development.
- Add consistent JSON errors for every API route.

## Frontend Review

The patch avoids redesigning the UI. It only adds:

- WebP homepage image fallback.
- Explicit image dimensions and async decoding.
- Lazy loading for below-the-fold/report preview images.
- CSRF tokens for existing forms and admin fetch calls.
- Map-bound API requests on public Leaflet map movement.

## Testing Added

- Security headers are present.
- Admin login rejects missing CSRF when CSRF is enabled.
- Admin login accepts a valid CSRF token.
- Public map API rejects invalid filters.
- Public map API supports bounds plus limit.
- Public map API rejects malformed bounds.
- Oversized-pixel uploads are rejected without creating reports.
- Duplicate detection API calls update one stored detection row.
- Admin delete removes uploaded and annotated images.
- Arabic locality aliases survive deduplication for curated places.
- Admin login rate limiting blocks repeated attempts.
- Production mode rejects unsafe default secrets.
- Locality search preloading builds a reusable cache.
- Runtime preloading respects the configured performance flags.
- Admin dashboard accessibility landmarks, tabs, rows, and map labels are present.
- Upload page locality search and map accessibility markup is present.

## Files Modified or Added

- `app/__init__.py`
- `app/security.py`
- `app/admin/routes.py`
- `app/reports/routes.py`
- `app/reports/location.py`
- `app/utils/storage.py`
- `app/detection/detector.py`
- `app/detection/jobs.py`
- `app/detection/routes.py`
- `config.py`
- `models.py`
- `run.py`
- `requirements.txt`
- `templates/index.html`
- `templates/upload.html`
- `templates/map.html`
- `templates/report_detail.html`
- `templates/admin/login.html`
- `templates/admin/dashboard.html`
- `templates/admin/report_detail.html`
- `tests/test_security_hardening.py`
- `tests/test_public_map_reports.py`
- `tests/test_upload_flow.py`
- `scripts/optimize_static_assets.py`
- `static/images/landing-road-hero.webp`

## Estimated Impact

- Homepage hero image transfer can drop by roughly 85-90% for WebP-capable browsers.
- Admin dashboard database query count should drop substantially as report volume grows because detections are eager-loaded and counts are grouped.
- Public map payload size improves when many reports exist because viewport bounds and limits are now supported.
- Security posture improves from MVP-level to much closer to submission/production readiness.

## Deployment Checklist

- Set `SECRET_KEY` to a strong random value.
- Set `ADMIN_USERNAME` and either `ADMIN_PASSWORD` or preferably `ADMIN_PASSWORD_HASH`.
- Set `SESSION_COOKIE_SECURE=1` behind HTTPS.
- Set `AUTO_CREATE_DATABASE=0` after migrations are introduced.
- Install requirements, including `Flask-Compress` and `Brotli`.
- Run `python -m pytest tests` before pushing.
