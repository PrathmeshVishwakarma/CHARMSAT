import React from 'react';
import { Play, Sparkles, RefreshCw, Cpu, Layers } from 'lucide-react';
import { ScreenId } from './Sidebar';

interface NavbarProps {
  currentScreen: ScreenId;
  onRunDemo: () => void;
  onReSolve: () => void;
  isSolving: boolean;
  isDemoActive: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentScreen,
  onRunDemo,
  onReSolve,
  isSolving,
  isDemoActive
}) => {
  const screenTitles: Record<ScreenId, { title: string; subtitle: string }> = {
    mapping: { title: 'UPLOAD & COLUMN AUTO-MAPPING', subtitle: 'Fuzzy Header Sniffing & Synonyms' },
    rules: { title: 'RULE CONFIGURATION & COMPILATION', subtitle: 'CP-SAT Constraint DSL & Parameters' },
    dashboard: { title: 'DELTAV CABINET & CHARM GRID', subtitle: 'Physical 4-CIOC x 8-BP x 12-Slot Allocation' },
    checker: { title: 'INDEPENDENT CHECKER AUDIT REPORT', subtitle: 'Zero-Violation Proof & Planted Flaw Test' },
    tqs: { title: 'TECHNICAL QUERIES (TQ) MANAGER', subtitle: 'Data, Capacity & Rule Conflict Explanations' },
    revision: { title: 'REVISION B MINIMUM-MOVE ALLOCATOR', subtitle: 'Diff Summary vs From-Scratch Churn' },
    benchmark: { title: 'ALGORITHM BENCHMARK SUITE', subtitle: 'B0 Greedy vs B1 Grouped vs CHARMSAT' },
    export: { title: 'EXPORT & ENGINEERING WORKBOOK', subtitle: 'Filled openpyxl Template & Audits' },
  };

  const meta = screenTitles[currentScreen];

  return (
    <header className="h-16 bg-[#08130C]/90 backdrop-blur-md border-b border-[#1B3826] px-6 flex items-center justify-between z-10 shrink-0">
      {/* Title & Context */}
      <div>
        <h2 className="text-sm font-display tracking-wider font-bold text-white flex items-center gap-2">
          <span className="text-[#4ADE80]">///</span>
          {meta.title}
        </h2>
        <p className="text-[11px] font-mono text-[#6B8E78] tracking-tight">
          {meta.subtitle}
        </p>
      </div>

      {/* Global Actions */}
      <div className="flex items-center gap-3">
        {/* Re-Solve Button */}
        <button
          onClick={onReSolve}
          disabled={isSolving}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#0F2618] hover:bg-[#163823] border border-[#235332] text-xs font-mono text-[#A7C7B3] transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSolving ? 'animate-spin text-[#4ADE80]' : ''}`} />
          <span>RE-SOLVE</span>
        </button>

        {/* 1-Click Demo Mode Button */}
        <button
          onClick={onRunDemo}
          disabled={isSolving}
          className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[#143B22] hover:bg-[#1A4E2D] border border-[#4ADE80] text-xs font-mono text-[#5CFF7A] font-semibold shadow-neon transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5 text-[#5CFF7A] animate-pulse" />
          <span>DEMO MODE (1,000 SIGNALS)</span>
        </button>

        {/* Status Pill */}
        <div className="flex items-center gap-2 pl-3 border-l border-[#1B3826]">
          <div className="w-2.5 h-2.5 rounded-full bg-[#4ADE80] animate-ping" />
          <span className="text-[10px] font-mono tracking-wider text-[#4ADE80] uppercase">
            ONLINE
          </span>
        </div>
      </div>
    </header>
  );
};
