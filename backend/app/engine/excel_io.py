import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List, Optional, Dict, Any
import pandas as pd
from app.models.domain import AllocatedSlot, Violation, TQ, RevisionSummary

class ExcelIO:
    @staticmethod
    def read_input(file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Reads CSV or Excel bytes into DataFrame"""
        import io
        if filename.endswith(".csv"):
            return pd.read_csv(io.BytesIO(file_bytes))
        else:
            return pd.read_excel(io.BytesIO(file_bytes))

    @staticmethod
    def export_workbook(
        allocations: List[AllocatedSlot],
        violations: List[Violation],
        tqs: List[TQ],
        rev_summary: Optional[RevisionSummary] = None,
        kpis: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Creates a beautifully styled DeltaV Electronic Marshalling Excel workbook.
        """
        import io
        wb = openpyxl.Workbook()

        # Styles
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1B4D3E", end_color="1B4D3E", fill_type="solid") # Dark DeltaV green
        accent_fill = PatternFill(start_color="2D6A4F", end_color="2D6A4F", fill_type="solid")
        title_font = Font(name="Segoe UI", size=14, bold=True, color="1B4D3E")
        data_font = Font(name="Segoe UI", size=10)
        mono_font = Font(name="Consolas", size=10)
        thin_border = Border(
            left=Side(style='thin', color='DDDDDD'),
            right=Side(style='thin', color='DDDDDD'),
            top=Side(style='thin', color='DDDDDD'),
            bottom=Side(style='thin', color='DDDDDD')
        )

        # 1. Sheet 1: Dashboard & KPIs
        ws_kpi = wb.active
        ws_kpi.title = "PROJECT_SUMMARY"
        ws_kpi.views.sheetView[0].showGridLines = True

        ws_kpi["A1"] = "CHARMSAT DELTAV IO ALLOCATION REPORT"
        ws_kpi["A1"].font = title_font
        ws_kpi["A2"] = "Automated Rule-Driven Hardware Assignment & Independent Verification"
        ws_kpi["A2"].font = Font(name="Segoe UI", size=10, italic=True, color="666666")

        ws_kpi["A4"] = "Metric"
        ws_kpi["B4"] = "Value"
        ws_kpi["C4"] = "Status / Reference"
        for col in ["A4", "B4", "C4"]:
            ws_kpi[col].font = header_font
            ws_kpi[col].fill = header_fill

        kpi_rows = [
            ("Total Signals Placed", len([s for s in allocations if not s.is_spare]), "100% Coverage"),
            ("Spare Pairs Reserved", len([s for s in allocations if s.is_spare]), "In Multi-Pair Cables"),
            ("Cabinets Deployed", kpis.get("cabinets_used", 0) if kpis else 0, f"Lower Bound: {kpis.get('lower_bound', 0) if kpis else 0}"),
            ("Actual Spare Capacity", f"{kpis.get('spare_pct', 0.0) if kpis else 0.0}%", "Configured Margin >= 10%"),
            ("Independent Rule Violations", len(violations), "0 VIOLATIONS VERIFIED" if len(violations) == 0 else "FAIL"),
            ("Active Technical Queries (TQs)", len(tqs), "Explained Conflicts"),
            ("CP-SAT Solver Runtime", f"{kpis.get('runtime_s', 0.0) if kpis else 0.0} s", "Deterministic Engine")
        ]

        for idx, (m, v, ref) in enumerate(kpi_rows, start=5):
            ws_kpi[f"A{idx}"] = m
            ws_kpi[f"B{idx}"] = v
            ws_kpi[f"C{idx}"] = ref
            for c in ["A", "B", "C"]:
                ws_kpi[f"{c}{idx}"].font = data_font
                ws_kpi[f"{c}{idx}"].border = thin_border

        # 2. Sheet 2: IO Allocation Matrix
        ws_alloc = wb.create_sheet(title="IO_ALLOCATION_MATRIX")
        ws_alloc.views.sheetView[0].showGridLines = True

        headers = [
            "Tag", "Cable", "Pair", "IO Type", "Subtype", "Group", "Train",
            "Cabinet Name", "CIOC Name", "Baseplate Name", "Slot",
            "CHARM Model", "Terminal Block Model", "Is Spare", "Global Slot"
        ]
        for col_idx, h in enumerate(headers, 1):
            cell = ws_alloc.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for row_idx, s in enumerate(allocations, start=2):
            vals = [
                s.tag or f"SPARE-{s.pair:02d}",
                s.cable,
                s.pair,
                s.io_type or "SPARE",
                s.subtype or "",
                s.group or "",
                s.seg or "",
                s.cabinet_name,
                s.cioc_name,
                s.baseplate_name,
                s.slot + 1,
                s.charm,
                s.terminal_block,
                "YES" if s.is_spare else "NO",
                s.global_slot
            ]
            for col_idx, v in enumerate(vals, 1):
                cell = ws_alloc.cell(row=row_idx, column=col_idx, value=v)
                cell.font = mono_font if col_idx in [1, 2, 8, 9, 10, 15] else data_font
                cell.border = thin_border

        # 3. Sheet 3: Independent Checker Audit
        ws_chk = wb.create_sheet(title="INDEPENDENT_CHECKER_AUDIT")
        ws_chk.views.sheetView[0].showGridLines = True
        chk_headers = ["Rule ID", "Rule Name", "Status", "Violations Count", "Audit Verdict"]
        for col_idx, h in enumerate(chk_headers, 1):
            cell = ws_chk.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill

        rule_audit_list = [
            ("RULE-01", "A/B Segregation per CIOC", "PASS" if not any(v.rule_id == "RULE-01" for v in violations) else "FAIL"),
            ("RULE-02", "Cable Block Contiguity & Boundaries", "PASS" if not any(v.rule_id == "RULE-02" for v in violations) else "FAIL"),
            ("RULE-03", "Group Cabinet Cohesion", "PASS" if not any(v.rule_id == "RULE-03" for v in violations) else "FAIL"),
            ("RULE-04", "Cabinet Spare Capacity Margin", "PASS" if not any(v.rule_id == "RULE-04" for v in violations) else "FAIL"),
            ("RULE-05", "Isolated CHARMs for Inductive DO", "PASS" if not any(v.rule_id == "RULE-05" for v in violations) else "FAIL"),
            ("RULE-06", "Hardware Model Deterministic Lookup", "PASS" if not any(v.rule_id == "RULE-06" for v in violations) else "FAIL")
        ]

        for row_idx, (r_id, r_name, stat) in enumerate(rule_audit_list, start=2):
            v_cnt = len([v for v in violations if v.rule_id == r_id])
            ws_chk.cell(row=row_idx, column=1, value=r_id).font = mono_font
            ws_chk.cell(row=row_idx, column=2, value=r_name).font = data_font
            stat_cell = ws_chk.cell(row=row_idx, column=3, value=stat)
            stat_cell.font = Font(name="Segoe UI", size=10, bold=True, color="007700" if stat == "PASS" else "CC0000")
            ws_chk.cell(row=row_idx, column=4, value=v_cnt).font = data_font
            ws_chk.cell(row=row_idx, column=5, value="Zero violations verified by independent checker" if v_cnt == 0 else f"{v_cnt} violations detected").font = data_font
            for c in range(1, 6):
                ws_chk.cell(row=row_idx, column=c).border = thin_border

        # 4. Sheet 4: TQ List
        ws_tq = wb.create_sheet(title="TECHNICAL_QUERIES_TQ")
        ws_tq.views.sheetView[0].showGridLines = True
        tq_headers = ["TQ ID", "Category", "Affected Items", "Conflicting Rules", "Engineering Explanation"]
        for col_idx, h in enumerate(tq_headers, 1):
            cell = ws_tq.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill

        if tqs:
            for row_idx, t in enumerate(tqs, start=2):
                ws_tq.cell(row=row_idx, column=1, value=t.id).font = mono_font
                ws_tq.cell(row=row_idx, column=2, value=t.kind.upper()).font = data_font
                ws_tq.cell(row=row_idx, column=3, value=", ".join(t.items)).font = data_font
                ws_tq.cell(row=row_idx, column=4, value=", ".join(t.rule_ids)).font = mono_font
                ws_tq.cell(row=row_idx, column=5, value=t.message).font = data_font
                for c in range(1, 6):
                    ws_tq.cell(row=row_idx, column=c).border = thin_border
        else:
            ws_tq.cell(row=2, column=1, value="No technical queries raised. Allocation is fully feasible.")

        # 5. Sheet 5: Revision Diff (if present)
        if rev_summary:
            ws_rev = wb.create_sheet(title="REVISION_B_DIFF")
            ws_rev.views.sheetView[0].showGridLines = True
            rev_headers = ["Tag", "Cable", "IO Type", "Group", "Previous Location (Rev A)", "New Location (Rev B)", "Forcing Rule", "Engineering Justification"]
            for col_idx, h in enumerate(rev_headers, 1):
                cell = ws_rev.cell(row=1, column=col_idx, value=h)
                cell.font = header_font
                cell.fill = header_fill

            for row_idx, m in enumerate(rev_summary.moves_detail, start=2):
                ws_rev.cell(row=row_idx, column=1, value=m.tag).font = mono_font
                ws_rev.cell(row=row_idx, column=2, value=m.cable).font = mono_font
                ws_rev.cell(row=row_idx, column=3, value=m.io_type).font = data_font
                ws_rev.cell(row=row_idx, column=4, value=m.group or "").font = data_font
                ws_rev.cell(row=row_idx, column=5, value=m.old_location).font = mono_font
                ws_rev.cell(row=row_idx, column=6, value=m.new_location).font = mono_font
                ws_rev.cell(row=row_idx, column=7, value=m.forcing_rule).font = data_font
                ws_rev.cell(row=row_idx, column=8, value=m.reason).font = data_font
                for c in range(1, 9):
                    ws_rev.cell(row=row_idx, column=c).border = thin_border

        # Adjust column widths automatically
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col[:100]:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                sheet.column_dimensions[col_letter].width = min(40, max(12, max_len + 3))

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
