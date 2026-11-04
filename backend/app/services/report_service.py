"""Формирование, согласование и экспорт отчетов (UC-4, UC-5, UC-6)."""
import io
import json
from collections import Counter
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BusinessError, PermissionDeniedError
from app.core.security import sign_document, verify_signature
from app.db.base import utcnow
from app.db.models import AuditReport, User
from app.domain.enums import OPEN_STATUSES, ReportStatus, RiskLevel, RoleName
from app.repository.audit_repository import AuditRepository
from app.repository.report_repository import ReportRepository
from app.repository.risk_repository import RiskRepository
from app.repository.transaction_repository import TransactionRepository
from app.services.notification_service import NotificationService
from app.services.risk_calculation import RiskCalculationService
from app.services.text import clean_text

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
ZONE_COLORS = {"green": "#3E9B4F", "yellow": "#E8C93A",
               "orange": "#E8930C", "red": "#D64545"}
_fonts_ready = False


def _register_fonts() -> None:
    global _fonts_ready
    if not _fonts_ready:
        pdfmetrics.registerFont(TTFont(
            "AuditSans", str(FONT_DIR / "LiberationSans-Regular.ttf")))
        pdfmetrics.registerFont(TTFont(
            "AuditSans-Bold", str(FONT_DIR / "LiberationSans-Bold.ttf")))
        _fonts_ready = True


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.reports = ReportRepository(session)
        self.risks = RiskRepository(session)
        self.audit = AuditRepository(session)
        self.notifier = NotificationService(session)

    async def create(self, *, title: str, period_from: date,
                     period_to: date, user: User) -> AuditReport:
        """Создает отчет по шаблону за период (FR-4.2)."""
        if period_to < period_from:
            raise BusinessError("Дата окончания раньше даты начала")
        risks = await self.risks.for_period(period_from, period_to)
        report = AuditReport(title=clean_text(title) or "Отчет по рискам",
                             period_from=period_from, period_to=period_to,
                             user_id=user.id, status=ReportStatus.DRAFT)
        report.summary = await self._summary(risks, period_from, period_to)
        self.session.add(report)
        await self.session.flush()
        for risk in risks:
            if risk.report_id is None:
                risk.report_id = report.id
        self._log(user, "CREATE", report)
        await self.session.commit()
        return report

    async def _summary(self, risks, period_from, period_to) -> dict:
        txn_count = await TransactionRepository(self.session).count_period(
            period_from, period_to)
        levels = Counter(r.level for r in risks)
        departments = Counter(r.transaction.department.name for r in risks)
        heatmap = RiskCalculationService.build_heatmap(risks, top=10)
        return {
            "transactions": txn_count, "risks": len(risks),
            "critical": levels.get(RiskLevel.CRITICAL, 0),
            "levels": {lvl.value: levels.get(lvl, 0) for lvl in RiskLevel},
            "processed": sum(r.status not in OPEN_STATUSES[:2]
                             for r in risks),
            "total_impact": round(sum(float(r.impact) for r in risks), 2),
            "departments": departments.most_common(),
            "heatmap": heatmap,
        }

    async def submit(self, report_id: int, user: User) -> AuditReport:
        """Отправляет отчет руководителю, статус «На проверке» (FR-4.3)."""
        report = await self.reports.get(report_id)
        if report.status not in (ReportStatus.DRAFT, ReportStatus.RETURNED):
            raise BusinessError(f"Отчет в статусе «{report.status}» "
                                f"нельзя отправить на проверку")
        report.status = ReportStatus.ON_REVIEW
        report.submitted_at = utcnow()
        self._log(user, "SUBMIT", report)
        await self.notifier.notify_role(
            RoleName.CHIEF, f"Отчет «{report.title}» ожидает утверждения",
            subject="AuditXP – отчет на утверждение")
        await self.session.commit()
        return report

    async def approve(self, report_id: int, user: User) -> AuditReport:
        """Утверждает отчет с наложением ЭЦП (FR-6.1)."""
        report = await self._for_review(report_id, user)
        report.status = ReportStatus.APPROVED
        report.approved_by = user.id
        report.approver = user
        report.approved_at = utcnow()
        report.signature = sign_document(self.canonical(report))
        self._log(user, "APPROVE", report)
        await self.notifier.notify(
            report.author, f"Отчет «{report.title}» утвержден",
            subject="AuditXP – отчет утвержден")
        await self.session.commit()
        return report

    async def return_for_rework(self, report_id: int, user: User,
                                comment: str) -> AuditReport:
        """Возвращает отчет с обязательным комментарием (FR-6.2)."""
        comment = clean_text(comment)
        if not comment:
            raise BusinessError("Укажите причину возврата отчета")
        report = await self._for_review(report_id, user)
        report.status = ReportStatus.RETURNED
        report.review_comment = comment
        self._log(user, "RETURN", report, comment)
        await self.notifier.notify(
            report.author, f"Отчет «{report.title}» возвращен на доработку. "
                           f"Комментарий руководителя {comment}",
            subject="AuditXP – отчет возвращен")
        await self.session.commit()
        return report

    async def _for_review(self, report_id: int, user: User) -> AuditReport:
        if user.role_name != RoleName.CHIEF:
            raise PermissionDeniedError(
                "Утверждать отчеты может только руководитель службы")
        report = await self.reports.get(report_id)
        if report.status != ReportStatus.ON_REVIEW:
            raise BusinessError("Отчет не находится на проверке")
        return report

    async def verify(self, report_id: int) -> bool:
        report = await self.reports.get(report_id)
        return bool(report.signature) and verify_signature(
            self.canonical(report), report.signature)

    @staticmethod
    def canonical(report: AuditReport) -> bytes:
        body = {"id": report.id, "title": report.title,
                "period": [str(report.period_from), str(report.period_to)],
                "summary": report.summary, "approved_by": report.approved_by}
        return json.dumps(body, ensure_ascii=False, sort_keys=True,
                          default=str).encode("utf-8")

    def _log(self, user: User, action: str, report: AuditReport,
             details: str | None = None) -> None:
        self.audit.add(user_id=user.id, table_name="audit_reports",
                       action=action, record_id=report.id,
                       details=details or report.title)

    async def export(self, report_id: int, fmt: str,
                     user: User) -> tuple[bytes, str, str]:
        """Экспорт отчета в PDF (FR-5.1) или XLSX (FR-5.2)."""
        report = await self.reports.get(report_id)
        risks = await self.risks.for_period(report.period_from,
                                            report.period_to)
        risks.sort(key=lambda r: (r.materiality, float(r.impact)),
                   reverse=True)
        self._log(user, "EXPORT", report, fmt.upper())
        await self.session.commit()
        name = f"auditxp_report_{report.id}.{fmt}"
        if fmt == "pdf":
            return build_pdf(report, risks), "application/pdf", name
        if fmt == "xlsx":
            return build_xlsx(report, risks), (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"), name
        raise BusinessError("Поддерживаются форматы pdf и xlsx")


def build_pdf(report: AuditReport, risks) -> bytes:
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm,
                            rightMargin=1.5 * cm, topMargin=1.5 * cm,
                            bottomMargin=1.5 * cm, title=report.title)
    base = ParagraphStyle("base", fontName="AuditSans", fontSize=10,
                          leading=13)
    head = ParagraphStyle("head", parent=base, fontName="AuditSans-Bold",
                          fontSize=15, leading=19, spaceAfter=6)
    sub = ParagraphStyle("sub", parent=base, fontName="AuditSans-Bold",
                         fontSize=11, spaceBefore=10, spaceAfter=4)
    s = report.summary or {}
    story = [Paragraph("ООО «Голдберг-Софт» · AuditXP: Риск-менеджмент",
                       base),
             Paragraph(escape(report.title), head),
             Paragraph(f"Период {report.period_from:%d.%m.%Y} – "
                       f"{report.period_to:%d.%m.%Y}. Статус "
                       f"{report.status}. Автор "
                       f"{escape(report.author.full_name)}", base),
             Spacer(1, 8)]
    kpi = [["Транзакций", "Рисков", "Критических", "Обработано",
            "Сумма ущерба, BYN"],
           [str(s.get("transactions", 0)), str(s.get("risks", 0)),
            str(s.get("critical", 0)), str(s.get("processed", 0)),
            money(s.get("total_impact", 0))]]
    story.append(_table(kpi, [3.2 * cm] * 4 + [4.3 * cm]))
    story.append(Paragraph("Тепловая карта рисков", sub))
    heat = s.get("heatmap") or {}
    if heat:
        rows = [["Вероятность / ущерб"] + heat["damage_labels"]]
        styles = []
        for p in range(4, -1, -1):
            r = len(rows)
            rows.append([heat["probability_labels"][p]]
                        + [str(c["count"]) for c in heat["cells"][p]])
            for d, cell in enumerate(heat["cells"][p]):
                styles.append(("BACKGROUND", (d + 1, r), (d + 1, r),
                               colors.HexColor(ZONE_COLORS[cell["zone"]])))
        story.append(_table(rows, [3.6 * cm] + [2.7 * cm] * 5, styles))
    story.append(Paragraph("Реестр рисков (наиболее существенные)", sub))
    reg = [["Код", "Тип риска", "Подразделение", "Ущерб, BYN", "Балл",
            "Статус"]]
    for risk in risks[:40]:
        reg.append([risk.code, Paragraph(escape(risk.risk_type), base),
                    risk.transaction.department.name,
                    money(float(risk.impact)), str(risk.materiality),
                    risk.status])
    story.append(_table(reg, [1.9 * cm, 5 * cm, 3 * cm, 3 * cm, 1.2 * cm,
                              2.9 * cm]))
    story.append(Spacer(1, 12))
    if report.signature:
        story.append(Paragraph(
            f"Утвержден {report.approved_at:%d.%m.%Y %H:%M} UTC, "
            f"{escape(report.approver.full_name)}. ЭЦП "
            f"{report.signature[:32]}", base))
    doc.build(story)
    return buf.getvalue()


