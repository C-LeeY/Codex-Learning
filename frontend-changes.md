# Frontend Changes

- Added an accessible icon-based theme toggle button in the top-right of the UI.
- Added dark and light theme CSS custom properties, including background, surface, text, border, primary, secondary, input, and shadow colors.
- Added theme-specific CSS overrides so existing frontend surfaces, messages, inputs, links, and controls adapt to the active theme.
- Integrated the light and dark themes with the app's existing CSS variables so the full chat layout switches consistently.
- Added smooth color, border, shadow, and icon transition animations for theme switching.
- Added JavaScript to initialize the theme from `localStorage` or the user's system preference, update the `data-theme` attribute on the document, persist changes, and maintain accessible toggle labels/state.
