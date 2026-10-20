"use client";

import React from "react";
import { ModelMetadataResponse } from "@/lib/types";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";


interface MetricsOverviewProps {
  metadata: ModelMetadataResponse | null;
  isLoading: boolean;
}

export function MetricsOverview({ metadata, isLoading }: MetricsOverviewProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-zinc-200 dark:bg-zinc-800 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!metadata) {
    return (
      <Card className="text-center py-8 text-zinc-500">
        <p>Model evaluation metrics currently unavailable from backend.</p>
      </Card>
    );
  }

  const { validation_metrics, test_metrics, splits } = {
    validation_metrics: metadata.validation_metrics,
    test_metrics: metadata.test_metrics,
    splits: {
      train: metadata.training_period,
      val: metadata.validation_period,
      test: metadata.test_period,
    },
  };

  return (
    <div className="space-y-6">
      {/* Partition Splits Horizon */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-blue-600">
          <span className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider block mb-1">
            Training Partition
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              {splits.train[0]} – {splits.train[1]}
            </span>
            <span className="text-xs text-zinc-500">21 harvest years</span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
            145 historical observations across 7 districts used to fit encoders and models.
          </p>
        </Card>

        <Card className="border-l-4 border-l-emerald-600">
          <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block mb-1">
            Validation Partition
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              {splits.val[0]} – {splits.val[1]}
            </span>
            <span className="text-xs text-zinc-500">4 harvest years</span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
            28 observations used strictly for benchmark model selection and PFI evaluation.
          </p>
        </Card>

        <Card className="border-l-4 border-l-purple-600">
          <span className="text-xs font-semibold text-purple-700 dark:text-purple-400 uppercase tracking-wider block mb-1">
            Untouched Test Partition
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
              {splits.test[0]} – {splits.test[1]}
            </span>
            <span className="text-xs text-zinc-500">3 harvest years</span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-2">
            21 observations evaluated exactly once post-selection; never touched during training.
          </p>
        </Card>
      </div>

      {/* Validation vs Test Performance Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Validation Metrics Card */}
        <Card>
          <CardHeader
            title="Model Selection Validation (2011–2014)"
            subtitle="Benchmark performance used to select the winning Random Forest pipeline."
            badge={<Badge variant="emerald">Selected Winner</Badge>}
          />
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Validation RMSE</span>
              <span className="text-2xl font-bold text-emerald-800 dark:text-emerald-400 font-mono">
                {validation_metrics.rmse_t_ha?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">t/ha</span>
            </div>

            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Validation MAE</span>
              <span className="text-2xl font-bold text-zinc-800 dark:text-zinc-200 font-mono">
                {validation_metrics.mae_t_ha?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">t/ha</span>
            </div>

            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Validation R²</span>
              <span className="text-2xl font-bold text-zinc-800 dark:text-zinc-200 font-mono">
                {validation_metrics.r2_score?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">30.3% variance</span>
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 text-xs text-emerald-800 dark:text-emerald-300">
            ✓ Outperformed Mean Baseline (0.5370 t/ha RMSE), Ridge (0.4761 t/ha), and Gradient Boosting (0.4806 t/ha).
          </div>
        </Card>

        {/* Untouched Test Metrics Card */}
        <Card>
          <CardHeader
            title="Untouched Chronological Test (2015–2017)"
            subtitle="Final generalization verification evaluated once on future unseen harvest years."
            badge={<Badge variant="zinc">Held-Out Test</Badge>}
          />
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Test RMSE</span>
              <span className="text-2xl font-bold text-purple-800 dark:text-purple-400 font-mono">
                {test_metrics.rmse_t_ha?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">t/ha</span>
            </div>

            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Test MAE</span>
              <span className="text-2xl font-bold text-zinc-800 dark:text-zinc-200 font-mono">
                {test_metrics.mae_t_ha?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">t/ha</span>
            </div>

            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/60 dark:border-zinc-700/60">
              <span className="text-xs text-zinc-500 block mb-1">Test R²</span>
              <span className="text-2xl font-bold text-zinc-800 dark:text-zinc-200 font-mono">
                {test_metrics.r2_score?.toFixed(4) ?? "N/A"}
              </span>
              <span className="text-[11px] text-zinc-400 block mt-0.5">14.0% variance</span>
            </div>
          </div>
          <div className="mt-4 p-3 rounded-lg bg-zinc-100 dark:bg-zinc-800/60 text-xs text-zinc-600 dark:text-zinc-300">
            Includes the severe 2015 Maharashtra drought year (0.6019 t/ha RMSE) and 2016 recovery (0.2900 t/ha RMSE).
          </div>
        </Card>
      </div>
    </div>
  );
}
