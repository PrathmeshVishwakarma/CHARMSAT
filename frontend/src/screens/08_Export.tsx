import React, { useState } from 'react';
import { Download, FileSpreadsheet, CheckCircle2, ShieldCheck, FileText, ArrowRight } from 'lucide-react';
import { API, AllocResult } from '../api';

interface ExportScreenProps {
  allocResult: AllocResult | null;
}

export const ScreenExport: React.FC<ExportScreenProps> = ({ allocResult }) => {
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportComplete, setExportComplete] = useState<boolean>(false);

  const handleDownload = async () => {
    setIsExporting(true);
    try {
      await API.downloadExcel();
      setExportComplete(true);
      setTimeout(() => setExportComplete(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadCSV = () => {
    if (!allocResult || !allocResult.allocations) return;
    const headers = [
      'Tag',
      'Cable',
      'Pair',
      'IO Type',
      'Subtype',
      'Group',
      'Train',
      'Cabinet',
      'CIOC',
      'Baseplate',
      'Slot',
      'CHARM Model',
      'Terminal Block',
      'Is Spare',
    ];
    const rows = allocResult.allocations.map((a) => [
      a.tag || '',
      a.cable,
      a.pair,
      a.io_type || '',
      a.subtype || '',
      a.group || '',
      a.seg || '',
      a.cabinet_name,
      a.cioc_name,
      a.baseplate_name,
      a.slot + 1,
      a.charm,
      a.terminal_block,
      a.is_spare ? 'YES' : 'NO',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'CHARMSAT_Allocation_Export.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleDownloadTQReport = () => {
    if (!allocResult) return;
    const jsonStr = JSON.stringify(allocResult.tqs, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'CHARMSAT_Technical_Queries_Report.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const totalSlots = allocResult?.allocations.length || 0;
  const activeSigs = allocResult?.allocations.filter((s) => !s.is_spare).length || 0;
  const spareSigs = totalSlots - activeSigs;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-lg flex items-center justify-between">
        <div>
          <h3 className="text-base font-display font-bold text-white tracking-wide flex items-center gap-2">
            <Download className="w-5 h-5 text-[#4ADE80]" />
            DELTAV ENGINEERING WORKBOOK & AUDIT EXPORT
          </h3>
          <p className="text-xs font-mono text-[#6B8E78] mt-1">
            Outputs fully formatted Emerson DeltaV allocation workbook via openpyxl. Preserves multi-sheet template layouts, audits, and revision history.
          </p>
        </div>

        {/* Primary Download Button */}
        <button
          onClick={handleDownload}
          disabled={isExporting || !allocResult}
          className="px-6 py-3 rounded-lg bg-[#143B22] hover:bg-[#1C5230] border border-[#4ADE80] text-xs font-mono font-bold text-[#5CFF7A] shadow-neon flex items-center gap-2.5 transition-all disabled:opacity-40"
        >
          {exportComplete ? (
            <>
              <CheckCircle2 className="w-4 h-4 text-[#5CFF7A]" />
              <span>DOWNLOAD COMPLETED!</span>
            </>
          ) : (
            <>
              <Download className={`w-4 h-4 ${isExporting ? 'animate-bounce' : ''}`} />
              <span>DOWNLOAD FILLED EXCEL (.XLSX)</span>
            </>
          )}
        </button>
      </div>

      {/* Package Contents Breakdown Cards */}
      <div className="grid grid-cols-3 gap-6">
        {/* Card 1: Excel Workbook */}
        <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-[#0F2618] border border-[#4ADE80] flex items-center justify-center shadow-neon">
              <FileSpreadsheet className="w-5 h-5 text-[#4ADE80]" />
            </div>
            <h4 className="text-sm font-mono font-bold text-white">
              EMERSON DELTAV ALLOCATION WORKBOOK
            </h4>
            <p className="text-xs font-mono text-[#6B8E78]">
              Includes 5 pre-styled worksheets: Summary KPIs, IO Allocation Matrix, Independent Checker Audit, TQ Log, and Revision B Diff.
            </p>
          </div>
          <div className="pt-3 border-t border-[#183622] flex justify-between items-center text-xs font-mono text-[#A7C7B3]">
            <span>Format: .xlsx (openpyxl)</span>
            <button
              onClick={handleDownload}
              className="text-[#4ADE80] font-bold hover:underline flex items-center gap-1"
            >
              Export <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Card 2: Plain CSV Allocation Table */}
        <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-[#0F2618] border border-[#38BDF8] flex items-center justify-center">
              <FileText className="w-5 h-5 text-[#38BDF8]" />
            </div>
            <h4 className="text-sm font-mono font-bold text-white">
              RAW IO ALLOCATION CSV
            </h4>
            <p className="text-xs font-mono text-[#6B8E78]">
              Clean machine-readable CSV for import into DCS configuration tools, CAD loop generators, or relational databases.
            </p>
          </div>
          <div className="pt-3 border-t border-[#183622] flex justify-between items-center text-xs font-mono text-[#A7C7B3]">
            <span>Format: .csv (UTF-8)</span>
            <button
              onClick={handleDownloadCSV}
              className="text-[#38BDF8] font-bold hover:underline flex items-center gap-1"
            >
              Export <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Card 3: Technical Queries (TQ) Audit Log */}
        <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="w-10 h-10 rounded-lg bg-[#0F2618] border border-amber-400 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-amber-400" />
            </div>
            <h4 className="text-sm font-mono font-bold text-white">
              TECHNICAL QUERY AUDIT LOG (JSON)
            </h4>
            <p className="text-xs font-mono text-[#6B8E78]">
              Machine-parsable JSON artifact containing all isolated Minimal Unsatisfiable Subsets (MUS) and customer clarifications.
            </p>
          </div>
          <div className="pt-3 border-t border-[#183622] flex justify-between items-center text-xs font-mono text-[#A7C7B3]">
            <span>Format: .json</span>
            <button
              onClick={handleDownloadTQReport}
              className="text-amber-400 font-bold hover:underline flex items-center gap-1"
            >
              Export <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Export Metadata Summary */}
      <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-lg space-y-3">
        <h4 className="text-xs font-mono font-bold text-white">EXPORT MANIFEST DETAILS</h4>
        <div className="grid grid-cols-4 gap-4 text-xs font-mono py-2">
          <div>
            <div className="text-[10px] text-[#6B8E78]">ACTIVE FIELD SIGNALS</div>
            <div className="text-lg font-bold text-white mt-0.5">{activeSigs.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#6B8E78]">RESERVED SPARE PAIRS</div>
            <div className="text-lg font-bold text-[#A7C7B3] mt-0.5">{spareSigs}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#6B8E78]">TOTAL PHYSICAL SLOTS</div>
            <div className="text-lg font-bold text-[#38BDF8] mt-0.5">{totalSlots.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-[10px] text-[#6B8E78]">VERIFICATION AUDIT</div>
            <div className="text-lg font-bold text-[#4ADE80] mt-0.5">
              {allocResult?.violations.length === 0 ? '0 VIOLATIONS' : 'FLAGGED'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
