# Cross-Browser Upload Form Test

## Purpose

Verify that the Tariq.lb report-upload form works consistently across:

- Google Chrome
- Mozilla Firefox
- Safari
- A mobile viewport with a width of 375 pixels

The test covers file selection, map interaction, form submission, loading states, validation messages, and report-page redirection.

---

## Test Environment

| Field | Value |
|---|---|
| Tester | Malek |
| Application URL | `http://127.0.0.1:5000/upload` |
| Branch | `feature/malek-upload` |
| Operating system | Windows |
| Test date | Not run yet |
| Application commit | Add commit hash after final testing |

---

## Preparation

Start the application from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python run.py