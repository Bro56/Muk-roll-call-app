import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)


def build_attendance_csv(course, students_with_stats):
    """students_with_stats: list of dicts with name, student_number, sessions_present,
    sessions_total, percentage."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Course", course.code, course.name])
    writer.writerow([])
    writer.writerow(["Student Number", "Full Name", "Sessions Present", "Total Sessions", "Attendance %"])
    for row in students_with_stats:
        writer.writerow([
            row["student_number"] or "-",
            row["name"],
            row["present"],
            row["total"],
            f'{row["percentage"]:.1f}%',
        ])
    return buf.getvalue().encode("utf-8")


def build_attendance_pdf(course, students_with_stats, threshold=75.0):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleMak", parent=styles["Title"], fontSize=18,
                                  textColor=colors.HexColor("#1f2947"))
    sub_style = ParagraphStyle("SubMak", parent=styles["Normal"], fontSize=11,
                                textColor=colors.HexColor("#555b7a"))

    elements = [
        Paragraph("Makerere University — Roll Call", title_style),
        Paragraph(f"Attendance Report: {course.code} — {course.name}", sub_style),
        Spacer(1, 0.6 * cm),
    ]

    data = [["#", "Student No.", "Full Name", "Present", "Total", "Attendance %", "Status"]]
    for i, row in enumerate(students_with_stats, start=1):
        status = "OK" if row["percentage"] >= threshold else "AT RISK"
        data.append([
            str(i),
            row["student_number"] or "-",
            row["name"],
            str(row["present"]),
            str(row["total"]),
            f'{row["percentage"]:.1f}%',
            status,
        ])

    table = Table(data, colWidths=[1 * cm, 2.6 * cm, 6.2 * cm, 2 * cm, 2 * cm, 2.6 * cm, 2.4 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2947")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d4c1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f5ee")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, row in enumerate(students_with_stats, start=1):
        if row["percentage"] < threshold:
            style_cmds.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor("#c0392b")))
        else:
            style_cmds.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor("#2e9e70")))
    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
