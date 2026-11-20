"""报告导出（F-04）：模板渲染 PDF / 长图，不使用 LLM。

报告是最终交付物，必须稳定、可复现、可截图（V3 4.4）。
本模块只读取数据库里的报告 JSON，不重新计算任何分数。
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

# ---------- 字体 ----------

_FONT_CANDIDATES: tuple[tuple[str, int], ...] = (
    (r"C:\Windows\Fonts\msyh.ttc", 0),
    (r"C:\Windows\Fonts\simhei.ttf", 0),
    (r"C:\Windows\Fonts\simsun.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
    ("/System/Library/Fonts/PingFang.ttc", 0),
)
_BOLD_CANDIDATES: tuple[tuple[str, int], ...] = (
    (r"C:\Windows\Fonts\msyhbd.ttc", 0),
    (r"C:\Windows\Fonts\simhei.ttf", 0),
) + _FONT_CANDIDATES

PDF_FONT = "CJK"
PDF_FONT_BOLD = "CJK-Bold"

_font_state: dict[str, Any] = {"registered": False, "regular": None, "bold": None}


def _pick_font(candidates: tuple[tuple[str, int], ...]) -> tuple[str, int] | None:
    for path, index in candidates:
        if Path(path).exists():
            return path, index
    return None


def _ensure_fonts() -> None:
    if _font_state["registered"]:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular = _pick_font(_FONT_CANDIDATES)
    if regular is None:
        raise RuntimeError(
            "未找到可用的中文字体，无法导出报告。请安装 Microsoft YaHei / 黑体 / Noto CJK。"
        )
    bold = _pick_font(_BOLD_CANDIDATES) or regular
    pdfmetrics.registerFont(TTFont(PDF_FONT, regular[0], subfontIndex=regular[1]))
    pdfmetrics.registerFont(TTFont(PDF_FONT_BOLD, bold[0], subfontIndex=bold[1]))
    _font_state.update({"registered": True, "regular": regular, "bold": bold})


# ---------- 展示辅助 ----------

SUGGESTION_COLORS = {
    "建议投递": "#14795f",
    "谨慎投递": "#9a6a00",
    "建议放弃": "#a33636",
}
SEVERITY_TEXT = {"low": "低", "medium": "中", "high": "高", "critical": "极高"}
JD_LEVEL_TEXT = {"low": "低", "medium": "中", "high": "高"}
COMPANY_LEVEL_TEXT = {
    "low_risk": "低风险",
    "medium_risk": "中风险",
    "high_risk": "高风险",
    "unknown": "未评估",
}


def _line(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _company_fact(item: dict) -> str:
    detail = item.get("detail") or {}
    return _line(detail.get("summary") or item.get("note"), "无")


# ---------- PDF ----------

def render_pdf(report: dict) -> bytes:
    _ensure_fonts()

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"求职决策报告 {report.get('report_id', '')}",
        author="大专生求职避坑平台",
    )

    base = ParagraphStyle(
        "Base",
        fontName=PDF_FONT,
        fontSize=9.5,
        leading=15,
        textColor=colors.HexColor("#17201d"),
        wordWrap="CJK",
        alignment=TA_LEFT,
        spaceAfter=3,
    )
    title_style = ParagraphStyle(
        "Title", parent=base, fontName=PDF_FONT_BOLD, fontSize=20, leading=28, spaceAfter=2
    )
    h2_style = ParagraphStyle(
        "H2", parent=base, fontName=PDF_FONT_BOLD, fontSize=12.5, leading=18,
        spaceBefore=10, spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "Small", parent=base, fontSize=8.5, leading=13, textColor=colors.HexColor("#4b5a55")
    )
    muted_style = ParagraphStyle(
        "Muted", parent=base, fontSize=8.5, leading=13, textColor=colors.HexColor("#7b8a84")
    )

    def p(text: str, style=base) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    story: list = []
    verdict = report.get("verdict") or {}
    suggestion = verdict.get("final_suggestion", "谨慎投递")
    accent = colors.HexColor(SUGGESTION_COLORS.get(suggestion, "#4b5a55"))

    story.append(p("岗位投递决策报告", title_style))
    story.append(
        p(
            f"报告编号 {report.get('report_id', '')} · 生成时间 "
            f"{datetime.now():%Y-%m-%d %H:%M}",
            muted_style,
        )
    )
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8e4")))

    veto_reason = verdict.get("veto_reason")
    verdict_text = f"最终建议：{suggestion}"
    if veto_reason:
        verdict_text += f"（一票否决：{veto_reason}）"
    verdict_table = Table(
        [[p(verdict_text, ParagraphStyle(
            "Verdict", parent=base, fontName=PDF_FONT_BOLD, fontSize=14, leading=22,
            textColor=accent,
        ))]],
        colWidths=[174 * mm],
    )
    verdict_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f8f6")),
                ("BOX", (0, 0), (-1, -1), 1, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(Spacer(1, 8))
    story.append(verdict_table)

    jd_risk = report.get("jd_risk") or {}
    company = report.get("company_score") or {}
    consistency = report.get("consistency") or {}

    score_cells = [
        [
            p("岗位风险分", small_style),
            p("公司可信分", small_style),
            p("一致性不一致项", small_style),
        ],
        [
            p(
                f"{jd_risk.get('score', '—')}（{JD_LEVEL_TEXT.get(jd_risk.get('level'), '—')}）",
                ParagraphStyle("N1", parent=base, fontName=PDF_FONT_BOLD, fontSize=16, leading=22),
            ),
            p(
                _line(company.get("score")) if company.get("available") else "—",
                ParagraphStyle("N2", parent=base, fontName=PDF_FONT_BOLD, fontSize=16, leading=22),
            ),
            p(
                f"{len(consistency.get('mismatches') or [])}",
                ParagraphStyle("N3", parent=base, fontName=PDF_FONT_BOLD, fontSize=16, leading=22),
            ),
        ],
    ]
    score_table = Table(score_cells, colWidths=[58 * mm, 58 * mm, 58 * mm])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8e4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8e4")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(Spacer(1, 10))
    story.append(score_table)

    jd = report.get("jd") or {}
    story.append(p("一、岗位信息", h2_style))
    jd_rows = [
        ["公司", _line(jd.get("company")), "岗位", _line(jd.get("position"))],
        ["薪资", _line(jd.get("salary")), "学历", _line(jd.get("education"))],
        ["宣称规模", _line(jd.get("claimed_headcount")), "到访地址", _line(jd.get("visit_address"))],
    ]
    jd_table = Table(
        [[p(c, small_style) for c in row] for row in jd_rows],
        colWidths=[22 * mm, 65 * mm, 22 * mm, 65 * mm],
    )
    jd_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8e4")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f6f8f6")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f6f8f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(jd_table)

    story.append(p("二、JD 风险扫描与原文证据", h2_style))
    hits = jd_risk.get("hits") or []
    if not hits:
        story.append(p("规则引擎未命中风险话术。未命中不代表无风险，请结合公司核验与人工判断。", small_style))
    else:
        hit_rows = [[p("类别", small_style), p("原文片段", small_style), p("扣分", small_style)]]
        for hit in hits[:30]:
            hit_rows.append(
                [
                    p(hit.get("type", ""), small_style),
                    p(f"「{hit.get('fragment', '')}」", small_style),
                    p(f"{hit.get('penalty', 0):g}", small_style),
                ]
            )
        hit_table = Table(hit_rows, colWidths=[38 * mm, 108 * mm, 28 * mm])
        hit_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8e4")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f6f8f6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(hit_table)
        for hit in hits[:12]:
            story.append(
                p(f"· {hit.get('explanation', '')}", muted_style)
            )
        if len(hits) > 30:
            story.append(p(f"（仅展示前 30 条，共 {len(hits)} 条）", muted_style))

    story.append(p("三、公司可信度核验", h2_style))
    if company.get("available"):
        if company.get("score") is None:
            story.append(
                p(
                    "可用证据覆盖不足"
                    f"（{float(company.get('coverage') or 0):.0%}），暂不给出公司可信度分数。",
                    small_style,
                )
            )
        else:
            story.append(
                p(
                    f"可信分 {company.get('score')} / 100，"
                    f"{COMPANY_LEVEL_TEXT.get(company.get('level'), '—')}，"
                    f"置信度 {company.get('confidence', '低')}。",
                    small_style,
                )
            )
        deductions = company.get("deductions") or []
        if deductions:
            for item in deductions:
                story.append(
                    p(
                        f"· {item.get('source', '')}：{item.get('fact', '')}"
                        f"（扣 {item.get('penalty', 0):g} 分）",
                        base,
                    )
                )
        else:
            story.append(p("当前证据未发现低于基线的事项。", small_style))
        missing = company.get("missing_sources") or []
        if missing:
            story.append(p(f"缺失信号：{'、'.join(missing)}。", muted_style))
    else:
        missing = company.get("missing_sources") or []
        story.append(
            p(
                "本次未获取到任何主体证据，因此不给出公司可信度分数。"
                + (f"缺失来源：{'、'.join(missing)}。" if missing else ""),
                small_style,
            )
        )

    story.append(p("四、JD—主体一致性校验", h2_style))
    mismatches = consistency.get("mismatches") or []
    if not mismatches:
        story.append(p("本次没有发现 JD 宣称与主体事实的直接矛盾。", small_style))
    else:
        mismatch_rows = [
            [p("类别", small_style), p("JD 宣称", small_style), p("主体事实", small_style), p("等级", small_style)]
        ]
        for item in mismatches:
            mismatch_rows.append(
                [
                    p(item.get("category", ""), small_style),
                    p(_line(item.get("jd_claim")), small_style),
                    p(_line(item.get("subject_fact")), small_style),
                    p(SEVERITY_TEXT.get(item.get("severity"), item.get("severity", "")), small_style),
                ]
            )
        mismatch_table = Table(mismatch_rows, colWidths=[24 * mm, 58 * mm, 70 * mm, 22 * mm])
        mismatch_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8e4")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f6f8f6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(mismatch_table)
    story.append(
        p(
            f"已核对：{'、'.join(consistency.get('rules_evaluated') or []) or '无'}；"
            f"证据不足暂未核对：{'、'.join(consistency.get('rules_not_evaluable') or []) or '无'}。"
            "未核对不代表无风险。",
            muted_style,
        )
    )

    story.append(p("五、证据链", h2_style))
    chain = report.get("evidence_chain") or []
    if not chain:
        story.append(p("本次没有可展示的证据条目。", small_style))
    else:
        for item in chain[:40]:
            detail = item.get("detail") or {}
            info = detail.get("summary") or detail.get("fragment") or ""
            story.append(
                p(
                    f"· [{item.get('evidence_id', '')}] {item.get('source', '')}"
                    + (f"：{info}" if info else ""),
                    small_style,
                )
            )

    story.append(Spacer(1, 8))
    story.append(
        p(
            report.get("disclaimer")
            or "本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。",
            muted_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()


# ---------- 长图 ----------

def _pil_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    chosen = _pick_font(_BOLD_CANDIDATES if bold else _FONT_CANDIDATES)
    if chosen is None:
        raise RuntimeError("未找到可用的中文字体，无法生成长图。")
    path, index = chosen
    return ImageFont.truetype(path, size=size, index=index)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text).splitlines() or [""]:
        current = ""
        for char in raw_line:
            candidate = current + char
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = char
        lines.append(current)
    return lines


def render_png(report: dict) -> bytes:
    width = 1080
    margin = 56
    content_width = width - margin * 2
    height = 20000

    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    regular = _pil_font(26)
    bold = _pil_font(34, bold=True)
    title_font = _pil_font(48, bold=True)
    small = _pil_font(22)
    tiny = _pil_font(20)

    y = 56
    ink = (23, 32, 29)
    muted = (123, 138, 132)
    line = (226, 232, 228)

    def text_line(text: str, font, fill=ink, gap: int = 10, x: int = margin) -> None:
        nonlocal y
        draw.text((x, y), text, font=font, fill=fill)
        y += font.size + gap

    def paragraph(text: str, font=regular, fill=ink, gap: int = 12) -> None:
        nonlocal y
        for line_text in _wrap(draw, text, font, content_width):
            draw.text((margin, y), line_text, font=font, fill=fill)
            y += font.size + 8
        y += gap

    def heading(text: str) -> None:
        nonlocal y
        y += 18
        draw.rectangle([margin, y + 2, margin + 6, y + 34], fill=(20, 121, 95))
        draw.text((margin + 18, y), text, font=bold, fill=ink)
        y += 48

    def section_line() -> None:
        nonlocal y
        draw.line([margin, y, width - margin, y], fill=line, width=2)
        y += 14

    verdict = report.get("verdict") or {}
    suggestion = verdict.get("final_suggestion", "谨慎投递")
    accent_hex = SUGGESTION_COLORS.get(suggestion, "#4b5a55")
    accent = tuple(int(accent_hex[i : i + 2], 16) for i in (1, 3, 5))

    draw.text((margin, y), "岗位投递决策报告", font=title_font, fill=ink)
    y += 66
    draw.text(
        (margin, y),
        f"报告编号 {report.get('report_id', '')} · {datetime.now():%Y-%m-%d %H:%M}",
        font=tiny,
        fill=muted,
    )
    y += 40
    section_line()

    draw.rounded_rectangle(
        [margin, y, width - margin, y + 116], radius=16, outline=accent, width=3, fill=(246, 248, 246)
    )
    draw.text((margin + 28, y + 20), f"最终建议：{suggestion}", font=bold, fill=accent)
    if verdict.get("veto_reason"):
        draw.text((margin + 28, y + 68), f"一票否决：{verdict['veto_reason']}", font=small, fill=ink)
    y += 140

    jd_risk = report.get("jd_risk") or {}
    company = report.get("company_score") or {}
    consistency = report.get("consistency") or {}
    cards = [
        ("岗位风险分", f"{jd_risk.get('score', '—')}（{JD_LEVEL_TEXT.get(jd_risk.get('level'), '—')}）"),
        (
            "公司可信分",
            _line(company.get("score")) if company.get("available") else "—",
        ),
        ("一致性不一致项", str(len(consistency.get("mismatches") or []))),
    ]
    card_width = (content_width - 24) // 3
    for index, (label, value) in enumerate(cards):
        x = margin + index * (card_width + 12)
        draw.rounded_rectangle([x, y, x + card_width, y + 110], radius=14, outline=line, width=2)
        draw.text((x + 20, y + 16), label, font=tiny, fill=muted)
        draw.text((x + 20, y + 52), value, font=bold, fill=ink)
    y += 136

    jd = report.get("jd") or {}
    heading("一、岗位信息")
    for label, value in [
        ("公司", _line(jd.get("company"))),
        ("岗位", _line(jd.get("position"))),
        ("薪资", _line(jd.get("salary"))),
        ("学历", _line(jd.get("education"))),
        ("宣称规模", _line(jd.get("claimed_headcount"))),
        ("到访地址", _line(jd.get("visit_address"))),
    ]:
        paragraph(f"{label}：{value}", small, gap=4)

    heading("二、JD 风险扫描与原文证据")
    hits = jd_risk.get("hits") or []
    if not hits:
        paragraph("规则引擎未命中风险话术。未命中不代表无风险，请结合公司核验与人工判断。", small, muted)
    else:
        for hit in hits[:20]:
            paragraph(
                f"【{hit.get('type', '')}】「{hit.get('fragment', '')}」  −{hit.get('penalty', 0):g} 分",
                regular,
                gap=2,
            )
            paragraph(hit.get("explanation", ""), tiny, muted, gap=8)
        if len(hits) > 20:
            paragraph(f"（仅展示前 20 条，共 {len(hits)} 条）", tiny, muted)

    heading("三、公司可信度核验")
    if company.get("available"):
        if company.get("score") is None:
            paragraph(
                "可用证据覆盖不足"
                f"（{float(company.get('coverage') or 0):.0%}），暂不给出公司可信度分数。",
                small,
            )
        else:
            paragraph(
                f"可信分 {company.get('score')} / 100，"
                f"{COMPANY_LEVEL_TEXT.get(company.get('level'), '—')}，"
                f"置信度 {company.get('confidence', '低')}。",
                small,
            )
        deductions = company.get("deductions") or []
        for item in deductions:
            paragraph(
                f"· {item.get('source', '')}：{item.get('fact', '')}（扣 {item.get('penalty', 0):g} 分）",
                small,
            )
        if not deductions:
            paragraph("当前证据未发现低于基线的事项。", small, muted)
        if company.get("missing_sources"):
            paragraph(f"缺失信号：{'、'.join(company['missing_sources'])}。", tiny, muted)
    else:
        paragraph(
            "本次未获取到任何主体证据，因此不给出公司可信度分数。"
            + (
                f"缺失来源：{'、'.join(company.get('missing_sources') or [])}。"
                if company.get("missing_sources")
                else ""
            ),
            small,
            muted,
        )

    heading("四、JD—主体一致性校验")
    mismatches = consistency.get("mismatches") or []
    if not mismatches:
        paragraph("本次没有发现 JD 宣称与主体事实的直接矛盾。", small, muted)
    for item in mismatches:
        paragraph(
            f"{item.get('category', '')}｜JD：{_line(item.get('jd_claim'))}｜事实：{_line(item.get('subject_fact'))}"
            f"｜{SEVERITY_TEXT.get(item.get('severity'), '')}",
            small,
            gap=8,
        )
    paragraph(
        f"已核对：{'、'.join(consistency.get('rules_evaluated') or []) or '无'}；"
        f"暂未核对：{'、'.join(consistency.get('rules_not_evaluable') or []) or '无'}。未核对不代表无风险。",
        tiny,
        muted,
    )

    heading("五、证据链")
    chain = report.get("evidence_chain") or []
    if not chain:
        paragraph("本次没有可展示的证据条目。", small, muted)
    for item in chain[:30]:
        detail = item.get("detail") or {}
        info = detail.get("summary") or detail.get("fragment") or ""
        paragraph(
            f"[{item.get('evidence_id', '')}] {item.get('source', '')}" + (f"：{info}" if info else ""),
            tiny,
            gap=4,
        )

    y += 16
    section_line()
    paragraph(
        report.get("disclaimer")
        or "本结果基于公开信息自动分析，仅供参考，不构成对任何企业的事实认定或法律判断。",
        tiny,
        muted,
        gap=0,
    )
    y += 40

    image = image.crop((0, 0, width, min(y, height)))
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()
