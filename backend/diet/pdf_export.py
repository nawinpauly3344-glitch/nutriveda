"""
PDF Export — converts the diet plan markdown to a clean, professional PDF using ReportLab.
Design principles:
  - Dark navy table headers (#1E3A5F) with white text — always readable
  - Smart column widths per table type (meal tables get wider Food Item column)
  - Paragraph objects in table cells for proper word-wrapping — no overlap
  - Section-coded H2 banner strips (dark backgrounds, white text)
  - Clean typography: Helvetica, consistent spacing
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

PDF_DIR = Path(__file__).parent.parent / "pdf_plans"
PDF_DIR.mkdir(exist_ok=True)


# ── Markdown parser ────────────────────────────────────────────────────────────

def _parse_md(text: str) -> list[dict]:
    """Parse plan markdown into structured blocks."""
    blocks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        raw = line.strip()

        if raw.startswith("### "):
            blocks.append({"type": "h3", "text": raw[4:].strip()})
        elif raw.startswith("## "):
            blocks.append({"type": "h2", "text": raw[3:].strip()})
        elif raw.startswith("# "):
            blocks.append({"type": "h1", "text": raw[2:].strip()})
        elif raw.startswith("|"):
            # Collect consecutive table lines
            tlines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tlines.append(lines[i].strip())
                i += 1
            rows = []
            for tl in tlines:
                # Skip separator lines like |---|---|
                if re.match(r"^\|[-| :]+\|$", tl):
                    continue
                cells = [c.strip() for c in tl.split("|")[1:-1]]
                if cells:
                    rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
            continue
        elif raw in ("---", "***", "___") or re.match(r"^-{3,}$", raw):
            blocks.append({"type": "divider"})
        elif raw.startswith("- ") or raw.startswith("• "):
            txt = re.sub(r"^[-•]\s+", "", raw)
            blocks.append({"type": "bullet", "text": txt})
        elif raw.startswith(">"):
            blocks.append({"type": "tip", "text": raw.lstrip("> ").strip()})
        elif not raw:
            blocks.append({"type": "spacer"})
        else:
            blocks.append({"type": "para", "text": raw})

        i += 1
    return blocks


def _clean(text: str) -> str:
    """Strip markdown symbols for plain text."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    return text.strip()


def _html(text: str) -> str:
    """Convert **bold** and *italic* to ReportLab XML tags."""
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    text = text.replace("&", "&amp;").replace("<b>", "\x00B\x00").replace("</b>", "\x00/B\x00") \
               .replace("<i>", "\x00I\x00").replace("</i>", "\x00/I\x00")
    # Now escape remaining < > then restore tags
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\x00B\x00", "<b>").replace("\x00/B\x00", "</b>") \
               .replace("\x00I\x00", "<i>").replace("\x00/I\x00", "</i>")
    return text


# ── Section colour resolver ────────────────────────────────────────────────────

def _section_hex(heading: str) -> str:
    """Return dark background hex colour for a section heading banner."""
    t = heading.lower()
    if any(k in t for k in ["exercise", "workout", "fitness", "training"]):
        return "#1E3A5F"   # Deep navy
    if any(k in t for k in ["supplement", "vitamin", "mineral"]):
        return "#3B0F6B"   # Deep purple
    if any(k in t for k in ["hydration", "water", "drink"]):
        return "#0A4050"   # Deep teal
    if any(k in t for k in ["avoid", "restrict", "limit", "never"]):
        return "#7F1D1D"   # Deep red
    if any(k in t for k in ["cheat", "indulg", "treat", "sunday"]):
        return "#6B210A"   # Deep amber
    if any(k in t for k in ["tip", "habit", "sleep", "recovery"]):
        return "#1E293B"   # Slate
    if any(k in t for k in ["blueprint", "nutritional", "macro", "calorie"]):
        return "#1E293B"   # Slate
    return "#065F46"       # Dark emerald (default / meals)


# ── Smart column widths ────────────────────────────────────────────────────────

