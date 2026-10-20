import React from "react";
import Link from "next/link";
import { Card } from "@/components/common/Card";
import {
  BookOpen,
  Sprout,
  Database,
  Layers,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/common/Button";

export default function MethodologyPage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Page Header */}
      <div className="pb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300">
            <BookOpen className="w-5 h-5" />
          </span>
          <span className="text-xs uppercase font-bold tracking-wider text-blue-800 dark:text-blue-400">
            Applied Data Science & Governance
          </span>
        </div>
        <h1 className="text-2xl sm:text-4xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
          Methodology & Scientific Transparency
        </h1>
        <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 mt-2 max-w-2xl leading-relaxed">
          Comprehensive documentation of data sources, chronological validation, model selection,
          and agricultural decision support boundaries.
        </p>
      </div>

      {/* 1. Problem Formulation & Scope */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>1. Problem Formulation & Agricultural Focus</span>
        </h2>
        <Card>
          <div className="space-y-4 text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
            <p>
              Soybean (<em>Glycine max</em>) represents a critical cash and protein crop across central India,
              cultivated predominantly under <strong>rainfed conditions during the Kharif monsoon</strong> (June–October).
              In Maharashtra, the Vidarbha and Marathwada regions experience substantial year-to-year yield volatility
              driven by monsoon timing, mid-season dry spells, and heavy vertisol clay dynamics.
            </p>
            <p>
              <strong>Objective:</strong> To develop an empirical, reproducible machine learning pipeline that models
              historical soybean yield in tonnes per hectare (t/ha) using authentic meteorological and
              topsoil properties without synthetic data fabrication or temporal lookahead leakage.
            </p>
          </div>
        </Card>
      </section>

      {/* 2. Data Sources & Provenance */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>2. Primary Data Sources & Provenance</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div className="w-9 h-9 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 flex items-center justify-center mb-3">
              <Database className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1">
              DES Crop Statistics
            </h3>
            <span className="text-xs text-emerald-700 dark:text-emerald-400 font-semibold block mb-2">
              Ministry of Agriculture, India
            </span>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              District-level historical harvest records (1990–2017). Yield calculated directly as
              production divided by cropped area and converted strictly to t/ha. Post-harvest totals
              are quarantined to prevent target leakage.
            </p>
          </Card>

          <Card>
            <div className="w-9 h-9 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300 flex items-center justify-center mb-3">
              <Sprout className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1">
              NASA POWER Meteorology
            </h3>
            <span className="text-xs text-blue-700 dark:text-blue-400 font-semibold block mb-2">
              Daily Agroclimatology API
            </span>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Daily gridded solar radiation, rainfall, relative humidity, and temperatures aggregated
              across the exact 153-day Kharif window (June 1 – Oct 31). Includes consecutive dry days and heat-stress counts.
            </p>
          </Card>

          <Card>
            <div className="w-9 h-9 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 flex items-center justify-center mb-3">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mb-1">
              ISRIC SoilGrids 2.0
            </h3>
            <span className="text-xs text-amber-700 dark:text-amber-400 font-semibold block mb-2">
              Global Soil Information System
            </span>
            <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
              Depth-weighted averages across 0–5cm, 5–15cm, and 15–30cm horizons for pH, organic carbon,
              texture fractions (clay, sand, silt), bulk density, and cation exchange capacity.
            </p>
          </Card>
        </div>
      </section>

      {/* 3. Anti-Fabrication Governance */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>3. Data Governance & Missing-District Policy</span>
        </h2>
        <Card className="border-l-4 border-l-emerald-600">
          <div className="space-y-3 text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
            <h4 className="font-semibold text-zinc-900 dark:text-zinc-100">
              Zero Synthetic Imputation Policy
            </h4>
            <p>
              In strict accordance with project data governance standards:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-xs">
              <li>
                <strong>No Fake Rows:</strong> Training records contain only verified, aligned observations. Zero rows were synthetically interpolated or imputed.
              </li>
              <li>
                <strong>Unprofiled Districts Excluded:</strong> Districts where live SoilGrids queries timed out were omitted from the modeling dataset rather than filled with district averages, future values, or spatial guesses.
              </li>
              <li>
                <strong>Target Leakage Quarantined:</strong> Post-harvest variables (<code>reported_area_ha</code> and <code>reported_production_tonnes</code>) are excluded from model features by automated test gates.
              </li>
            </ul>
          </div>
        </Card>
      </section>

      {/* 4. Chronological Splitting Strategy */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>4. Chronological Evaluation Strategy</span>
        </h2>
        <Card>
          <div className="space-y-4 text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">
            <p>
              Random row k-fold splitting violates temporal ordering in agricultural time series, causing lookahead
              leakage and overly optimistic validation metrics. We enforce strict temporal boundaries:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
              <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700">
                <span className="text-xs font-semibold text-zinc-500 uppercase block mb-1">
                  Training Period
                </span>
                <span className="text-lg font-bold text-zinc-900 dark:text-zinc-100">
                  1990 – 2010
                </span>
                <span className="text-xs text-zinc-500 block mt-1">145 rows • 7 districts</span>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-400 uppercase block mb-1">
                  Validation Period
                </span>
                <span className="text-lg font-bold text-emerald-900 dark:text-emerald-300">
                  2011 – 2014
                </span>
                <span className="text-xs text-zinc-500 block mt-1">28 rows • Model Selection</span>
              </div>

              <div className="p-3.5 rounded-xl bg-purple-50/60 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800">
                <span className="text-xs font-semibold text-purple-800 dark:text-purple-400 uppercase block mb-1">
                  Untouched Test Period
                </span>
                <span className="text-lg font-bold text-purple-900 dark:text-purple-300">
                  2015 – 2017
                </span>
                <span className="text-xs text-zinc-500 block mt-1">21 rows • Evaluated Once</span>
              </div>
            </div>
            <p className="text-xs text-zinc-500">
              The test partition was locked and remained untouched during all feature engineering and hyperparameter decisions.
            </p>
          </div>
        </Card>
      </section>

      {/* 5. Scientific Decision Support Boundaries */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>5. Operational Caveats & Boundaries</span>
        </h2>
        <Card className="bg-amber-50/30 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60 p-6 space-y-4">
          <div className="flex items-center gap-2 font-bold text-amber-900 dark:text-amber-200">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <span>What This Model CAN and CANNOT Be Used For</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
            <div className="space-y-2">
              <span className="font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block">
                ✓ Intended Agricultural Uses:
              </span>
              <ul className="list-disc pl-4 space-y-1">
                <li>End-of-season regional yield estimation after harvest weather is recorded.</li>
                <li>Retrospective scenario analysis of past drought anomalies (e.g. 2015 vs 2016).</li>
                <li>Regional agricultural intelligence and crop loss risk assessment for Vidarbha/Marathwada.</li>
                <li>Research benchmarking for multi-modal weather/soil integration.</li>
              </ul>
            </div>

            <div className="space-y-2">
              <span className="font-semibold text-rose-700 dark:text-rose-400 uppercase tracking-wider block">
                ✗ Unintended / Invalid Uses:
              </span>
              <ul className="list-disc pl-4 space-y-1">
                <li>Pre-sowing yield forecasts (seasonal monsoon data is required).</li>
                <li>Prescription of fertilizer, pesticide, or irrigation quantities to individual farmers.</li>
                <li>Micro-parcel or field-level precision agriculture (SoilGrids represents regional averages).</li>
                <li>Spatial extrapolation to unverified districts or non-Maharashtra states.</li>
              </ul>
            </div>
          </div>
        </Card>
      </section>

      {/* CTA Footer */}
      <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-2xl bg-zinc-100 dark:bg-zinc-900">
        <div>
          <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
            Ready to explore predictions or model insights?
          </h4>
          <p className="text-xs text-zinc-500 mt-0.5">
            Test custom observations in the Yield Studio or inspect model comparison tables.
          </p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Link href="/predict" className="w-full sm:w-auto">
            <Button variant="primary" className="w-full sm:w-auto">
              Yield Studio
            </Button>
          </Link>
          <Link href="/insights" className="w-full sm:w-auto">
            <Button variant="outline" className="w-full sm:w-auto">
              Model Insights
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
