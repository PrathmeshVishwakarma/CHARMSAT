import React from 'react';
import { 
  FileSpreadsheet, 
  Sliders, 
  Grid, 
  ShieldCheck, 
  AlertCircle, 
  GitCompare, 
  BarChart3, 
  Download,
  Cpu,
  Layers,
  Sparkles
} from 'lucide-react';

export type ScreenId = 
  | 'mapping'
  | 'rules'
  | 'dashboard'
  | 'checker'
  | 'tqs'
  | 'revision'
  | 'benchmark'
  | 'export';

interface SidebarProps {
  currentScreen: ScreenId;
  onSelectScreen: (screen: ScreenId) => void;
  violationsCount: number;
  tqCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentScreen,
  onSelectScreen,
  violationsCount,
  tqCount
}) => {
  const menuItems: { id: ScreenId; label: string; icon: React.ReactNode; badge?: string | number; badgeColor?: string }[] = [
    { id: 'mapping', label: '1. Upload & Mapping', icon: <FileSpreadsheet className="w-5 h-5" /> },
    { id: 'rules', label: '2. Rule Panel', icon: <Sliders className="w-5 h-5" /> },
    { id: 'dashboard', label: '3. Allocation Grid', icon: <Grid className="w-5 h-5" /> },
    { 
      id: 'checker', 
      label: '4. Checker Report', 
      icon: <ShieldCheck className="w-5 h-5" />,
      badge: violationsCount === 0 ? '0 VIOL' : `${violationsCount} VIOL`,
      badgeColor: violationsCount === 0 ? 'bg-emerald-950 text-emerald-400 border-emerald-600' : 'bg-red-950 text-red-400 border-red-600'
    },
    { 
      id: 'tqs', 
      label: '5. Technical Queries (TQs)', 
      icon: <AlertCircle className="w-5 h-5" />,
      badge: tqCount > 0 ? `${tqCount}` : undefined,
      badgeColor: 'bg-amber-950 text-amber-400 border-amber-600'
    },
    { id: 'revision', label: '6. Revision Diff (Rev B)', icon: <GitCompare className="w-5 h-5" /> },
    { id: 'benchmark', label: '7. Benchmarks', icon: <BarChart3 className="w-5 h-5" /> },
    { id: 'export', label: '8. Export Workbook', icon: <Download className="w-5 h-5" /> },
  ];

  return (
    <aside className="w-64 bg-[#08120B] border-r border-[#1B3826] flex flex-col justify-between shrink-0 h-screen select-none">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-[#1B3826]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#0F2618] border border-[#4ADE80] flex items-center justify-center shadow-neon">
              <Cpu className="w-6 h-6 text-[#4ADE80]" />
            </div>
            <div>
              <h1 className="font-display tracking-wider text-xl font-bold text-white flex items-center gap-1.5">
                CHARMSAT
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-[#102E1B] text-[#4ADE80] border border-[#1E4D2C]">
                  v1.0
                </span>
              </h1>
              <p className="text-[10px] text-[#6B8E78] font-mono tracking-tight">
                DELTA-V IO ENGINE // VIT PUNE
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1.5">
          <div className="text-[10px] font-mono tracking-wider uppercase text-[#547560] px-3 pt-2 pb-1">
            WORKFLOW SCREENS
          </div>
          {menuItems.map((item) => {
            const isActive = currentScreen === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectScreen(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-[#122A1C] text-white border border-[#4ADE80] shadow-neon font-semibold'
                    : 'text-[#9BB8A5] hover:bg-[#0D1F13] hover:text-white border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={isActive ? 'text-[#4ADE80]' : 'text-[#6B8E78]'}>
                    {item.icon}
                  </span>
                  <span className="tracking-wide">{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${item.badgeColor}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-[#1B3826] bg-[#050C07] space-y-3">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-[#6B8E78]">SOLVER CORE</span>
          <span className="text-[#4ADE80] flex items-center gap-1 font-semibold">
            <span className="w-2 h-2 rounded-full bg-[#4ADE80] animate-pulse"></span>
            OR-TOOLS CP-SAT
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-[#6B8E78]">VERIFIER</span>
          <span className="text-[#38BDF8]">INDEPENDENT</span>
        </div>
        <div className="pt-2 border-t border-[#14291B] text-[10px] font-mono text-[#52705D] flex justify-between">
          <span>TEAM lost_in_the_shine</span>
          <span>APEX 2026</span>
        </div>
      </div>
    </aside>
  );
};
