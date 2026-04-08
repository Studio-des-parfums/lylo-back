from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def generate_formula_pdf(formula: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], fontSize=20, spaceAfter=6, textColor=colors.HexColor("#3a2e2a")
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#7f6f66"), spaceAfter=20, fontName="Helvetica-Oblique"
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=14, textTransform="uppercase"
    )
    note_style = ParagraphStyle(
        "note", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#3a2e2a"), spaceAfter=2, leftIndent=12
    )

    profile = formula.get("profile", "")
    description = formula.get("description", "")
    top_notes = formula.get("top_notes", [])
    heart_notes = formula.get("heart_notes", [])
    base_notes = formula.get("base_notes", [])
    sizes = formula.get("sizes", {})

    story = []

    story.append(Paragraph(profile, title_style))
    if description:
        story.append(Paragraph(description, subtitle_style))

    # Notes
    for label, notes in [("Notes de tête", top_notes), ("Notes de cœur", heart_notes), ("Notes de fond", base_notes)]:
        if not notes:
            continue
        story.append(Paragraph(label, section_style))
        for note in notes:
            story.append(Paragraph(f"• {note}", note_style))

    # Quantités par taille
    if sizes:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Quantités par format", section_style))

        for size_key in ("10ml", "30ml", "50ml"):
            size_data = sizes.get(size_key)
            if not size_data:
                continue

            story.append(Paragraph(size_key, ParagraphStyle(
                "sizekey", parent=styles["Normal"], fontSize=10,
                fontName="Helvetica-Bold", textColor=colors.HexColor("#3a2e2a"),
                spaceBefore=8, spaceAfter=4
            )))

            rows = []
            for note_key, note_label in [("top_notes", "Tête"), ("heart_notes", "Cœur"), ("base_notes", "Fond")]:
                for n in size_data.get(note_key, []):
                    rows.append([note_label, n["name"], f"{n['ml']} ml"])
            for b in size_data.get("boosters", []):
                rows.append(["Booster", b["name"], f"{b['ml']} ml"])

            if rows:
                table = Table([["Famille", "Note", "Quantité"]] + rows, colWidths=[3 * cm, 9 * cm, 3 * cm])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f0ed")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#555555")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf8f7")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5ddd8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(table)

    doc.build(story)
    return buf.getvalue()