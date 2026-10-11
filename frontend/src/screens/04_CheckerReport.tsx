import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, Bug, CheckCircle, RefreshCw, XCircle } from 'lucide-react';
import { API, AllocResult, Violation } from '../api';

interface CheckerReportProps {
  allocResult: AllocResult | null;
  onRefreshClean: () => void;
  onPlantTampered: (tamperedViolations: Violation[]) => void;
}

export const ScreenCheckerReport: React.FC<CheckerReportProps> = ({
  allocResult,
  onRefreshClean,
  onPlantTampered
}) => {
  const [isTampering, setIsTampering] = useState<boolean>(false);
  const [tamperedType, setTamperedType] = useState<string | null>(null);
  const [tamperedViolations, setTamperedViolations] = useState<Violation[] | null>(null);

  const activeViolations = tamperedViolations !== null 
    ? tamperedViolations 
    : (allocResult?.violations || []);

  const isClean = activeViolations.length === 0;

  const handlePlantViolation = async (plantType: string) => {
    setIsTampering(true);
    setTamperedType(plantType);
    try {
      const res = await API.plantViolation(plantType);
      setTamperedViolations(res.violations);
      onPlantTampered(res.violations);
    } catch (err) {
      console.error(err);
    } finally {
      setIsTampering(false);
    }
  };

  const handleResetToClean = () => {
    setTamperedViolations(null);
    setTamperedType(null);
    onRefreshClean();
  };

  // Rule summary definition
  const ruleAuditList = [
    {
      id: 'RULE-01',
      name: 'A/B Train Segregation',
      desc: 'No shared CIOC between Train A and Train B signals',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-01'),
    },
    {
      id: 'RULE-02',
      name: 'Cable Contiguity & Boundary',
      desc: 'Atomic cable blocks, pair order, baseplate alignment',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-02'),
    },
    {
      id: 'RULE-03',
      name: 'Group Cabinet Cohesion',
      desc: 'All instruments of a functional group mapped to single cabinet',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-03'),
    },
    {
      id: 'RULE-04',
      name: 'Cabinet Spare Capacity Margin',
      desc: 'Max used slots <= floor(384 * (1 - spare%))',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-04'),
    },
    {
      id: 'RULE-05',
      name: 'Isolated CHARMs for DO Subtypes',
      desc: 'SOV / horn / beacon routed to Isolated CHARM & Relay TB',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-05'),
    },
    {
      id: 'RULE-06',
      name: 'Hardware Deterministic Lookup',
      desc: 'AI / AO / DI / DO mapped to certified DeltaV modules',
      viols: activeViolations.filter((v) => v.rule_id === 'RULE-06'),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner & Credibility Pitch */}
      <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-lg flex items-center justify-between">
        <div>
          <h3 className="text-base font-display font-bold text-white tracking-wide flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#4ADE80]" />
            INDEPENDENT VERIFICATION ENGINE AUDIT
          </h3>
          <p className="text-xs font-mono text-[#6B8E78] mt-1">
            Re-derives every rule constraint directly from output allocation. Zero solver code shared. Provable mathematical correctness.
          </p>
        </div>

        {/* Big Status Badge */}
        <div className={`px-6 py-3 rounded-xl border flex items-center gap-3 transition-all ${
          isClean
            ? 'bg-[#091F11] border-[#4ADE80] shadow-neon'
            : 'bg-[#210909] border-[#EF4444] shadow-redGlow animate-pulse'
        }`}>
          {isClean ? (
            <>
              <CheckCircle className="w-7 h-7 text-[#5CFF7A]" />
              <div>
                <div className="text-xl font-mono font-bold text-[#5CFF7A] tracking-wider leading-none">
                  0 VIOLATIONS
                </div>
                <div className="text-[10px] font-mono text-[#4ADE80] tracking-tight mt-0.5">
                  CLEAN AUDIT // VERIFIED
                </div>
              </div>
            </>
          ) : (
            <>
              <XCircle className="w-7 h-7 text-[#EF4444]" />
              <div>
                <div className="text-xl font-mono font-bold text-[#EF4444] tracking-wider leading-none">
                  {activeViolations.length} VIOLATIONS
                </div>
                <div className="text-[10px] font-mono text-[#F87171] tracking-tight mt-0.5">
                  PLANTED FLAW DETECTED
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Credibility Demo: Plant a Violation Bar */}
      <div className="bg-[#0A160F] border border-[#1E3A2B] rounded-xl p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Bug className="w-4 h-4 text-amber-400" />
          <div>
            <span className="text-xs font-mono font-bold text-white">
              CREDIBILITY DEMO: PLANT A VIOLATION
            </span>
            <span className="text-[10px] font-mono text-[#6B8E78] block">
              Injects a deliberate error into the allocation copy to prove the independent checker catches it.
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handlePlantViolation('ab_leak')}
            disabled={isTampering}
            className="px-3 py-1.5 rounded-lg bg-[#14261B] hover:bg-[#1E3B29] border border-[#265337] text-xs font-mono text-[#A7C7B3] hover:text-white transition-all"
          >
            Plant A/B Leak
          </button>
          <button
            onClick={() => handlePlantViolation('split_cable')}
            disabled={isTampering}
            className="px-3 py-1.5 rounded-lg bg-[#14261B] hover:bg-[#1E3B29] border border-[#265337] text-xs font-mono text-[#A7C7B3] hover:text-white transition-all"
          >
            Sever Cable Contiguity
          </button>
          <button
            onClick={() => handlePlantViolation('scatter_group')}
            disabled={isTampering}
            className="px-3 py-1.5 rounded-lg bg-[#14261B] hover:bg-[#1E3B29] border border-[#265337] text-xs font-mono text-[#A7C7B3] hover:text-white transition-all"
          >
            Scatter Group Cohesion
          </button>
          {!isClean && (
            <button
              onClick={handleResetToClean}
              className="px-3.5 py-1.5 rounded-lg bg-[#143B22] border border-[#4ADE80] text-xs font-mono font-bold text-[#5CFF7A] shadow-neon flex items-center gap-1.5 transition-all ml-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>RESET TO CLEAN</span>
            </button>
          )}
        </div>
      </div>

      {/* Per-Rule Audit Table */}
      <div className="bg-[#0B1710] border border-[#1E3A2B] rounded-xl p-5 shadow-lg space-y-4">
        <h4 className="text-xs font-mono font-bold text-white flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#4ADE80]" />
          RULE-BY-RULE VERIFICATION AUDIT MATRIX
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#1A3624] text-[#6B8E78] text-[11px]">
                <th className="py-2.5 px-3">RULE ID</th>
                <th className="py-2.5 px-3">RULE NAME</th>
                <th className="py-2.5 px-3">CONSTRAINT INTENT</th>
                <th className="py-2.5 px-3">VERIFICATION STATUS</th>
                <th className="py-2.5 px-3">VIOLATIONS COUNT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#132A1C]">
              {ruleAuditList.map((r) => {
                const isPass = r.viols.length === 0;
                return (
                  <tr key={r.id} className="hover:bg-[#0D1F14] transition-all">
                    <td className="py-3 px-3 font-bold text-[#4ADE80]">{r.id}</td>
                    <td className="py-3 px-3 font-semibold text-white">{r.name}</td>
                    <td className="py-3 px-3 text-[#7CA089]">{r.desc}</td>
                    <td className="py-3 px-3">
                      {isPass ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-600">
                          <CheckCircle className="w-3 h-3" />
                          PASS (0 VIOLATIONS)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-950 text-red-400 border border-red-600 animate-pulse">
                          <AlertTriangle className="w-3 h-3" />
                          FAIL ({r.viols.length} FLAGGED)
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-bold">
                      <span className={isPass ? 'text-[#4ADE80]' : 'text-[#EF4444]'}>
                        {r.viols.length}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Flagged Offending Violations Detail (When tampered) */}
      {!isClean && (
        <div className="bg-[#1C0909] border border-[#EF4444] rounded-xl p-5 shadow-redGlow space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-mono font-bold text-[#F87171] flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#EF4444]" />
              OFFENDING ALLOCATION ROWS CAUGHT BY INDEPENDENT CHECKER ({activeViolations.length})
            </h4>
            <span className="text-[10px] font-mono text-[#FCA5A5]">
              Planted Flaw: {tamperedType}
            </span>
          </div>

          <div className="overflow-x-auto max-h-60">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#3D1414] text-[#FCA5A5] text-[10px]">
                  <th className="py-1.5 px-2">TAG</th>
                  <th className="py-1.5 px-2">CABLE</th>
                  <th className="py-1.5 px-2">RULE</th>
                  <th className="py-1.5 px-2">LOCATION</th>
                  <th className="py-1.5 px-2">ERROR DIAGNOSTIC</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3D1414]">
                {activeViolations.map((v, i) => (
                  <tr key={i} className="hover:bg-[#2B0E0E]">
                    <td className="py-2 px-2 font-bold text-white">{v.tag || 'Spare'}</td>
                    <td className="py-2 px-2 text-[#FCA5A5]">{v.cable || 'N/A'}</td>
                    <td className="py-2 px-2 text-[#EF4444]">{v.rule_id}</td>
                    <td className="py-2 px-2 text-white">
                      CAB-{(v.cabinet || 0) + 1} CIOC-{(v.cioc || 0) + 1} BP-{(v.baseplate || 0) + 1}
                    </td>
                    <td className="py-2 px-2 text-[#FECACA]">{v.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
