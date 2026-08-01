# Tariq.lb Reference Site Theme

This package makes the whole site follow the provided dashboard/map screenshots:

- warm off-white page background
- white rounded dashboard cards
- red and green icon tiles
- large editorial public/map headings
- clean admin control-center heading style
- red map/admin headers with green divider
- consistent buttons, forms, tables, modals, badges, popups, and Leaflet controls

The package preserves existing Flask routes, forms, report management logic, API calls, marker logic, clustering, filtering, and JavaScript behavior.

## Apply

Run `apply_reference_site_theme.ps1` from this folder.

## Rollback

Run `restore_previous_style.ps1` from this folder. It restores `.bak_reference_site_theme` backups and removes the added CSS file if it did not exist before.
