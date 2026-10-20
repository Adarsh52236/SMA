"use client";

import React from "react";
import { GlobalFeatureImportanceItem } from "@/lib/types";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { BarChart3, Info } from "lucide-react";

interface FeatureImportanceChartProps {
  items: GlobalFeatureImportanceItem[];
}

export function FeatureImportanceChart({ items }: FeatureImportanceChartProps) {
  if (!items || items.length === 0) {
    return (
      <Card className="text-center py-8 text-zinc-500">
        <p>Feature importance data currently unavailable.</p>
      </Card>
    );
  }

  // Get max importance to compute normalized bar widths
  const maxMean = Math.max(...items.map((i) => i.importance_mean_rmse), 0.001);

  const getCategory = (feature: string): { label: string; color: string } => {
    if (
      feature.includes("rain") ||
      feature.includes("temp") ||
      feature.includes("humidity") ||
      feature.includes("dry_days") ||
      feature.includes("heat") ||
      feature.includes("radiation")
    ) {
      return { label: "Weather", color: "bg-blue-600 dark:bg-blue-500" };
    }
    if (feature.includes("district")) {
      return { label: "Location", color: "bg-purple-600 dark:bg-purple-500" };
    }
    return { label: "Soil", color: "bg-amber-600 dark:bg-amber-500" };
  };

  return (
    <Card>
      <CardHeader
        title="Permutation Feature Importance (PFI)"
        subtitle="Evaluated across 20 shuffle repeats on held-out validation data (2011–2014)."
        badge={<BarChart3 className="w-4 h-4 text-emerald-600" />}
      />

      <div className="space-y-4">
        {items.map((item, index) => {
          const category = getCategory(item.feature);
          const barWidthPercent = Math.max(
            4,
            Math.min(100, (item.importance_mean_rmse / maxMean) * 100)
          );

          return (
            <div key={item.feature} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-zinc-400 w-5 text-right">{index + 1}.</span>
                  <span className="font-medium text-zinc-800 dark:text-zinc-200">
                    {item.feature.replace(/_/g, " ")}
                  </span>
                  <Badge variant="zinc" size="sm">
                    {category.label}
                  </Badge>
                </div>
                <div className="font-mono text-zinc-600 dark:text-zinc-400">
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                    +{item.importance_mean_rmse.toFixed(4)}
                  </span>{" "}
                  <span className="text-[11px] text-zinc-400">
                    ± {item.importance_std_rmse.toFixed(4)} t/ha
                  </span>
                </div>
              </div>

              {/* Bar with relative width */}
              <div className="w-full h-3 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden relative">
                <div
                  className={`h-full rounded-full ${category.color} transition-all duration-700 ease-out`}
                  style={{ width: `${barWidthPercent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Scientific Transparency Callout */}
      <div className="mt-6 p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/40 border border-zinc-200/80 dark:border-zinc-700/80 text-xs text-zinc-600 dark:text-zinc-300 space-y-2">
        <div className="flex items-center gap-2 font-semibold text-zinc-900 dark:text-zinc-100">
          <Info className="w-4 h-4 text-emerald-600" />
          <span>Scientific Governance: Association vs. Causality</span>
        </div>
        <p className="leading-relaxed">
          1. <strong>Moisture Dominance:</strong> Under rainfed Kharif conditions, relative humidity, consecutive dry days, and cumulative rainfall account for the majority of year-to-year yield variance.
        </p>
        <p className="leading-relaxed">
          2. <strong>Static Soil Baseline:</strong> Topsoil properties (pH, organic carbon, clay) provide a static baseline for regional yield potential, while seasonal weather drives annual yield volatility.
        </p>
        <p className="leading-relaxed">
          3. <strong>Not an Agronomic Prescription:</strong> High permutation importance indicates predictive reliance in the model, not that artificially increasing rainfall or modifying a single property will linearly increase crop yield.
        </p>
      </div>
    </Card>
  );
}
