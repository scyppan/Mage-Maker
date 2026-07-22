import tkinter.font as tkfont


FONT_FAMILY = "Segoe UI"
FONT_WEIGHT = "normal"
FONT_WEIGHT_STRONG = "bold"

APP_BACKGROUND = "#EDE4F4"
SURFACE = "#FBF8FD"
SURFACE_MUTED = "#F2EBF7"
SURFACE_RAISED = "#E7DBED"

FIELD_BACKGROUND = "#FFFFFF"
FIELD_HOVER = "#F8F2FB"
FIELD_FOCUS = "#7D5190"
FIELD_DISABLED = "#E8E1EB"

PRIMARY = "#7D5190"
PRIMARY_DARK = "#5B3A69"
PRIMARY_LIGHT = "#DDC8E7"
PRIMARY_SOFT = "#E4D5EB"
PRIMARY_HOVER = "#6B417D"

BUTTON_SOFT = "#E8DDEE"
BUTTON_SOFT_HOVER = "#D8C7E1"
BUTTON_DISABLED = "#EEE9F0"
DELETE_SOFT = "#F1DDE3"
DELETE_HOVER = "#E5C2CC"

TEXT_DARK = "#302437"
TEXT_MUTED = "#6D5C73"
TEXT_LIGHT = "#FFFFFF"
TEXT_DISABLED = "#9B919E"

BORDER = "#C8B6D1"
BORDER_SOFT = "#DED2E4"
LIST_ALTERNATE = "#F7F1FA"
LIST_HOVER = "#E8D9EF"
LIST_SELECTED = "#D4BAE0"

CONTROL_RADIUS = 10


def app_font(size, weight=FONT_WEIGHT):
    return (FONT_FAMILY, size, weight)


def configure_tk_fonts(root):
    for font_name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    ):
        try:
            named_font = tkfont.nametofont(font_name, root=root)
        except tk.TclError:
            continue

        named_font.configure(family=FONT_FAMILY, weight=FONT_WEIGHT)
