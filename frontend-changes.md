# Frontend Changes

- Added an accessible icon-only theme toggle button to the top-right of the UI in `frontend/index.html`.
- Added dark and light theme CSS custom properties in `frontend/style.css`, including background, text, surface, border, primary, and secondary colors.
- Added smooth color, shadow, transform, and icon transition styles for the toggle button.
- Added JavaScript theme switching in `frontend/script.js` using a `data-theme` attribute on the `body` element.
- Persisted the selected theme in `localStorage` and initialized the theme from the saved value or the user's system color-scheme preference.
