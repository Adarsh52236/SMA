import React from "react";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { Database, ShieldCheck, MapPin, Hash } from "lucide-react";

interface DatasetProvenanceCardProps {
  sha256?: string;
  districts?: string[];
  totalRows?: number;
}

export function DatasetProvenanceCard({
  sha256 = "656a3a8999c8feb73d30aae7b6a7fb72c5112a933107fdbe3338bdc17861bf9a",
  districts = [
    "Ahmednagar",
    "Akola",
    "Amravati",
    "Aurangabad",
    "Beed",
    "Bhandara",
    "Buldhana",
  ],
  totalRows = 194,
}: DatasetProvenanceCardProps) {
  return (
    <Card>
      <CardHeader
        title="Dataset Provenance & Quality Governance"
        subtitle="Zero synthetic observations. Complete verification against primary government & scientific sources."
        badge={<Database className="w-4 h-4 text-emerald-600" />}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
          <span className="text-xs text-zinc-500 block mb-1">Total Verified Observations</span>
          <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
            {totalRows}
          </span>
          <span className="text-[11px] text-zinc-400 block mt-0.5">28 harvest years (1990–2017)</span>
        </div>

        <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
          <span className="text-xs text-zinc-500 block mb-1">Supported Districts</span>
          <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 font-mono">
            {districts.length}
          </span>
          <span className="text-[11px] text-zinc-400 block mt-0.5">With SoilGrids 2.0 depth profiles</span>
        </div>

        <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
          <span className="text-xs text-zinc-500 block mb-1">Target Yield Variable</span>
          <span className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 font-mono">
            yield_t_ha
          </span>
          <span className="text-[11px] text-zinc-400 block mt-0.5">Mean: 1.0502 t/ha [0.14, 2.16]</span>
        </div>
      </div>

      {/* District Whitelist Badges */}
      <div className="space-y-2 mb-5">
        <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-emerald-600" />
          <span>Covered Agroecological Districts:</span>
        </span>
        <div className="flex flex-wrap gap-2">
          {districts.map((d) => (
            <Badge key={d} variant="emerald" size="md">
              {d}
            </Badge>
          ))}
        </div>
      </div>

      {/* Dataset SHA-256 Fingerprint */}
      <div className="p-3.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
          <Hash className="w-3.5 h-3.5 text-zinc-500" />
          <span>Immutable Dataset SHA-256 Fingerprint:</span>
        </div>
        <code className="font-mono text-[11px] text-emerald-800 dark:text-emerald-400 break-all select-all">
          {sha256}
        </code>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
        <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
        <span>
          Unprofiled districts were strictly excluded during Phase 2 preprocessing rather than filled with
          synthetic or interpolated values, preserving 100% genuine data provenance.
        </span>
      </div>
    </Card>
  );
}
