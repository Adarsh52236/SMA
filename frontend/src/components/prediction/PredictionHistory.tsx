"use client";

import React from "react";
import { HistoryItem } from "@/lib/types";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { History, Trash2, ArrowUpRight, ShieldCheck } from "lucide-react";

interface PredictionHistoryProps {
  onSelect: (item: HistoryItem) => void;
  currentHistory: HistoryItem[];
  onClearHistory: () => void;
  onDeleteItem: (id: string) => void;
}

export function PredictionHistory({
  onSelect,
  currentHistory,
  onClearHistory,
  onDeleteItem,
}: PredictionHistoryProps) {
  if (currentHistory.length === 0) {
    return null;
  }

  return (
    <Card className="mt-8">
      <CardHeader
        title="Session Prediction History"
        subtitle="Recent predictions executed during this browser session."
        badge={<History className="w-4 h-4 text-emerald-600" />}
        action={
          <button
            onClick={onClearHistory}
            className="text-xs text-zinc-500 hover:text-rose-600 dark:hover:text-rose-400 flex items-center gap-1 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
          </button>
        }
      />

      <div className="space-y-2.5">
        {currentHistory.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between p-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 hover:bg-zinc-100/70 dark:hover:bg-zinc-800/60 transition-colors group"
          >
            <button
              onClick={() => onSelect(item)}
              className="flex-1 text-left flex items-center justify-between gap-4 cursor-pointer"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">
                    {item.request.district} ({item.request.year})
                  </span>
                  <Badge variant="emerald" size="sm">
                    {item.response.predicted_yield_t_ha.toFixed(2)} t/ha
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  <span>{item.request.crop} • Kharif</span>
                  <span>•</span>
                  <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
              </div>
              <div className="text-zinc-400 group-hover:text-emerald-600 transition-colors mr-2">
                <ArrowUpRight className="w-4 h-4" />
              </div>
            </button>

            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteItem(item.id);
              }}
              className="p-1.5 text-zinc-400 hover:text-rose-600 rounded transition-colors"
              title="Remove entry"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800 flex items-center gap-1.5 text-[11px] text-zinc-400">
        <ShieldCheck className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
        <span>Stored strictly in sessionStorage. Clears automatically when tab closes.</span>
      </div>
    </Card>
  );
}
