# CardVector OS UI Style Guide

CardVector OS v1.2.0 carries forward the UI lock for the active Tkinter app.

Future screens should use the shared design tokens and helpers in
`putnam_os.py`:

- `BRAND` for colors.
- `FONT_FAMILY`, `FONT_FALLBACKS`, and `FONT_SIZES` for typography.
- `SPACING` for page, panel, and button spacing.
- `card()` for panels.
- `label()` / `text_label()` for text.
- `primary_button()` for the main action on a screen.
- `action_button()` for normal secondary actions.
- `quiet_button()` for low-emphasis actions.
- `button_bar()` for long action rows that may need horizontal scrolling.

Do not casually introduce raw colors, one-off font sizes, or custom button
styling in new CardVector OS screens. If a new UI need appears, extend the shared
tokens or helpers first.

Native Tkinter buttons do not support true border-radius consistently. The
v1.2.0 style uses flat, padded buttons with hover states and consistent colors
instead of per-widget custom drawing.
