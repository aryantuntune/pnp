"""
Background task: generate and email a per-branch item-wise daily report
at 23:59 IST every day to configured recipients.

Fixes:
- Uses a DB-level lock (daily_report_log with UNIQUE on report_date) to
  prevent duplicate sends when multiple gunicorn workers each run this loop.
- Sends a PDF attachment (all branches in one document) instead of HTML body.
"""
import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal
from app.models.branch import Branch
from app.models.daily_report_log import DailyReportLog
from app.models.daily_report_recipient import DailyReportRecipient
from app.services import email_service, report_service

logger = logging.getLogger("ssmspl.daily_report")

CHECK_INTERVAL_SECONDS = 60  # Check every minute
SEND_TIME = time(23, 59)

_last_sent_date: date | None = None


async def daily_report_loop():
    """Main loop — runs forever, fires the report once per day at 23:59 IST."""
    global _last_sent_date

    # On startup: clean up stale "sending" rows (worker crashed before finishing)
    # and seed _last_sent_date from the last successfully completed report.
    try:
        async with AsyncSessionLocal() as db:
            # Delete rows stuck in "sending" so the day can be retried
            stale = await db.execute(
                select(DailyReportLog).where(DailyReportLog.status == "sending")
            )
            for row in stale.scalars().all():
                logger.warning("Cleaning up stale daily report claim for %s", row.report_date)
                await db.delete(row)
            await db.commit()

            # Seed from last completed entry only
            latest = await db.execute(
                select(DailyReportLog.report_date)
                .where(DailyReportLog.status.in_(("sent", "no_data")))
                .order_by(DailyReportLog.report_date.desc())
                .limit(1)
            )
            row = latest.scalar_one_or_none()
            if row:
                _last_sent_date = row
                logger.info("Daily report loop: last sent date from DB = %s", _last_sent_date)
    except Exception:
        logger.exception("Failed to seed _last_sent_date from DB, starting fresh")

    while True:
        try:
            now = datetime.now(timezone.utc)
            # Convert to IST (UTC+5:30) since branches operate in India
            ist_now = now + timedelta(hours=5, minutes=30)

            if (
                ist_now.time() >= SEND_TIME
                and _last_sent_date != ist_now.date()
            ):
                _last_sent_date = ist_now.date()
                await _generate_and_send_report(ist_now.date())
        except Exception:
            logger.exception("Error in daily report loop")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def _claim_report_slot(report_date: date, recipient_count: int) -> bool:
    """Try to insert a row into daily_report_log for this date.

    Uses its own session and commits immediately so the UNIQUE constraint
    is visible to other workers.  Returns True if this worker won the slot.
    """
    async with AsyncSessionLocal() as db:
        try:
            db.add(DailyReportLog(
                report_date=report_date,
                recipient_count=recipient_count,
                status="sending",
            ))
            await db.commit()
            return True
        except IntegrityError:
            await db.rollback()
            logger.info(
                "Daily report for %s already claimed by another worker, skipping",
                report_date,
            )
            return False


async def _update_report_status(report_date: date, status: str):
    """Update the daily_report_log status after send attempt."""
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(DailyReportLog).where(DailyReportLog.report_date == report_date)
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.status = status
                await db.commit()
        except Exception:
            logger.exception("Failed to update report log status for %s", report_date)


