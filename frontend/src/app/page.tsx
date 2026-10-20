"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ModelMetadataResponse, ApiStatus } from "@/lib/types";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import {
  Sprout,
  Calculator,
  LineChart,
  BookOpen,
  MapPin,
  Clock,
  ShieldCheck,
  TrendingUp,
  Activity,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function OverviewPage() {
  const [metadata, setMetadata] = useState<ModelMetadataResponse | null>(null);
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    isChecking: true,
    backendReachable: false,
    modelReady: false,
    lastChecked: null,
  });

  useEffect(() => {
    async function loadData() {
      try {
        const readyRes = await api.checkReadiness();
        setApiStatus({
          isChecking: false,
          backendReachable: true,
          modelReady: readyRes.status === "ready",
          modelName: readyRes.model_name,
          lastChecked: new Date(),
        });
      } catch (err: unknown) {
        setApiStatus({
          isChecking: false,
          backendReachable: false,
          modelReady: false,
          lastChecked: new Date(),
          errorMessage: err instanceof Error ? err.message : "Service unreachable",
        });
      }

      try {
        const meta = await api.getModelMetadata();
        setMetadata(meta);
      } catch {
        // Handled via fallback display
      }
    }

    loadData();
  }, []);

  const supportedDistricts = metadata?.supported_districts || [
    "Ahmednagar",
    "Akola",
    "Amravati",
    "Aurangabad",
    "Beed",
    "Bhandara",
    "Buldhana",
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-emerald-900 via-emerald-800 to-zinc-900 text-white p-8 sm:p-12 shadow-xl border border-emerald-700/50">
        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant="emerald" size="md">
              <Sprout className="w-3.5 h-3.5" />
              <span>Maharashtra Kharif Soybean</span>
            </Badge>
            <Badge variant="zinc" size="md">
              <span>FastAPI • Random Forest Regressor</span>
            </Badge>
            {apiStatus.modelReady && (
              <Badge variant="emerald" size="md">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>Backend Ready</span>
              </Badge>
            )}
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight">
            Agricultural Crop Yield Intelligence Platform
          </h1>

          <p className="text-base sm:text-lg text-emerald-100/90 leading-relaxed font-normal">
            Predict rainfed soybean harvest yields in tonnes per hectare (t/ha) across
            Maharashtra using multi-decade meteorological observations and verified SoilGrids 2.0 topsoil profiles.
          </p>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 pt-2">
            <Link href="/predict">
              <Button
                size="lg"
                variant="primary"
                leftIcon={<Calculator className="w-5 h-5" />}
                className="w-full sm:w-auto shadow-lg bg-emerald-600 hover:bg-emerald-500 border-emerald-400"
              >
                Open Yield Studio
              </Button>
            </Link>
            <Link href="/insights">
              <Button
                size="lg"
                variant="outline"
                leftIcon={<LineChart className="w-5 h-5" />}
                className="w-full sm:w-auto bg-emerald-950/40 text-emerald-100 border-emerald-600/60 hover:bg-emerald-900/60"
              >
                Inspect Validation Metrics
              </Button>
            </Link>
          </div>
        </div>

        {/* Ambient watermark icon */}
        <div className="absolute -right-12 -bottom-12 opacity-10 pointer-events-none">
          <Sprout className="w-96 h-96 text-white" />
        </div>
      </section>

      {/* Mandatory Timing Disclosure Card */}
      <section>
        <Card className="bg-amber-50/60 dark:bg-amber-950/30 border-amber-200/80 dark:border-amber-900/60 p-6">
          <div className="flex items-start gap-3.5">
            <Clock className="w-5 h-5 text-amber-700 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1.5">
              <h3 className="text-sm font-bold text-amber-950 dark:text-amber-200 uppercase tracking-wider">
                Prediction Timing & Scientific Context
              </h3>
              <p className="text-xs sm:text-sm text-amber-900/90 dark:text-amber-300 leading-relaxed">
                The deployed machine learning model uses growing-season weather features aggregated across the
                full Kharif monsoon cycle (June 1 through October 31). Consequently, this system generates an{" "}
                <strong>end-of-season yield estimate using observed weather</strong>, not an early-season forecast or
                pre-sowing prediction. Forecast values or arbitrary defaults are never substituted.
              </p>
            </div>
          </div>
        </Card>
      </section>

      {/* Key Metrics & Model Highlights Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Validation RMSE
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 font-mono">
              {metadata?.validation_metrics.rmse_t_ha?.toFixed(4) ?? "0.4483"}
            </span>
            <span className="text-xs text-zinc-500">t/ha</span>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            16.5% lower error than the Mean Yield Baseline (0.5370 t/ha).
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Untouched Test RMSE
            </span>
            <LineChart className="w-4 h-4 text-purple-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 font-mono">
              {metadata?.test_metrics.rmse_t_ha?.toFixed(4) ?? "0.4360"}
            </span>
            <span className="text-xs text-zinc-500">t/ha</span>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            Evaluated once on untouched future harvest years (2015–2017).
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Dataset Provenance
            </span>
            <ShieldCheck className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 font-mono">
              194
            </span>
            <span className="text-xs text-zinc-500">observations</span>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            28 harvest years (1990–2017). 0 synthetic or fabricated records.
          </p>
        </Card>

        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Model Pipeline
            </span>
            <Layers className="w-4 h-4 text-amber-600" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              {metadata?.model_name || "Random Forest"}
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-2">
            StandardScaler + OneHotEncoder + 100 Trees ensemble.
          </p>
        </Card>
      </section>

      {/* Supported Coverage & Top Predictors Dual Section */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Geographic Coverage */}
        <Card>
          <CardHeader
            title="Geographic Coverage (Maharashtra)"
            subtitle="Districts with verified SoilGrids 2.0 pedological depth profiles."
            badge={<MapPin className="w-4 h-4 text-emerald-600" />}
          />
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mb-4 leading-relaxed">
            The dataset strictly covers the following 7 agroecological districts across the Vidarbha and
            Marathwada regions. Spatial holdout testing demonstrated consistent generalization across these contiguous zones.
          </p>
          <div className="flex flex-wrap gap-2 mb-6">
            {supportedDistricts.map((district) => (
              <Badge key={district} variant="emerald" size="md">
                {district}
              </Badge>
            ))}
          </div>
          <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800 text-xs text-zinc-500">
            Unprofiled districts were omitted from the dataset rather than filled with unsupported spatial defaults.
          </div>
        </Card>

        {/* Global Feature Importance Preview */}
        <Card>
          <CardHeader
            title="Top Prediction Drivers (PFI)"
            subtitle="Permutation test showing the most influential features in the validation partition."
            badge={<Activity className="w-4 h-4 text-emerald-600" />}
            action={
              <Link href="/insights" className="text-xs text-emerald-700 dark:text-emerald-400 hover:underline inline-flex items-center gap-1 font-medium">
                View All <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            }
          />
          <div className="space-y-3 mb-4">
            {(metadata?.global_feature_importance?.slice(0, 4) || [
              { feature: "mean_relative_humidity_pct", importance_mean_rmse: 0.1445 },
              { feature: "consecutive_dry_days_max", importance_mean_rmse: 0.019 },
              { feature: "cumulative_rainfall_mm", importance_mean_rmse: 0.0161 },
              { feature: "mean_temp_max_c", importance_mean_rmse: 0.0058 },
            ]).map((item, idx) => (
              <div key={item.feature} className="space-y-1 text-xs">
                <div className="flex justify-between font-mono text-zinc-700 dark:text-zinc-300">
                  <span className="font-sans font-medium">
                    {idx + 1}. {item.feature.replace(/_/g, " ")}
                  </span>
                  <span className="text-zinc-500">+{item.importance_mean_rmse.toFixed(4)} t/ha</span>
                </div>
                <div className="w-full h-2 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-600"
                    style={{
                      width: `${Math.min(100, (item.importance_mean_rmse / 0.1445) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 text-xs text-zinc-500">
            Correlated meteorological factors drive year-to-year yield variations under rainfed conditions.
          </div>
        </Card>
      </section>

      {/* Navigation CTA Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
        <Link href="/predict" className="group">
          <Card className="h-full border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 dark:hover:border-emerald-500 transition-all p-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Calculator className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1 flex items-center justify-between">
              <span>Interactive Yield Studio</span>
              <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:text-emerald-600 transition-colors" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Input custom or illustrative weather and soil measurements to obtain a real-time yield prediction.
            </p>
          </Card>
        </Link>

        <Link href="/insights" className="group">
          <Card className="h-full border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 dark:hover:border-emerald-500 transition-all p-6">
            <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <LineChart className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1 flex items-center justify-between">
              <span>Model Insights & Metrics</span>
              <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:text-purple-600 transition-colors" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Inspect benchmark model comparisons, permutation feature importances, and chronological split boundaries.
            </p>
          </Card>
        </Link>

        <Link href="/methodology" className="group">
          <Card className="h-full border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 dark:hover:border-emerald-500 transition-all p-6">
            <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1 flex items-center justify-between">
              <span>Data & Methodology</span>
              <ArrowRight className="w-4 h-4 text-zinc-400 group-hover:text-blue-600 transition-colors" />
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Read the full scientific documentation on data provenance, temporal validation, and decision support caveats.
            </p>
          </Card>
        </Link>
      </section>
    </div>
  );
}
