"""Report exporters — turn a parsed report dict into a downloadable PDF or DOCX.

PDF generation uses ReportLab. CJK is wired via the Adobe Asian Font Pack
CIDFonts that ship with ReportLab (STSong-Light for Simplified Chinese), which
means we get Chinese / Japanese / Korean rendering without bundling any TTF.
The CJK CIDFont is registered as the body font; the standard PostScript Type-1
"Helvetica" still works for ASCII fallback because PDF readers handle font
substitution at glyph time.

DOCX generation uses python-docx — Word handles unicode natively, so we only
need to set a CJK-friendly font name (`Microsoft YaHei`) in the run's
`rFonts` element so Word picks the right glyph table for East-Asian runs.
"""
from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional
import re

from app.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Mirrors the frontend's ENUMERATED_BREAK_RE — inserts a newline before
# inline-numbered items so "1. foo 2. bar" prints as a list rather than one
# wall-of-text paragraph.
_ENUMERATED_BREAK_RE = re.compile(
    r'(?<!^)(?<=[\s.。;；!！?？)）"”\]])(?=(?:\(?\d{1,2}[.、)）]|[①-⑳])\s*\S)'
)


def _format_numbered(text: Optional[str]) -> str:
    if not text:
        return ""
    if "\n" in text:
        return text
    return _ENUMERATED_BREAK_RE.sub("\n", text)


_RISK_LABEL = {
    "high": ("High Risk / 高风险", "#b91c1c"),
    "medium": ("Medium Risk / 中风险", "#b45309"),
    "low": ("Low Risk / 低风险", "#0f766e"),
}


def _risk_label(severity: str) -> str:
    return _RISK_LABEL.get(severity, ("—", "#475569"))[0]


def _format_remaining(days):
    if not isinstance(days, int):
        return None
    if days < 0:
        return f"{abs(days)} days overdue / 已逾期 {abs(days)} 天"
    if days == 0:
        return "Due today / 今天到期"
    return f"{days} days remaining / 还剩 {days} 天"


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

_CJK_FONT_REGISTERED = False


def _ensure_cjk_font() -> str:
    """Register Adobe's STSong-Light CIDFont once. Returns the font name."""
    global _CJK_FONT_REGISTERED
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    if not _CJK_FONT_REGISTERED:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        _CJK_FONT_REGISTERED = True
    return "STSong-Light"


