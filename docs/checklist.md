# Delivery Checklist — Tariq.lb
Week 5 · Walkthrough by Zahraa

Last updated: July 2026

This checklist follows Section 11 of the 5-week project plan.
Each item is marked as complete ✅, in progress ⏳, or pending ❌.

---

## Core User Flow

| Item | Status | Owner |
|------|--------|-------|
| User can upload a road photo (JPG/PNG) | ✅ Complete | Malek |
| GPS coordinates auto-extracted from EXIF | ✅ Complete | Malek |
| User shown whether GPS detected or manual needed | ✅ Complete | Malek |
| Manual map-pin selection works | ✅ Complete | Malek/Gloria |
| YOLOv8 detects road damage from uploaded image | ✅ Complete | Majd |
| Damage type classified | ✅ Complete | Majd |
| Confidence score generated and stored | ✅ Complete | Majd |
| Severity score and label generated | ✅ Complete | Majd |
| Annotated image saved and displayable | ✅ Complete | Majd |
| Report saved to SQLite database | ✅ Complete | Zahraa |
| Report appears as colored pin on Leaflet map | ✅ Complete | Gloria |
| Clicking pin shows popup with damage info | ✅ Complete | Gloria |
| Report detail page loads with full info | ✅ Complete | Zahraa/Gloria |

---

## Map & Filters

| Item | Status | Owner |
|------|--------|-------|
| Map filter by damage type | ✅ Complete | Gloria |
| Map filter by severity level | ✅ Complete | Gloria |
| Map legend visible and accurate | ✅ Complete | Gloria |
| Map loads within 2 seconds with 30+ reports | ⏳ To verify | Gloria |

---

## Admin Panel

| Item | Status | Owner |
|------|--------|-------|
| Admin login page accessible and working | ✅ Complete | Zahraa |
| Admin dashboard shows all reports | ✅ Complete | Zahraa |
| Admin can update report status | ✅ Complete | Zahraa |
| Admin can delete report (cascade deletes detection) | ✅ Complete | Zahraa |
| Admin sees analytics summary | ✅ Complete | Zahraa |

---

## Code Quality & Engineering

| Item | Status | Owner |
|------|--------|-------|
| Unit tests written and passing | ✅ 17/17 passing | Zahraa/Malek |
| API endpoints tested with valid and invalid inputs | ✅ Complete | Zahraa |
| Error handling for wrong file type, GPS failure, detection failure | ✅ Complete | Malek/Zahraa |
| No debug print statements in production code | ⏳ To verify | All |
| All feature branches merged into main | ⏳ Pending PR #7 merge | Zahraa/Majd |
| At least one teammate reviewed every PR | ✅ Complete | All |
| File upload type and size validation in place | ✅ Complete | Malek |

---

## Documentation

| Item | Status | Owner |
|------|--------|-------|
| README.md complete with setup and run instructions | ✅ Complete | Zahraa |
| docs/api.md complete with all endpoints documented | ✅ Complete | Zahraa |
| docs/schema.md complete with all tables and fields | ✅ Complete | Zahraa |
| docs/setup_guide.md written | ✅ Complete | Zahraa |
| docs/user_guide.md written | ⏳ Pending | Malek |
| Final project report compiled and submitted | ⏳ Pending | Zahraa/All |
| Presentation slides ready | ⏳ Pending | Malek |

---

## Summary

| Module | Owner | Status |
|--------|-------|--------|
| M1 — Report Submission | Malek | ✅ Complete |
| M2 — AI Detection Engine | Majd | ✅ Complete |
| M3 — Map & Visualization | Gloria | ✅ Complete |
| M4 — Database & Admin | Zahraa | ✅ Complete |
| M5 — Integration, Testing & Docs | All | ⏳ Final steps remaining |

---

## Known Gaps Before Final Submission

- PR #7 (`feature/zahraa-admin-panel`) pending merge by Majd
- `docs/user_guide.md` pending from Malek
- Presentation slides pending from Malek
- Final project report pending compilation
- Map load time with 30+ reports needs final verification

---

*Tariq.lb — Delivery Checklist · Zahraa · Week 5*