def _col_widths(header_row: list[str], page_width_cm: float = 17.0):
    """
    Assign column widths proportionally based on header keywords.
    Ensures text never overflows by giving content-heavy columns more space.
    """
    from reportlab.lib.units import cm
    n = len(header_row)
    if n == 0:
        return []

    # Weight map: keywords → relative weight
    WEIGHTS = {
        # Wide content columns
        "ingredient": 3.8,                 # "Ingredient" column — food names need lots of space
        "food": 3.5, "item": 3.5, "description": 3.5, "detail": 3.0,
        "what": 3.5, "eat": 3.5,           # "What to Eat" column
        "alternative": 2.0,                # Alternative food column
        "benefit": 2.8, "exercise": 2.2, "activity": 2.2,
        "notes": 2.2,                      # Notes column — recipe assumptions etc.
        "source": 2.0, "topic": 1.8,
        # Medium columns
        "meal": 1.3, "day": 1.1,
        "quantity": 1.2, "amount": 1.2, "portion": 1.2, "qty": 1.0,
        # Narrow columns — short numbers or times
        "time": 0.85,
        "calories": 0.9, "kcal": 0.9,
        "protein": 0.95, "carbs": 0.85, "carbohydrates": 0.9,
        "fat": 0.8, "fats": 0.8,
    }
    weights = []
    for h in header_row:
        h_low = h.lower().lstrip("~").strip()  # strip leading ~ so "~kcal" → "kcal"
        w = 1.0  # default weight
        for kw, wt in WEIGHTS.items():
            if kw in h_low:
                w = max(w, wt)   # take best match, don't break early
        weights.append(w)

    total_w = sum(weights)
    return [round((wt / total_w) * page_width_cm, 2) * cm for wt in weights]


# ── Table renderer ────────────────────────────────────────────────────────────

def _build_table(rows: list[list[str]]):
    """
    Build a ReportLab Table with:
    - Dark navy header row (always readable)
    - Smart column widths (no text overflow)
    - Paragraph objects in cells (word wrapping)
    - Meal-type row colour coding
    - Alternating row shading
    """
    from reportlab.platypus import Table, TableStyle, Spacer, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.units import cm

    if not rows:
        return []

    # Header row detection
    header = rows[0]
    data_rows = rows[1:]

    # Colours
    HDR_BG   = colors.HexColor("#1E3A5F")   # Dark navy — always visible with white text
    HDR_TEXT = colors.white
    ROW_BF   = colors.HexColor("#FFFBEB")   # Breakfast
    ROW_LN   = colors.HexColor("#FFF7ED")   # Lunch
    ROW_DN   = colors.HexColor("#EFF6FF")   # Dinner
    ROW_SN   = colors.HexColor("#F0FDF4")   # Snack
    ROW_TOT  = colors.HexColor("#F1F5F9")   # Total
    ROW_ALT  = colors.HexColor("#FAFAFA")   # Alt
    GRID_CLR = colors.HexColor("#CBD5E1")

    # Cell paragraph styles
    ps_hdr = ParagraphStyle("th", fontSize=9, textColor=HDR_TEXT,
                            fontName="Helvetica-Bold", leading=12,
                            spaceAfter=0, spaceBefore=0)
    ps_cell = ParagraphStyle("td", fontSize=9, textColor=colors.HexColor("#1A202C"),
                             fontName="Helvetica", leading=12,
                             spaceAfter=0, spaceBefore=0, wordWrap="CJK")
    ps_cell_bold = ParagraphStyle("td_b", fontSize=9, textColor=colors.HexColor("#1A202C"),
                                  fontName="Helvetica-Bold", leading=12,
                                  spaceAfter=0, spaceBefore=0, wordWrap="CJK")

    def _para(text: str, style, is_total=False):
        txt = _clean(text)
        if is_total:
            return Paragraph(f"<b>{txt}</b>", ps_cell_bold)
        return Paragraph(txt, style)

    col_widths = _col_widths(header)
    n_cols = len(header)

    # Meal row colour detection — checks first OR second cell (ingredient tables have meal in col 0,
    # but subsequent ingredient rows leave col 0 blank and put ingredient name in col 1)
    def _meal_bg(row: list):
        # Check first non-empty cell for meal type
        combined = " ".join(c.lower() for c in row[:3])
        if any(k in combined for k in ["breakfast", "morning"]):
            return ROW_BF
        if "lunch" in combined:
            return ROW_LN
        if any(k in combined for k in ["dinner", "evening"]):
            return ROW_DN
        if any(k in combined for k in ["snack", "mid"]):
            return ROW_SN
        if any(k in combined for k in ["total", "daily", "week"]):
            return ROW_TOT
        return None

    is_meal_tbl = any(k in " ".join(header).lower()
                      for k in ["meal", "food", "kcal", "calories"])

    # Build table data as Paragraph objects
    table_data = [[_para(h, ps_hdr) for h in header]]
    row_colors = []   # (row_idx, bg_color)

    for r_idx, row in enumerate(data_rows, start=1):
        padded = row + [""] * (n_cols - len(row))
        is_total = any("total" in c.lower() or "daily total" in c.lower() for c in row)

        if is_meal_tbl:
            bg = _meal_bg(padded) or (ROW_ALT if r_idx % 2 == 0 else colors.white)
        elif is_total:
            bg = ROW_TOT
        else:
            bg = ROW_ALT if r_idx % 2 == 0 else colors.white

        row_colors.append((r_idx, bg))
        table_data.append([_para(c, ps_cell_bold if (is_total or (is_meal_tbl and i == 0)) else ps_cell, is_total)
                           for i, c in enumerate(padded)])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1,
                hAlign="LEFT", splitByRow=True)

    ts = TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0), HDR_BG),
        ("TEXTCOLOR",    (0, 0), (-1, 0), HDR_TEXT),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 9),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID",         (0, 0), (-1, -1), 0.5, GRID_CLR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT]),
    ])

    # Apply meal-specific row backgrounds
    for r_idx, bg in row_colors:
        ts.add("BACKGROUND", (0, r_idx), (-1, r_idx), bg)

    tbl.setStyle(ts)
    return [tbl, Spacer(1, 0.35 * cm)]


