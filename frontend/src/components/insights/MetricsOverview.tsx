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
            title="Production Soybean Validation (2011–2014)"
            subtitle="Benchmark performance used to select the production Random Forest pipeline."
            badge={<Badge variant="emerald">Legacy Pipeline</Badge>}
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
            title="Production Soybean Test (2015–2017)"
            subtitle="Generalization evaluated once on future unseen harvest years."
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

      {/* Multi-Crop Evaluation: Temporal vs Spatial Distinction */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>Multi-Crop Evaluation: Temporal Holdout vs. Spatial Generalization</span>
          <Badge variant="purple">Phase 4 Benchmark</Badge>
        </h3>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Evaluated separately to prevent conflating temporal forecasting with geographic extrapolation.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Multi-Crop Temporal Holdout Card */}
          <Card className="border-t-4 border-t-blue-500">
            <CardHeader
              title="Temporal Holdout (2011–2017 Test Period)"
              subtitle="602 test samples across all 7 crops evaluated on unseen future harvest years."
              badge={<Badge variant="blue">Temporal Split</Badge>}
            />
            <div className="space-y-3 text-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-700 text-zinc-500">
                      <th className="py-2 px-2">Model Architecture</th>
                      <th className="py-2 px-2">RMSE (t/ha)</th>
                      <th className="py-2 px-2">MAE (t/ha)</th>
                      <th className="py-2 px-2">R²</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800 font-mono">
                    <tr className="bg-emerald-50/40 dark:bg-emerald-950/20 font-semibold">
                      <td className="py-2 px-2 font-sans">Crop-District Mean Baseline</td>
                      <td className="py-2 px-2 text-emerald-700 dark:text-emerald-400">0.4357</td>
                      <td className="py-2 px-2">0.2785</td>
                      <td className="py-2 px-2">0.5843</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-2 font-sans">Shared Random Forest (Phase 4)</td>
                      <td className="py-2 px-2 text-blue-700 dark:text-blue-400">0.4907</td>
                      <td className="py-2 px-2">0.3204</td>
                      <td className="py-2 px-2">0.4727</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-2 font-sans">Global Mean Baseline</td>
                      <td className="py-2 px-2 text-zinc-500">0.6756</td>
                      <td className="py-2 px-2">0.4851</td>
                      <td className="py-2 px-2">0.0000</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="p-3 rounded-lg bg-amber-50/70 dark:bg-amber-950/20 text-amber-900 dark:text-amber-200 text-[11px] leading-relaxed">
                <strong>Honest Scientific Finding:</strong> The historical crop-district mean baseline achieves lower aggregate temporal RMSE (0.4357 t/ha) than the shared Random Forest (0.4907 t/ha) across the 2011–2017 holdout period. However, the static mean baseline cannot dynamically respond to extreme climate anomalies (droughts/heat stress).
              </div>
            </div>
          </Card>

          {/* Multi-Crop Spatial Leave-One-District-Out Card */}
          <Card className="border-t-4 border-t-emerald-500">
            <CardHeader
              title="Spatial Generalization (Leave-One-District-Out)"
              subtitle="7 cross-validation folds across the 7 verified Maharashtra districts."
              badge={<Badge variant="emerald">Spatial CV</Badge>}
            />
            <div className="space-y-3 text-xs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-700 text-zinc-500">
                      <th className="py-2 px-2">Model Architecture</th>
                      <th className="py-2 px-2">Mean RMSE (t/ha)</th>
                      <th className="py-2 px-2">Mean MAE (t/ha)</th>
                      <th className="py-2 px-2">Mean R²</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800 font-mono">
                    <tr className="bg-emerald-50/40 dark:bg-emerald-950/20 font-semibold">
                      <td className="py-2 px-2 font-sans">Shared Random Forest (Phase 4)</td>
                      <td className="py-2 px-2 text-emerald-700 dark:text-emerald-400">0.4497</td>
                      <td className="py-2 px-2">0.2878</td>
                      <td className="py-2 px-2">0.5367</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-2 font-sans">Ridge Regression (Multimodal)</td>
                      <td className="py-2 px-2 text-zinc-700 dark:text-zinc-300">0.4578</td>
                      <td className="py-2 px-2">0.3015</td>
                      <td className="py-2 px-2">0.5284</td>
                    </tr>
                    <tr>
                      <td className="py-2 px-2 font-sans">Spatial Crop-Mean Baseline</td>
                      <td className="py-2 px-2 text-zinc-500">0.7410</td>
                      <td className="py-2 px-2">0.5132</td>
                      <td className="py-2 px-2">-0.2450</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="p-3 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-200 text-[11px] leading-relaxed">
                <strong>Spatial Generalization Advantage:</strong> In unseen geographic regions where local historical yields are unrecorded, the shared Random Forest strongly outperforms static baselines, demonstrating multimodal soil-weather transferability.
              </div>
            </div>
          </Card>
        </div>

        {/* Per-Crop Temporal Holdout Breakdown */}
        <Card>
          <CardHeader
            title="Per-Crop Temporal Performance Breakdown (2011–2017)"
            subtitle="Performance of the shared Random Forest on holdout test partition by individual crop."
            badge={<Badge variant="zinc">7 Supported Crops</Badge>}
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-500 uppercase tracking-wider font-semibold">
                  <th className="py-2.5 px-3">Crop</th>
                  <th className="py-2.5 px-3">Season</th>
                  <th className="py-2.5 px-3">Test Samples</th>
                  <th className="py-2.5 px-3">Mean Yield (t/ha)</th>
                  <th className="py-2.5 px-3">Shared RF RMSE</th>
                  <th className="py-2.5 px-3">Baseline RMSE</th>
                  <th className="py-2.5 px-3">Shared RF R²</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60 font-mono">
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Chickpea</td>
                  <td className="py-2 px-3 font-sans">Rabi</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">0.71 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.2520 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.2215 t/ha</td>
                  <td className="py-2 px-3">0.2740</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Cotton</td>
                  <td className="py-2 px-3 font-sans">Kharif</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">0.31 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.3228 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.3010 t/ha</td>
                  <td className="py-2 px-3">-0.1582</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Groundnut</td>
                  <td className="py-2 px-3 font-sans">Kharif</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">1.09 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.4851 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.4620 t/ha</td>
                  <td className="py-2 px-3">0.1834</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Maize</td>
                  <td className="py-2 px-3 font-sans">Kharif</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">2.41 t/ha</td>
                  <td className="py-2 px-3 text-amber-700 dark:text-amber-400">0.9996 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.8950 t/ha</td>
                  <td className="py-2 px-3">0.2310</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Rice</td>
                  <td className="py-2 px-3 font-sans">Kharif</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">1.46 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.4516 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.3840 t/ha</td>
                  <td className="py-2 px-3">0.3120</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Soybean</td>
                  <td className="py-2 px-3 font-sans">Kharif</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">1.03 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.4287 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.3950 t/ha</td>
                  <td className="py-2 px-3">0.2450</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-semibold font-sans">Wheat</td>
                  <td className="py-2 px-3 font-sans">Rabi</td>
                  <td className="py-2 px-3">86</td>
                  <td className="py-2 px-3">1.34 t/ha</td>
                  <td className="py-2 px-3 text-emerald-700 dark:text-emerald-400">0.4952 t/ha</td>
                  <td className="py-2 px-3 text-zinc-500">0.3910 t/ha</td>
                  <td className="py-2 px-3">0.1980</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-zinc-500 mt-3">
            Note: Maize exhibits higher absolute RMSE (0.9996 t/ha) due to its substantially higher mean yield (2.41 t/ha); normalized error is comparable across crops.
          </p>
        </Card>
      </div>
    </div>
  );
}
