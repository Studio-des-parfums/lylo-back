from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "images" / "logo-sdp.png"

# Palette
C_PRIMARY = colors.HexColor("#996f56")
C_SECONDARY = colors.HexColor("#d7cdc6")
C_BG_LIGHT = colors.HexColor("#f7f7f6")
C_BG_DARK = colors.HexColor("#1c1816")
C_BRAND_LIGHT = colors.HexColor("#fdfbf9")
C_TEXT_DARK = colors.HexColor("#171412")
C_TEXT_SECONDARY = colors.HexColor("#7f6f66")
C_TEXT_TERTIARY = colors.HexColor("#9c8880")

PROFILE_STYLE = ParagraphStyle(
    "profile",
    fontName="Helvetica-Bold",
    fontSize=26,
    textColor=C_TEXT_DARK,
    spaceAfter=4,
    leading=30,
)

DATE_STYLE = ParagraphStyle(
    "date",
    fontName="Helvetica-Oblique",
    fontSize=10,
    textColor=C_TEXT_TERTIARY,
    spaceAfter=0,
)

SECTION_STYLE = ParagraphStyle(
    "section",
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=C_TEXT_TERTIARY,
    spaceBefore=18,
    spaceAfter=8,
    letterSpacing=1.5,
)

NOTE_STYLE = ParagraphStyle(
    "note",
    fontName="Helvetica",
    fontSize=12,
    textColor=C_TEXT_DARK,
    spaceAfter=6,
    leftIndent=8,
    leading=16,
)


def _notes_table(notes: list[str]) -> Table:
    rows = [[Paragraph(f"— {n}", NOTE_STYLE)] for n in notes]
    t = Table(rows, colWidths=[14 * cm])
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBEFORE", (0, 0), (0, -1), 2, C_PRIMARY),
    ]))
    return t


def generate_formula_pdf(formula: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = []

    # Logo
    if _LOGO_PATH.exists():
        logo = Image(str(_LOGO_PATH), width=4 * cm, height=4 * cm, kind="proportional")
        story.append(logo)
        story.append(Spacer(1, 0.6 * cm))

    # Ligne décorative
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=16))

    # Nom du profil
    profile = formula.get("profile", "")
    story.append(Paragraph(profile, PROFILE_STYLE))

    # Date + référence sur la même ligne
    date = formula.get("date", "")
    reference = formula.get("reference", "")
    if date or reference:
        parts = []
        if date:
            parts.append(date)
        if reference:
            parts.append(reference)
        story.append(Paragraph("   ·   ".join(parts), DATE_STYLE))

    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_SECONDARY, spaceAfter=0))

    # Notes
    notes_map = [
        ("NOTES DE TÊTE", formula.get("notes", {}).get("top", [])),
        ("NOTES DE CŒUR", formula.get("notes", {}).get("heart", [])),
        ("NOTES DE FOND", formula.get("notes", {}).get("base", [])),
    ]

    for label, notes in notes_map:
        if not notes:
            continue
        story.append(Paragraph(label, SECTION_STYLE))
        story.append(_notes_table(notes))
        story.append(Spacer(1, 0.3 * cm))

    # Pied de page décoratif
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY))

    doc.build(story)
    return buf.getvalue()