# ── Main PDF generator ────────────────────────────────────────────────────────

def generate_pdf(
    plan_markdown: str,
    client_name: str,
    submission_id: int,
    plan_id: int,
) -> str:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
            Table, TableStyle
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    except ImportError:
        log.error("ReportLab not installed. Run: pip install reportlab")
        return ""

    # ── Colour palette ─────────────────────────────────────────────────────────
    C_EMERALD   = colors.HexColor("#065F46")   # Dark emerald (brand)
    C_MID_GRN   = colors.HexColor("#059669")   # Accent green
    C_NAVY      = colors.HexColor("#1E3A5F")   # Table headers
    C_DARK      = colors.HexColor("#1A202C")   # Body text
    C_GRAY      = colors.HexColor("#64748B")   # Muted text
    C_LIGHT_GRN = colors.HexColor("#ECFDF5")   # Very pale green
    C_WHITE     = colors.white

    safe_name = re.sub(r"[^\w\s-]", "", client_name).replace(" ", "_")
    filename = f"diet_plan_{submission_id}_{plan_id}_{safe_name}.pdf"
    output_path = PDF_DIR / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Personalized Diet & Fitness Plan — {client_name}",
        author="NutriVeda Certified Nutrition Consultant",
    )

    # ── Styles ─────────────────────────────────────────────────────────────────
    def _ps(name, **kw):
        return ParagraphStyle(name, **kw)

    st_h1 = _ps("H1", fontSize=20, textColor=C_EMERALD, spaceAfter=6, spaceBefore=6,
                fontName="Helvetica-Bold", alignment=TA_CENTER, leading=26)
    st_h2_base = _ps("H2Base", fontSize=12, textColor=C_WHITE, spaceAfter=0,
                     spaceBefore=0, fontName="Helvetica-Bold", leading=16)
    st_h3 = _ps("H3", fontSize=11, textColor=C_NAVY, spaceAfter=4, spaceBefore=10,
                fontName="Helvetica-Bold", leading=15)
    st_body = _ps("Body", fontSize=10, textColor=C_DARK, spaceAfter=4,
                  fontName="Helvetica", leading=15, alignment=TA_JUSTIFY)
    st_bullet = _ps("Bullet", fontSize=10, textColor=C_DARK, spaceAfter=3,
                    fontName="Helvetica", leftIndent=14, leading=14)
    st_tip = _ps("Tip", fontSize=9.5, textColor=colors.HexColor("#6B210A"),
                 fontName="Helvetica-Oblique", leading=13,
                 backColor=colors.HexColor("#FFFBEB"), leftIndent=8)
    st_footer = _ps("Footer", fontSize=8, textColor=C_GRAY, alignment=TA_CENTER, leading=11)
    st_sub = _ps("Sub", fontSize=12, textColor=C_GRAY, alignment=TA_CENTER,
                 spaceAfter=3, leading=16)
    st_date = _ps("Date", fontSize=9, textColor=C_GRAY, alignment=TA_CENTER,
                  spaceAfter=10, leading=12)

    story = []

    # ── Cover header ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * cm))

    # Brand banner (dark emerald box)
    brand_data = [[Paragraph("NutriVeda", _ps("brand", fontSize=26, textColor=C_WHITE,
                                              fontName="Helvetica-Bold", alignment=TA_CENTER))]]
    brand_tbl = Table(brand_data, colWidths=[17 * cm])
    brand_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_EMERALD),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(brand_tbl)

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Certified Nutrition Consultation", st_sub))
    story.append(Paragraph("PERSONALISED DIET & FITNESS PLAN", _ps(
        "Title", fontSize=13, textColor=C_EMERALD, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=4, leading=17)))
    story.append(Paragraph(
        f"Prepared for <b>{_html(client_name)}</b>  |  "
        f"Reference NV-{submission_id:04d}  |  "
        f"{datetime.now().strftime('%d %B %Y')}",
        st_date,
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=C_EMERALD))
    story.append(Spacer(1, 0.5 * cm))

    # ── Parse and render ───────────────────────────────────────────────────────
    blocks = _parse_md(plan_markdown)
    pending_table: list | None = None

    def flush():
        nonlocal pending_table
        if pending_table:
            story.extend(_build_table(pending_table))
            pending_table = None

    strip_emoji = lambda t: re.sub(
        r"^[\U0001F300-\U0001FFFF\u2600-\u27BF\u2700-\u27BF]+\s*", "", t
    ).strip()

    for block in blocks:
        btype = block["type"]

        if btype == "table":
            if pending_table is None:
                pending_table = block["rows"]
            else:
                pending_table.extend(block["rows"])
            continue
        else:
            flush()

        if btype == "h1":
            display = strip_emoji(block["text"])
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(_html(display), st_h1))

        elif btype == "h2":
            display = strip_emoji(block["text"])
            hex_bg = _section_hex(display)
            bg_col = colors.HexColor(hex_bg)
            story.append(Spacer(1, 0.4 * cm))
            # Dark banner strip
            h2_data = [[Paragraph(f"  {_html(display)}", st_h2_base)]]
            h2_tbl = Table(h2_data, colWidths=[17 * cm])
            h2_tbl.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), bg_col),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]))
            story.append(h2_tbl)
            story.append(Spacer(1, 0.15 * cm))

        elif btype == "h3":
            display = strip_emoji(block["text"])
            story.append(Paragraph(_html(display), st_h3))

        elif btype == "divider":
            story.append(Spacer(1, 0.15 * cm))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#CBD5E1")))
            story.append(Spacer(1, 0.15 * cm))

        elif btype == "bullet":
            clean = _html(block["text"])
            story.append(Paragraph(f"• {clean}", st_bullet))

        elif btype == "tip":
            clean = _html(block["text"])
            story.append(Paragraph(f"  {clean}", st_tip))
            story.append(Spacer(1, 0.1 * cm))

        elif btype == "para":
            raw = block["text"]
            if re.match(r"^[-=]{3,}$", raw.strip()):
                continue
            story.append(Paragraph(_html(raw), st_body))

        elif btype == "spacer":
            story.append(Spacer(1, 0.12 * cm))

    flush()

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_MID_GRN))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "This plan is prepared by your certified nutrition consultant and is personalised exclusively for you. "
        "Please do not share. For any adjustments or queries, contact your nutritionist directly.",
        st_footer,
    ))

    doc.build(story)
    log.info(f"PDF generated: {output_path}")
    return str(output_path)
