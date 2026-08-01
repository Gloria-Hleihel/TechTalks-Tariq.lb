# Tariq.lb Design System Consistency

This staged update adds one shared design-system layer across the Tariq.lb UI while preserving existing Flask routes, forms, Leaflet maps, admin report actions, filters, popups, and JavaScript behavior.

## Files Covered

- `templates/base.html`
- `templates/map.html`
- `templates/report_detail.html`
- `templates/admin/login.html`
- `templates/admin/dashboard.html`
- `templates/admin/report_detail.html`
- `static/css/design-system.css`

## Design Decisions

- One global background: `#f7f7f5`
- One shared color system: red `#7b0d1e`, green `#4a7c59`, dark `#1a1a1a`, white cards
- Shared card, button, input, table, badge, modal, map-control, and popup styling
- Shared hover and fade-up animations
- Navbar is no longer fixed during scrolling, so pages do not slide underneath it
- Standalone templates receive only a CSS hook and body class; backend logic is untouched

## Rollback

The installer creates `.bak_design_system_consistency` backups before replacing files. Run the rollback script from this package to restore the previous visual style.
