# CardVector OS UI Style Guide

CardVector OS uses the public `cardvector.app` website as its visual reference.
The desktop application preserves its production workflows while sharing the
website's bright blue-and-white presentation.

Core visual direction:

- white and pale-blue application surfaces
- dark navy typography
- royal-blue primary actions and active navigation
- soft blue borders and restrained depth
- generous workspace spacing
- compact, action-oriented desktop layouts
- filled status chips using quiet success, warning, and error backgrounds

Future screens should use the shared design tokens and helpers in
`putnam_os.py`:

- `BRAND` for colors.
- `FONT_FAMILY`, `FONT_FALLBACKS`, and `FONT_SIZES` for typography.
- `SPACING` for page, panel, and button spacing.
- `card()` for panels.
- `label()` / `text_label()` for text.
- `primary_button()` for filled royal-blue main actions.
- `action_button()` for blue-gray outlined secondary actions.
- `quiet_button()` for low-emphasis actions.
- `button_bar()` for long action rows that may need horizontal scrolling.
- `status_indicator()` for colored dot + text status displays.
- `style_treeview()` / `tree_insert()` for modern desktop table styling.

Do not casually introduce raw colors, one-off font sizes, or custom button
styling in new CardVector OS screens. If a new UI need appears, extend the shared
tokens or helpers first.

Native Tkinter widgets do not support the website's full border radius and
shadow system consistently. CardVector uses spacing, pale borders, clean
surfaces, and instant blue hover changes to provide the closest reliable
desktop equivalent without replacing working widgets or behavior.
