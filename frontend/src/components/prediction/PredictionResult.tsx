"use client";

import React from "react";
import Link from "next/link";
import { PredictionResponse } from "@/lib/types";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import {
  Sprout,
  Calendar,
  MapPin,
  Clock,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  BarChart3,
  Copy,
  Check,
} from "lucide-react";

interface PredictionResultProps {
  result: PredictionResponse;
  onReset: () => void;
}

export function PredictionResult({
  result,
  onReset,
}: PredictionResultProps) {
  const [copied, setCopied] = React.useState(false);

  const copyRequestId = () => {
    if (result.request_id) {
      navigator.clipboard.writeText(result.request_id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const yieldKgHa = result.predicted_yield_kg_ha ?? Math.round(result.predicted_yield_t_ha * 1000);
  const yieldQuintalHa = (result.predicted_yield_t_ha * 10).toFixed(2);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 1. Main Yield Banner Card */}
      <Card className="border-emerald-200 dark:border-emerald-800/80 bg-gradient-to-br from-white via-emerald-50/20 to-emerald-100/30 dark:from-zinc-900 dark:via-emerald-950/20 dark:to-zinc-900 p-8 shadow-md">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-emerald-100 dark:border-emerald-900/50">
          <div>
            <div className="flex items-center flex-wrap gap-2 mb-2">
              <Badge variant="emerald" size="md">
                <Clock className="w-3.5 h-3.5" />
                <span>End-of-Season Yield Estimate</span>
              </Badge>
              <Badge variant="zinc" size="md">
                Model: {result.model_name} (v{result.model_version})
              </Badge>
              {result.model_strategy && (
                <Badge variant={result.model_strategy.includes("multicrop") ? "purple" : "blue"} size="md">
                  Strategy: {result.model_strategy.replace(/_/g, " ")}
                </Badge>
              )}
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
              Estimated {result.crop} Yield
            </h2>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1 max-w-xl">
              Calculated using observed {result.season} seasonal agroclimatology and
              ISRIC SoilGrids 0–30 cm pedological characteristics for {result.district} district.
            </p>
          </div>

          {/* Primary Yield Metric Badge */}
          <div className="flex flex-col items-start lg:items-end bg-white dark:bg-zinc-950 px-6 py-4 rounded-2xl border border-emerald-200 dark:border-emerald-800 shadow-sm">
            <span className="text-xs uppercase font-semibold tracking-wider text-emerald-800 dark:text-emerald-400">
              Predicted Harvest Yield
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl sm:text-5xl font-black text-emerald-900 dark:text-emerald-300 tracking-tight">
                {result.predicted_yield_t_ha.toFixed(2)}
              </span>
              <span className="text-lg font-semibold text-zinc-500 dark:text-zinc-400">
                t/ha
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400 mt-2">
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                {yieldKgHa.toLocaleString()} kg/ha
              </span>
              <span>•</span>
              <span>≈ {yieldQuintalHa} quintal/ha</span>
            </div>
          </div>
        </div>

        {/* Input Parameters Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 text-sm">
          <div className="flex items-center gap-2.5">
            <MapPin className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="text-xs text-zinc-400 block">District</span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {result.district}, {result.state}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Calendar className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="text-xs text-zinc-400 block">Harvest Season</span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {result.season} {result.year}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Sprout className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="text-xs text-zinc-400 block">Crop Variety Focus</span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {result.crop}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <TrendingUp className="w-4 h-4 text-emerald-600 shrink-0" />
            <div>
              <span className="text-xs text-zinc-400 block">Inference Engine</span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                FastAPI • scikit-learn
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Timing Disclosure & Methodology Context */}
      <Card className="bg-amber-50/40 dark:bg-amber-950/20 border-amber-200/80 dark:border-amber-900/60 p-5">
        <div className="flex items-start gap-3">
          <Clock className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">
              Important Scientific Notice: Prediction vs. Historical Reality
            </h4>
            <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
              {result.timing_description} Historical model estimates are retrospective statistical inferences
              based on agroclimatic and pedological covariates, not guaranteed actual field harvest yields.
              Observed historical yields remain the ground truth for agronomic accounting.
            </p>
          </div>
        </div>
      </Card>

      {/* 3. Global Permutation Feature Importance */}
      {result.global_feature_importance && result.global_feature_importance.length > 0 && (
        <Card>
          <CardHeader
            title="Global Predictor Importance"
            subtitle="Top agroclimatic factors driving model yield variance (held-out permutation test)."
            badge={<BarChart3 className="w-4 h-4 text-emerald-600" />}
            action={
              <Link href="/insights" className="text-xs text-emerald-700 dark:text-emerald-400 hover:underline inline-flex items-center gap-1 font-medium">
                Full Insights <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            }
          />
          <div className="space-y-3">
            {result.global_feature_importance.map((item, idx) => {
              // Normalize relative bar width
              const maxVal = result.global_feature_importance![0].importance_mean_rmse;
              const barWidth = Math.max(8, Math.min(100, (item.importance_mean_rmse / maxVal) * 100));

              return (
                <div key={item.feature} className="space-y-1 text-xs">
                  <div className="flex justify-between font-mono text-zinc-700 dark:text-zinc-300">
                    <span className="font-sans font-medium">
                      {idx + 1}. {item.feature.replace(/_/g, " ")}
                    </span>
                    <span className="text-zinc-500">
                      +{item.importance_mean_rmse.toFixed(4)} t/ha RMSE
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-emerald-600 dark:bg-emerald-500 transition-all duration-500"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-zinc-400 mt-4">
            Note: Global permutation importance reflects retrospective statistical associations.
            It does not establish direct pharmacological or on-farm fertilizer causality.
          </p>
        </Card>
      )}

      {/* 4. Model Limitations & Boundaries */}
      <Card>
        <CardHeader
          title="Model Operational Limitations"
          subtitle="Pre-flight boundaries and data governance constraints."
          badge={<ShieldAlert className="w-4 h-4 text-amber-600" />}
        />
        <ul className="space-y-2 text-xs text-zinc-600 dark:text-zinc-300">
          {result.limitations.map((lim, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
              <span className="leading-relaxed">{lim}</span>
            </li>
          ))}
        </ul>
      </Card>

      {/* 5. Traceability and Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-zinc-100 dark:bg-zinc-900 text-xs text-zinc-500">
        <div className="flex items-center gap-2">
          <span>Request Trace ID:</span>
          <code className="font-mono bg-white dark:bg-zinc-800 px-2 py-0.5 rounded border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200">
            {result.request_id || "N/A"}
          </code>
          {result.request_id && (
            <button
              onClick={copyRequestId}
              className="p-1 hover:text-zinc-800 dark:hover:text-zinc-200 transition-colors"
              title="Copy request ID"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Button variant="secondary" onClick={onReset} className="w-full sm:w-auto">
            New Prediction
          </Button>
          <Link href="/insights">
            <Button variant="outline" className="w-full sm:w-auto">
              Inspect Model Validation
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