async def _generate_and_send_report(report_date: date):
    """Collect branch-wise item summaries and email them to all active recipients."""
    async with AsyncSessionLocal() as db:
        try:
            # Get active recipients
            result = await db.execute(
                select(DailyReportRecipient).where(
                    DailyReportRecipient.is_active == True  # noqa: E712
                )
            )
            recipients = result.scalars().all()
            if not recipients:
                logger.info("No active daily report recipients, skipping")
                return

            # --- DB-level dedup: only one worker sends per day ---
            claimed = await _claim_report_slot(report_date, len(recipients))
            if not claimed:
                return

            # Get all active branches
            branch_result = await db.execute(
                select(Branch)
                .where(Branch.is_active == True)  # noqa: E712
                .order_by(Branch.name)
            )
            branches = branch_result.scalars().all()

            # Collect data for each branch
            branch_reports = []
            overall_grand_total = 0.0
            for branch in branches:
                data = await report_service.get_branch_item_summary(
                    db, report_date, report_date, branch.id
                )
                if data["rows"]:  # Only include branches that had transactions
                    branch_reports.append(data)
                    overall_grand_total += float(data["grand_total"])

            if not branch_reports:
                logger.info("No transactions today, skipping daily report email")
                await _update_report_status(report_date, "no_data")
                return

            # Build PDF with all branches
            pdf_buf = _build_daily_report_pdf(report_date, branch_reports, overall_grand_total)
            recipient_emails = [r.email for r in recipients]
            filename = f"PNP_Daily_Report_{report_date.strftime('%d_%m_%Y')}.pdf"

            await email_service.send_daily_report_email(
                to_emails=recipient_emails,
                subject=f"PNP Daily Report — {report_date.strftime('%d/%m/%Y')}",
                html_body=_build_brief_email_html(report_date, branch_reports, overall_grand_total),
                pdf_bytes=pdf_buf.getvalue(),
                pdf_filename=filename,
            )
            await _update_report_status(report_date, "sent")
            logger.info(
                "Daily report sent to %d recipients for %s",
                len(recipient_emails),
                report_date,
            )
        except Exception:
            logger.exception("Error generating daily report for %s", report_date)
            await _update_report_status(report_date, "failed")


# ---------------------------------------------------------------------------
# PDF generation (all branches in a single document)
# ---------------------------------------------------------------------------

