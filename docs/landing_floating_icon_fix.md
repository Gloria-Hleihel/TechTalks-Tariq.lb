# Landing floating icon fix

This patch fixes the red and green icon blocks on the landing hero image cards.

Problem:

- The small SVG icons were pushed into the corner because general text-span styling overrode the icon container layout.

Fix:

- Re-centers the icon containers.
- Keeps the red and green rounded icon boxes.
- Forces the SVG icons to render white, centered, and correctly sized.
- Does not change routes, backend code, JavaScript, or content.