def generate_pdf_bytes(report: Dict, file_name: str = "contract") -> bytes:
    """Render the analysis report to a PDF and return the raw bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether
    )
    from reportlab.platypus.flowables import HRFlowable

    font_name = _ensure_cjk_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"SpotClause Report — {file_name}",
        author="SpotClause AI",
    )

    base = getSampleStyleSheet()

    h1 = ParagraphStyle("H1", parent=base["Heading1"], fontName=font_name,
                        fontSize=20, leading=26, spaceAfter=4 * mm,
                        textColor=colors.HexColor("#0f172a"))
    h2 = ParagraphStyle("H2", parent=base["Heading2"], fontName=font_name,
                        fontSize=14, leading=20, spaceBefore=6 * mm,
                        spaceAfter=2 * mm, textColor=colors.HexColor("#1e293b"))
    h3 = ParagraphStyle("H3", parent=base["Heading3"], fontName=font_name,
                        fontSize=11.5, leading=16, spaceBefore=3 * mm,
                        spaceAfter=1 * mm, textColor=colors.HexColor("#334155"))
    body = ParagraphStyle("Body", parent=base["BodyText"], fontName=font_name,
                          fontSize=10, leading=14, spaceAfter=1 * mm,
                          textColor=colors.HexColor("#1f2937"))
    muted = ParagraphStyle("Muted", parent=body, textColor=colors.HexColor("#64748b"),
                           fontSize=9, leading=12)
    quote = ParagraphStyle("Quote", parent=body, leftIndent=6 * mm,
                           textColor=colors.HexColor("#475569"), fontSize=9.5,
                           leading=13, spaceBefore=1 * mm, spaceAfter=1 * mm)
    label_style = ParagraphStyle("Label", parent=body, fontSize=9, leading=12,
                                 textColor=colors.HexColor("#64748b"),
                                 spaceBefore=2 * mm, spaceAfter=0)

    elements = []

    # Header
    elements.append(Paragraph(f"<b>SpotClause AI — Contract Review Report</b>", h1))
    elements.append(Paragraph(file_name or "Contract", muted))
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.6))
    elements.append(Spacer(1, 3 * mm))

    # Tags row
    contract_type = report.get("contractType") or "—"
    jurisdiction = report.get("jurisdiction") or "—"
    elements.append(Paragraph(
        f"<b>Type:</b> {_pdf_escape(contract_type)} &nbsp;&nbsp;&nbsp; "
        f"<b>Jurisdiction:</b> {_pdf_escape(jurisdiction)}",
        body,
    ))

    # Summary
    if report.get("summary"):
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(_pdf_escape(report["summary"]), body))

    # Risk breakdown table
    rb = report.get("riskBreakdown") or {}
    if rb:
        data = [[
            Paragraph(f"<b>{rb.get('high', 0)}</b><br/><font size=8>High / 高</font>", body),
            Paragraph(f"<b>{rb.get('medium', 0)}</b><br/><font size=8>Medium / 中</font>", body),
            Paragraph(f"<b>{rb.get('low', 0)}</b><br/><font size=8>Low / 低</font>", body),
        ]]
        tbl = Table(data, colWidths=[58 * mm, 58 * mm, 58 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fee2e2")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fef3c7")),
            ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#ccfbf1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(Spacer(1, 3 * mm))
        elements.append(tbl)

    # Risky clauses
    risky: List[Dict] = report.get("riskyClauses") or []
    if risky:
        elements.append(Paragraph("Risky Clauses / 风险条款", h2))
        for c in risky:
            block: List = []
            block.append(Paragraph(
                f"<b>{_pdf_escape(_risk_label(c.get('severity', 'low')))}</b> · "
                f"{_pdf_escape(c.get('clauseTitle') or '')}",
                h3,
            ))
            if c.get("originalText"):
                block.append(Paragraph("Original / 原文：", label_style))
                block.append(Paragraph(_pdf_escape(c["originalText"]), quote))
            if c.get("legalBasis"):
                block.append(Paragraph("Risk Reason / 风险原因：", label_style))
                block.append(Paragraph(_pdf_escape(_format_numbered(c["legalBasis"])), body))
            if c.get("plainExplanation"):
                block.append(Paragraph("Explanation / 说明：", label_style))
                block.append(Paragraph(_pdf_escape(_format_numbered(c["plainExplanation"])), body))
            if c.get("solution"):
                block.append(Paragraph("Suggested Fix / 建议：", label_style))
                block.append(Paragraph(_pdf_escape(_format_numbered(c["solution"])), body))
            ns = c.get("negotiationScript") or {}
            if any([ns.get("yourOpening"), ns.get("theirRebuttal"), ns.get("yourResponse")]):
                block.append(Paragraph("Negotiation / 谈判：", label_style))
                if ns.get("yourOpening"):
                    block.append(Paragraph(f"<b>You:</b> {_pdf_escape(ns['yourOpening'])}", body))
                if ns.get("theirRebuttal"):
                    block.append(Paragraph(f"<b>Them:</b> {_pdf_escape(ns['theirRebuttal'])}", body))
                if ns.get("yourResponse"):
                    block.append(Paragraph(f"<b>You:</b> {_pdf_escape(ns['yourResponse'])}", body))
            block.append(Spacer(1, 2 * mm))
            block.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.3))
            elements.append(KeepTogether(block))

    # Missing clauses
    missing: List[Dict] = report.get("missingClauses") or []
    if missing:
        elements.append(Paragraph("Missing Clauses / 缺失条款", h2))
        for m in missing:
            block = []
            block.append(Paragraph(
                f"<b>{_pdf_escape(_risk_label(m.get('severity', 'medium')))}</b> · "
                f"{_pdf_escape(m.get('title') or '')}",
                h3,
            ))
            if m.get("description"):
                block.append(Paragraph(_pdf_escape(_format_numbered(m["description"])), body))
            if m.get("suggestedText"):
                block.append(Paragraph("Suggested Wording / 建议条款：", label_style))
                block.append(Paragraph(_pdf_escape(_format_numbered(m["suggestedText"])), quote))
            block.append(Spacer(1, 2 * mm))
            elements.append(KeepTogether(block))

    # Key dates
    dates: List[Dict] = report.get("keyDates") or []
    if dates:
        elements.append(Paragraph("Key Dates / 关键日期", h2))
        rows = [["Date", "Remaining", "Milestone"]]
        for d in dates:
            rows.append([
                d.get("date", ""),
                _format_remaining(d.get("daysRemaining")) or "—",
                d.get("milestone") or "—",
            ])
        col_widths = [30 * mm, 50 * mm, doc.width - 80 * mm]
        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, 0), font_name),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(tbl)

    # Key terms
    terms: List[Dict] = report.get("keyTerms") or []
    if terms:
        elements.append(Paragraph("Key Terms / 关键术语", h2))
        rows = [["Term", "Plain Meaning"]]
        for term in terms:
            rows.append([term.get("term", ""), term.get("plainMeaning", "")])
        col_widths = [55 * mm, doc.width - 55 * mm]
        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(tbl)

    # Footer / disclaimer
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.4))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "SpotClause AI is not a law firm. This report is for reference only and is not legal advice. "
        "SpotClause AI 非律师事务所，本报告仅供参考，不构成法律意见。",
        muted,
    ))

    doc.build(elements)
    return buffer.getvalue()


_HTML_ESCAPE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
}


def _pdf_escape(text) -> str:
    """ReportLab's Paragraph parser is a tiny HTML subset; raw &/</> break it.

    Also collapse runs of whitespace except for explicit newlines (which become <br/>).
    """
    if text is None:
        return ""
    s = str(text)
    # Preserve explicit line breaks
    parts = s.split("\n")
    out_parts = []
    for part in parts:
        escaped = "".join(_HTML_ESCAPE.get(ch, ch) for ch in part)
        out_parts.append(escaped)
    return "<br/>".join(out_parts)


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

def generate_docx_bytes(report: Dict, file_name: str = "contract") -> bytes:
    """Render the analysis report to a DOCX and return the raw bytes."""
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    doc = Document()

    # Tighten default page margins
    for section in doc.sections:
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)

    # Default style — set a CJK-friendly font so Word doesn't fall back to
    # Calibri for East-Asian glyphs.
    base_style = doc.styles["Normal"]
    base_style.font.name = "Microsoft YaHei"
    base_rpr = base_style.element.xpath(".//w:rPr")
    if base_rpr:
        rfonts = OxmlElement("w:rFonts")
        rfonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        rfonts.set(qn("w:ascii"), "Microsoft YaHei")
        rfonts.set(qn("w:hAnsi"), "Microsoft YaHei")
        base_rpr[0].append(rfonts)

    def _set_cjk_font(run, font_name="Microsoft YaHei"):
        run.font.name = font_name
        rPr = run._element.get_or_add_rPr()
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:eastAsia"), font_name)
        rFonts.set(qn("w:ascii"), font_name)
        rFonts.set(qn("w:hAnsi"), font_name)
        rPr.append(rFonts)

    def _add_heading(text, level=1, color="#0f172a"):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.bold = True
        if level == 1:
            run.font.size = Pt(20)
        elif level == 2:
            run.font.size = Pt(14)
        else:
            run.font.size = Pt(11.5)
        run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
        _set_cjk_font(run)
        return p

    def _add_paragraph(text, *, italic=False, color=None, size=10, bold=False):
        p = doc.add_paragraph()
        for i, chunk in enumerate(str(text).split("\n")):
            run = p.add_run(chunk)
            run.font.size = Pt(size)
            run.italic = italic
            run.bold = bold
            if color:
                run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))
            _set_cjk_font(run)
            if i < len(str(text).split("\n")) - 1:
                p.add_run().add_break()
        return p

    def _add_label(text):
        return _add_paragraph(text, color="#64748b", size=9, bold=True)

    # Title block
    _add_heading("SpotClause AI — Contract Review Report", level=1)
    _add_paragraph(file_name or "Contract", color="#64748b", size=9, italic=True)
    doc.add_paragraph()

    # Tags
    tags = []
    if report.get("contractType"):
        tags.append(f"Type: {report['contractType']}")
    if report.get("jurisdiction"):
        tags.append(f"Jurisdiction: {report['jurisdiction']}")
    if tags:
        _add_paragraph(" · ".join(tags), color="#1e293b", size=10, bold=True)

    # Summary
    if report.get("summary"):
        _add_paragraph(report["summary"])

    # Risk breakdown
    rb = report.get("riskBreakdown") or {}
    if rb:
        tbl = doc.add_table(rows=1, cols=3)
        tbl.style = "Light Grid Accent 1"
        cells = tbl.rows[0].cells
        cells[0].text = f"High / 高: {rb.get('high', 0)}"
        cells[1].text = f"Medium / 中: {rb.get('medium', 0)}"
        cells[2].text = f"Low / 低: {rb.get('low', 0)}"
        for cell in cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    _set_cjk_font(run)
                    run.bold = True
        doc.add_paragraph()

    # Risky clauses
    risky = report.get("riskyClauses") or []
    if risky:
        _add_heading("Risky Clauses / 风险条款", level=2)
        for c in risky:
            _add_heading(
                f"[{_risk_label(c.get('severity', 'low'))}] {c.get('clauseTitle') or ''}",
                level=3,
            )
            if c.get("originalText"):
                _add_label("Original / 原文：")
                _add_paragraph(c["originalText"], color="#475569", size=9.5, italic=True)
            if c.get("legalBasis"):
                _add_label("Risk Reason / 风险原因：")
                _add_paragraph(_format_numbered(c["legalBasis"]))
            if c.get("plainExplanation"):
                _add_label("Explanation / 说明：")
                _add_paragraph(_format_numbered(c["plainExplanation"]))
            if c.get("solution"):
                _add_label("Suggested Fix / 建议：")
                _add_paragraph(_format_numbered(c["solution"]))
            ns = c.get("negotiationScript") or {}
            if any([ns.get("yourOpening"), ns.get("theirRebuttal"), ns.get("yourResponse")]):
                _add_label("Negotiation / 谈判：")
                if ns.get("yourOpening"):
                    _add_paragraph(f"You: {ns['yourOpening']}")
                if ns.get("theirRebuttal"):
                    _add_paragraph(f"Them: {ns['theirRebuttal']}")
                if ns.get("yourResponse"):
                    _add_paragraph(f"You: {ns['yourResponse']}")

    # Missing clauses
    missing = report.get("missingClauses") or []
    if missing:
        _add_heading("Missing Clauses / 缺失条款", level=2)
        for m in missing:
            _add_heading(
                f"[{_risk_label(m.get('severity', 'medium'))}] {m.get('title') or ''}",
                level=3,
            )
            if m.get("description"):
                _add_paragraph(_format_numbered(m["description"]))
            if m.get("suggestedText"):
                _add_label("Suggested Wording / 建议条款：")
                _add_paragraph(_format_numbered(m["suggestedText"]), color="#475569", italic=True)

    # Key dates
    dates = report.get("keyDates") or []
    if dates:
        _add_heading("Key Dates / 关键日期", level=2)
        tbl = doc.add_table(rows=1, cols=3)
        tbl.style = "Light Grid Accent 1"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Date"
        hdr[1].text = "Remaining"
        hdr[2].text = "Milestone"
        for cell in hdr:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
                    _set_cjk_font(run)
        for d in dates:
            row = tbl.add_row().cells
            row[0].text = d.get("date", "")
            row[1].text = _format_remaining(d.get("daysRemaining")) or "—"
            row[2].text = d.get("milestone") or "—"
            for cell in row:
                for para in cell.paragraphs:
                    for run in para.runs:
                        _set_cjk_font(run)

    # Key terms
    terms = report.get("keyTerms") or []
    if terms:
        _add_heading("Key Terms / 关键术语", level=2)
        tbl = doc.add_table(rows=1, cols=2)
        tbl.style = "Light Grid Accent 1"
        hdr = tbl.rows[0].cells
        hdr[0].text = "Term"
        hdr[1].text = "Plain Meaning"
        for cell in hdr:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.bold = True
                    _set_cjk_font(run)
        for term in terms:
            row = tbl.add_row().cells
            row[0].text = term.get("term", "")
            row[1].text = term.get("plainMeaning", "")
            for cell in row:
                for para in cell.paragraphs:
                    for run in para.runs:
                        _set_cjk_font(run)

    # Disclaimer
    doc.add_paragraph()
    disc = doc.add_paragraph()
    disc_run = disc.add_run(
        "SpotClause AI is not a law firm. This report is for reference only and is not legal advice. "
        "SpotClause AI 非律师事务所，本报告仅供参考，不构成法律意见。"
    )
    disc_run.font.size = Pt(8)
    disc_run.font.color.rgb = RGBColor.from_string("64748b")
    _set_cjk_font(disc_run)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def sanitize_filename(name: str, default: str = "contract") -> str:
    """Strip path-segments and trim length so the filename is safe for the
    user's filesystem when written client-side. Preserves CJK characters —
    they're allowed on every major OS we support. For HTTP headers, pair
    this with `ascii_filename` below for the latin-1-safe fallback."""
    if not name:
        return default
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    base = base.rsplit(".", 1)[0]  # drop original extension
    cleaned = re.sub(r"[^\w一-鿿぀-ゟ゠-ヿ㐀-䶿\-. ]+", "_", base)
    cleaned = cleaned.strip(" ._") or default
    return cleaned[:80]


def ascii_filename(name: str, default: str = "contract") -> str:
    """Strict-ASCII filename for the `filename=` slot in Content-Disposition.

    RFC 6266 requires `filename=` to be latin-1; HTTP/1.1 disallows non-ASCII
    octets in header values. Browsers that don't understand `filename*=UTF-8''`
    fall back to this token, so it must be readable enough that the file isn't
    mysterious to the user — but we can't keep CJK characters here. We strip
    them to underscores; if the result is empty, fall back to `default`.
    """
    if not name:
        return default
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0]
    cleaned = re.sub(r"[^A-Za-z0-9 _.\-]+", "_", base)
    cleaned = re.sub(r"_+", "_", cleaned).strip(" ._") or default
    return cleaned[:80]
