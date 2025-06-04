# report_generator.py

import json
import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image


def main():
    # 1) Locate the JSON report
    rpt_path = Path("report.json")
    if not rpt_path.exists():
        print("⚠️ report.json not found, skipping PDF generation")
        return

    try:
        data = json.loads(rpt_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ ERROR reading report.json: {e}", file=sys.stderr)
        return

    summary = data.get("summary", {})
    total  = summary.get("total",   summary.get("collected",  0))
    passed = summary.get("passed",  0)
    failed = summary.get("failed",  0)

    # 2) Generate a .md document

    md_lines = [
        "# Test Report Summary",
        f"- **Total tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        "",
        "## Failed Tests Details",
    ]

    for t in data.get("tests", []):
        if t.get("outcome") == "failed":
            nodeid_md = t["nodeid"]
            # look up the assertion message under call.crash.message
            msg = t.get("call", {}) \
                .get("crash", {}) \
                .get("message", "<no message>")
            md_lines.append(f"- `{nodeid_md}`: {msg}")

    md_text = "\n".join(md_lines)
    with open("TEST_REPORT.md", "w", encoding="utf-8") as md_out:
        md_out.write(md_text)
    print("✔️ TEST_REPORT.md generated")

    # 3) Prepare the PDF document
    pdf_path = Path("TEST_REPORT.pdf")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    # a centered title style
    styles.add(ParagraphStyle(
        name="CenteredTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
    ))

    story = []

    # 4) Add your logo (centered) if it exists
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        try:
            img_logo = Image(str(logo_path), width=2*inch, height=2*inch)
            img_logo.hAlign = "CENTER"
            story.append(img_logo)
            story.append(Spacer(1, 12))
        except Exception as img_err:
            print(f"⚠️ Could not embed logo.png: {img_err}", file=sys.stderr)

    # 5) Add a big, centered title
    story.append(Paragraph("Test Report Summary", styles["CenteredTitle"]))
    story.append(Spacer(1, 12))

    # 6) Summary stats
    body = styles["BodyText"]
    story.append(Paragraph(f"<b>Total tests:</b> {total}", body))
    story.append(Paragraph(f"<b>Passed:</b> {passed}", body))
    story.append(Paragraph(f"<b>Failed:</b> {failed}", body))
    story.append(Spacer(1, 12))

    # 7) Failed‐tests header
    story.append(Paragraph("Failed Tests Details", styles["Heading2"]))
    story.append(Spacer(1, 6))

    # 8) Loop through each failed test
    for t in data.get("tests", []):
        if t.get("outcome") == "failed":
            nodeid = t["nodeid"]
            msg    = t.get("call", {}) \
                      .get("crash", {}) \
                      .get("message", "<no message>")

            # —8a) Print the nodeid (bold)
            safe_node = nodeid.replace("/", " / ")
            header_text = f"<b>{safe_node}</b>:"
            story.append(Paragraph(header_text, body))
            story.append(Spacer(1, 4))

            # —8b) Print the failure message itself (normal text)
            #     This ensures the failure message appears immediately before any screenshot.
            story.append(Paragraph(msg, body))
            story.append(Spacer(1, 8))

            # —8c) Check for a screenshot in user_properties
            screenshot_path = None
            for name, value in t.get("user_properties", []):
                if name == "screenshot":
                    screenshot_path = value
                    break

            if screenshot_path:
                abs_path = Path(os.getcwd()) / screenshot_path
                print(f"▶️ Found screenshot for {nodeid}: {abs_path} (exists? {abs_path.exists()})")

                if abs_path.is_file():
                    try:
                        # Scale to a reasonable size (6" wide, 3" tall)
                        img = Image(abs_path, width=6 * inch, height=3 * inch)
                        img.hAlign = "CENTER"
                        story.append(img)
                        story.append(Spacer(1, 12))
                    except Exception as img_err:
                        story.append(Paragraph(f"[Unable to insert screenshot: {img_err}]", body))
                        story.append(Spacer(1, 12))
                else:
                    story.append(Paragraph("[No screenshot file found]", body))
                    story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("[No screenshot captured]", body))
                story.append(Spacer(1, 12))

    # 9) Build the PDF (catch any exceptions)
    print("ℹ️ About to build PDF…")
    try:
        doc.build(story)
        print("✔️ TEST_REPORT.pdf generated")
    except Exception as e:
        print(f"❌ ERROR generating TEST_REPORT.pdf: {e}", file=sys.stderr)
        fallback = Path("TEST_REPORT_ERROR.txt")
        fallback.write_text(f"PDF generation failed:\n{e}\n", encoding="utf-8")
        print(f"ℹ️ Wrote fallback error to {fallback}")


if __name__ == "__main__":
    main()