def _build_daily_report_pdf(
    report_date: date,
    branch_reports: list[dict],
    overall_grand_total: float,
) -> BytesIO:
    """Build an A4 PDF with per-branch item summaries and an overall total."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
    )
    base = getSampleStyleSheet()

    styles = {
        "company": ParagraphStyle(
            "CompanyHeader", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=13,
            alignment=TA_CENTER, spaceAfter=2 * mm,
        ),
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=11,
            alignment=TA_CENTER, spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=9,
            alignment=TA_CENTER, spaceAfter=3 * mm,
        ),
        "branch_header": ParagraphStyle(
            "BranchHeader", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=10,
            spaceAfter=2 * mm,
            textColor=colors.HexColor("#0a2a38"),
        ),
        "section_label": ParagraphStyle(
            "SectionLabel", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=8,
            spaceAfter=1 * mm,
            textColor=colors.HexColor("#666666"),
        ),
    }

    elements: list = []

    # --- Header ---
    elements.append(Paragraph("PNP MARITIME SERVICES PVT. LTD.", styles["company"]))
    elements.append(Paragraph("Daily Collection Report", styles["title"]))
    elements.append(Paragraph(
        f"Date: {report_date.strftime('%d %B %Y')}",
        styles["subtitle"],
    ))
    elements.append(Spacer(1, 4 * mm))

    # --- Per-branch sections ---
    for idx, report in enumerate(branch_reports):
        branch_name = report.get("branch_name") or "Unknown Branch"
        rows = report.get("rows", [])
        payment_modes = report.get("payment_modes", [])
        grand_total = float(report.get("grand_total", 0))

        # Branch name
        elements.append(Paragraph(f"{idx + 1}. {branch_name}", styles["branch_header"]))

        # Item table
        item_data = [["Item", "Rate", "Qty", "Net Amount"]]
        total_qty = 0
        for row in rows:
            item_data.append([
                str(row["item_name"]),
                _fmt_inr(row["rate"]),
                str(row["quantity"]),
                _fmt_inr(row["net"]),
            ])
            total_qty += row["quantity"]
        item_data.append(["Branch Total", "", str(total_qty), _fmt_inr(grand_total)])

        col_w = [45 * mm, 30 * mm, 20 * mm, 35 * mm]
        item_table = Table(item_data, colWidths=col_w, repeatRows=1)
        item_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a6b8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f8fa")]),
            # Totals row
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0f5")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
        item_table.setStyle(item_style)
        elements.append(item_table)
        elements.append(Spacer(1, 2 * mm))

        # Payment mode breakdown
        active_pms = [pm for pm in payment_modes if float(pm.get("amount", 0)) > 0]
        if active_pms:
            elements.append(Paragraph("Payment Mode Breakdown", styles["section_label"]))
            pm_data = [["Payment Mode", "Amount"]]
            for pm in active_pms:
                pm_data.append([
                    str(pm["payment_mode_name"]),
                    _fmt_inr(pm["amount"]),
                ])
            pm_col_w = [45 * mm, 35 * mm]
            pm_table = Table(pm_data, colWidths=pm_col_w, repeatRows=1)
            pm_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(pm_table)

        elements.append(Spacer(1, 6 * mm))

    # --- Overall Grand Total ---
    elements.append(Spacer(1, 4 * mm))
    total_data = [["Overall Grand Total", _fmt_inr(overall_grand_total)]]
    total_table = Table(total_data, colWidths=[50 * mm, 40 * mm])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a2a38")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(total_table)

    doc.build(elements)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Brief HTML email body (accompanies the PDF attachment)
# ---------------------------------------------------------------------------

def _build_brief_email_html(
    report_date: date,
    branch_reports: list[dict],
    overall_grand_total: float,
) -> str:
    """Short HTML email body — just a summary. Full details are in the PDF."""
    branch_lines = ""
    for report in branch_reports:
        name = report.get("branch_name") or "Unknown"
        total = float(report.get("grand_total", 0))
        branch_lines += (
            f'<tr>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2e8f0;">{name}</td>'
            f'<td style="padding:6px 12px;border-bottom:1px solid #e2e8f0;text-align:right;">&#8377;{_fmt_inr(total)}</td>'
            f'</tr>'
        )

    return f"""
    <div style="max-width:640px;margin:0 auto;font-family:Arial,sans-serif;">
        <div style="background:linear-gradient(135deg,#0a2a38,#1a6b8a);color:white;padding:24px;text-align:center;">
            <h1 style="margin:0;font-size:22px;">PNP Daily Report</h1>
            <p style="margin:8px 0 0;opacity:0.9;font-size:14px;">{report_date.strftime('%d %B %Y')}</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p style="margin:0 0 16px;color:#555;font-size:14px;">
                Please find attached the detailed item-wise daily collection report for
                <strong>{report_date.strftime('%d/%m/%Y')}</strong>.
            </p>
            <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
                <thead>
                    <tr style="background:#f0f9ff;">
                        <th style="padding:8px 12px;text-align:left;font-size:13px;color:#0a2a38;border-bottom:2px solid #0284c7;">Branch</th>
                        <th style="padding:8px 12px;text-align:right;font-size:13px;color:#0a2a38;border-bottom:2px solid #0284c7;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {branch_lines}
                </tbody>
            </table>
            <div style="padding:16px;background:linear-gradient(135deg,#0a2a38,#1a6b8a);border-radius:8px;text-align:center;">
                <span style="color:rgba(255,255,255,0.8);font-size:13px;">Overall Grand Total</span><br/>
                <span style="color:white;font-size:24px;font-weight:bold;">&#8377;{_fmt_inr(overall_grand_total)}</span>
            </div>
            <p style="margin:16px 0 0;color:#999;font-size:12px;">
                See attached PDF for the full item-wise breakdown by branch with payment mode details.
            </p>
        </div>
        <div style="padding:16px;background:#f8fafc;text-align:center;color:#999;font-size:12px;">
            PNP Maritime Services Pvt. Ltd.
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_inr(amount) -> str:
    """Format number as Indian currency: 1,23,456.00"""
    num = float(amount)
    if num < 0:
        return f"-{_fmt_inr(-num)}"
    s = f"{num:,.2f}"
    # Convert 1,234,567.89 to 12,34,567.89 (Indian grouping)
    parts = s.split(".")
    integer_part = parts[0].replace(",", "")
    if len(integer_part) <= 3:
        return s
    last3 = integer_part[-3:]
    rest = integer_part[:-3]
    # Group remaining digits in pairs from right
    groups = []
    while rest:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(groups) + "," + last3 + "." + parts[1]
