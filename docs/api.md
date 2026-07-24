---

### PATCH /admin/api/admin/reports/:id
Updates the status of a specific report.

**URL parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Report ID |

**Request body (JSON):**
```json
{ "status": "reviewed" }
```

**Valid status values:** `pending`, `reviewed`, `resolved`

**Responses:**
- `200 OK` → updated report as JSON
- `400 Bad Request` → invalid status value
- `404 Not Found` → report ID doesn't exist

---

### POST /admin/update/:id
Updates report status via form submission (used by dashboard UI).

**URL parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Report ID |

**Request body (form data):**
| Field | Type | Description |
|-------|------|-------------|
| status | string | New status value |

**Response:** `302 Redirect` → `/admin/dashboard`

---

### POST /admin/delete/:id
Deletes a report and its linked detection record (cascade delete).

**URL parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Report ID |

**Responses:**
- `302 Redirect` → `/admin/dashboard` on success
- `404 Not Found` → report ID doesn't exist

---

### GET /admin/reports/:id
Returns the admin detail view for a specific report.

**URL parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Report ID |

**Response:** `200 OK` → HTML detail page showing full report
and detection data

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 302 | Redirect |
| 400 | Bad request (invalid input) |
| 404 | Resource not found |
| 405 | Method not allowed |

---

*Tariq.lb API Docs · Zahraa · Week 4*