def _table(rows, widths, extra=None) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "AuditSans", 9),
        ("FONT", (0, 0), (-1, 0), "AuditSans-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7F2EE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#7A8280")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ] + (extra or [])))
    return table


def build_xlsx(report: AuditReport, risks) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Сводка"
    s = report.summary or {}
    bold = Font(bold=True)
    ws.append(["Отчет", report.title])
    ws.append(["Период", f"{report.period_from:%d.%m.%Y} – "
                         f"{report.period_to:%d.%m.%Y}"])
    ws.append(["Статус", report.status])
    for key, label in (("transactions", "Транзакций"), ("risks", "Рисков"),
                       ("critical", "Критических"),
                       ("processed", "Обработано"),
                       ("total_impact", "Сумма ущерба, BYN")):
        ws.append([label, s.get(key, 0)])
    for row in ws.iter_rows(min_col=1, max_col=1):
        row[0].font = bold
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 40

    reg = wb.create_sheet("Реестр рисков")
    header = ["Код", "Тип риска", "Описание", "Подразделение", "Документ",
              "Дата", "Контрагент", "Сумма, BYN", "Вероятность", "Балл",
              "Уровень", "Статус"]
    reg.append(header)
    for risk in risks:
        t = risk.transaction
        reg.append([risk.code, risk.risk_type, risk.description,
                    t.department.name, t.doc_number,
                    t.transaction_date.strftime("%d.%m.%Y %H:%M"),
                    t.counterparty_info, float(risk.impact),
                    float(risk.probability), risk.materiality, risk.level,
                    risk.status])
    for cell in reg[1]:
        cell.font = bold
    for col, width in zip("ABCDEFGHIJKL",
                          (10, 26, 48, 16, 18, 17, 28, 14, 12, 7, 12, 14),
                          strict=True):
        reg.column_dimensions[col].width = width
    reg.freeze_panes = "A2"

    heat = s.get("heatmap") or {}
    hm = wb.create_sheet("Тепловая карта")
    if heat:
        hm.append(["Вероятность / ущерб"] + heat["damage_labels"])
        for p in range(4, -1, -1):
            hm.append([heat["probability_labels"][p]]
                      + [c["count"] for c in heat["cells"][p]])
            for d, cell in enumerate(heat["cells"][p]):
                target = hm.cell(row=hm.max_row, column=d + 2)
                target.fill = PatternFill(
                    "solid", fgColor=ZONE_COLORS[cell["zone"]][1:])
                target.alignment = Alignment(horizontal="center")
        hm.column_dimensions["A"].width = 20
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
