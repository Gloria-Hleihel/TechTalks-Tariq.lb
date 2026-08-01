# Landing impact copy and readability fix

This patch fixes the landing page impact strip shown in the screenshot.

Changes:

- Fixes invisible white text on the first impact card.
- Replaces technical wording with simple user-facing language.
- Removes terms like model image size, confidence, YOLOv8, and damage classes from the visible landing-page cards.
- Keeps backend behavior unchanged.

Updated files:

- `templates/index.html`
- `static/css/reference-theme.css`
