"use client";

import React, { useState, useEffect } from "react";
import { DatasetProfile } from "@/lib/types";
import { api, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { Badge } from "@/components/common/Badge";
import { Button } from "@/components/common/Button";
import { Alert } from "@/components/common/Alert";
import {
  Database,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Sparkles,
  FileSpreadsheet,
  ShieldAlert,
  Scale,
  RefreshCw,
} from "lucide-react";

export default function DiscoveryStudioPage() {
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Upload inspector states
  const [inspectingFile, setInspectingFile] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"columns" | "combinations" | "quality" | "summary">("columns");

  useEffect(() => {
    let isMounted = true;
    api
      .getDatasetProfile()
      .then((data) => {
        if (isMounted) {
          setProfile(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Failed to fetch discovered dataset schema profile.");
          }
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const reloadProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getDatasetProfile();
      setProfile(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to fetch discovered dataset schema profile.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setInspectingFile(true);
    setUploadError(null);
    try {
      const inspected = await api.inspectDataset(file);
      setProfile(inspected);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setUploadError(err.message);
      } else {
        setUploadError("Failed to parse and profile the uploaded dataset.");
      }
    } finally {
      setInspectingFile(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="emerald" size="md">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 6 Autonomous Intelligence</span>
            </Badge>
            <Badge variant="zinc" size="md">
              Deterministic Schema Inference
            </Badge>
          </div>
          <h1 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
            Dataset Discovery & Schema Intelligence
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl">
            Autonomous inspection engine that derives semantic roles, target variables, categorical
            cardinalities, and data hygiene constraints directly from empirical observations.
          </p>
        </div>

        {/* Upload or Refresh Toolbar */}
        <div className="flex items-center gap-3">
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".csv,.parquet"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              isLoading={inspectingFile}
              leftIcon={<Upload className="w-4 h-4" />}
            >
              Inspect Custom File
            </Button>
          </label>
          <Button
            variant="secondary"
            size="sm"
            onClick={reloadProfile}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Reload Active Profile
          </Button>
        </div>
      </div>

      {uploadError && (
        <Alert variant="error" title="File Inspection Error" onClose={() => setUploadError(null)}>
          {uploadError}
        </Alert>
      )}

      {error && (
        <Alert variant="error" title="Profile Retrieval Failed" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-4">
          <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-zinc-500 font-medium">Profiling dataset and discovering category cross-tabulations...</p>
        </div>
      ) : profile ? (
        <>
          {/* Top Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-5">
              <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-xs">
                <span>Active Dataset</span>
                <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2 text-xl font-bold text-zinc-900 dark:text-zinc-100 truncate">
                {profile.dataset_name}
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {profile.row_count.toLocaleString()} rows × {profile.col_count} columns
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-xs">
                <span>Discovered Target</span>
                <Scale className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2 text-xl font-bold text-emerald-700 dark:text-emerald-400 truncate">
                {profile.selected_target || "None"}
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {profile.target_candidates.length} candidate(s) evaluated
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-xs">
                <span>Quality Score</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2 text-xl font-bold text-zinc-900 dark:text-zinc-100">
                {profile.quality_report.quality_score_pct.toFixed(1)}%
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {profile.quality_report.duplicate_rows} duplicates • {profile.quality_report.constant_columns.length} constant cols
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-xs">
                <span>Discovered Categories</span>
                <Layers className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2 text-xl font-bold text-zinc-900 dark:text-zinc-100">
                {Object.keys(profile.discovered_categories).length} Dimensions
              </div>
              <div className="text-xs text-zinc-500 mt-1">
                {profile.observed_combinations.length} observed cross-combinations
              </div>
            </Card>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2">
            {[
              { id: "columns", label: `Columns & Roles (${profile.col_count})` },
              { id: "combinations", label: `Cross-Tabulations (${profile.observed_combinations.length})` },
              { id: "quality", label: `Hygiene & Leakage Checks (${profile.quality_report.warnings.length})` },
              { id: "summary", label: "Executive Markdown Report" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                  activeTab === tab.id
                    ? "bg-emerald-100 dark:bg-emerald-950/70 text-emerald-900 dark:text-emerald-300 shadow-2xs"
                    : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab 1: Columns and Roles */}
          {activeTab === "columns" && (
            <Card>
              <CardHeader
                title="Discovered Schema & Inferred Column Roles"
                subtitle="Deterministic analysis of data types, null rates, uniqueness, physical units, and leakage risks."
                badge={<Database className="w-4 h-4 text-emerald-600" />}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Column Name</th>
                      <th className="py-3 px-4">Inferred Role</th>
                      <th className="py-3 px-4">Data Type</th>
                      <th className="py-3 px-4">Null %</th>
                      <th className="py-3 px-4">Unique</th>
                      <th className="py-3 px-4">Units</th>
                      <th className="py-3 px-4">Confidence</th>
                      <th className="py-3 px-4">Hygiene Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                    {Object.entries(profile.columns).map(([colName, col]) => (
                      <tr key={colName} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-zinc-900 dark:text-zinc-100">
                          {colName}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              col.inferred_role === "target"
                                ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                                : col.inferred_role === "leakage"
                                ? "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300"
                                : col.inferred_role === "categorical"
                                ? "bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300"
                                : col.inferred_role === "numerical"
                                ? "bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300"
                                : "bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-300"
                            }`}
                          >
                            {col.inferred_role}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-zinc-500">{col.dtype}</td>
                        <td className="py-3 px-4 text-zinc-600 dark:text-zinc-300">{col.null_pct}%</td>
                        <td className="py-3 px-4 text-zinc-600 dark:text-zinc-300">
                          {col.unique_count.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-zinc-500 font-mono">{col.inferred_units || "—"}</td>
                        <td className="py-3 px-4 text-zinc-600 dark:text-zinc-300">
                          {(col.confidence_role * 100).toFixed(0)}%
                        </td>
                        <td className="py-3 px-4">
                          {col.is_leakage_risk ? (
                            <span className="text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1">
                              <ShieldAlert className="w-3.5 h-3.5" /> Leakage Risk
                            </span>
                          ) : col.is_constant ? (
                            <span className="text-amber-600 dark:text-amber-400 font-medium">Constant (Zero Variance)</span>
                          ) : (
                            <span className="text-emerald-600 dark:text-emerald-400">Valid Covariate</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Tab 2: Category Combinations */}
          {activeTab === "combinations" && (
            <Card>
              <CardHeader
                title="Observed Category Combinations & Cross-Tabulations"
                subtitle="Data sufficiency evaluation across crops, districts, and seasons."
                badge={<Layers className="w-4 h-4 text-emerald-600" />}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Feature A</th>
                      <th className="py-3 px-4">Value A</th>
                      <th className="py-3 px-4">Feature B</th>
                      <th className="py-3 px-4">Value B</th>
                      <th className="py-3 px-4">Observation Count</th>
                      <th className="py-3 px-4">Mean Yield</th>
                      <th className="py-3 px-4">Representation Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                    {profile.observed_combinations.slice(0, 50).map((combo, idx) => (
                      <tr key={idx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3 px-4 font-medium text-zinc-500">{combo.feature_a}</td>
                        <td className="py-3 px-4 font-bold text-zinc-900 dark:text-zinc-100">{combo.value_a}</td>
                        <td className="py-3 px-4 font-medium text-zinc-500">{combo.feature_b}</td>
                        <td className="py-3 px-4 font-bold text-zinc-900 dark:text-zinc-100">{combo.value_b}</td>
                        <td className="py-3 px-4 font-mono">{combo.observation_count}</td>
                        <td className="py-3 px-4 font-mono">
                          {combo.mean_target_value != null ? `${combo.mean_target_value.toFixed(2)} t/ha` : "—"}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              combo.representation_status === "well_represented"
                                ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                                : combo.representation_status === "sparse"
                                ? "bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300"
                                : "bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300"
                            }`}
                          >
                            {combo.representation_status.replace(/_/g, " ")}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {profile.observed_combinations.length > 50 && (
                <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500 text-center">
                  Showing top 50 of {profile.observed_combinations.length} observed cross-combinations.
                </div>
              )}
            </Card>
          )}

          {/* Tab 3: Data Quality Report */}
          {activeTab === "quality" && (
            <div className="space-y-6">
              <Card className="p-6">
                <CardHeader
                  title="Data Quality & Hygiene Audit"
                  subtitle="Integrity checks for duplicates, constant zero-variance features, and leakage."
                  badge={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700">
                    <span className="text-xs text-zinc-500 block">Duplicate Rows</span>
                    <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">
                      {profile.quality_report.duplicate_rows}
                    </span>
                    <span className="text-[11px] text-zinc-400">
                      {profile.quality_report.duplicate_rows_pct.toFixed(2)}% of dataset
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700">
                    <span className="text-xs text-zinc-500 block">Constant Columns</span>
                    <span className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mt-1 block">
                      {profile.quality_report.constant_columns.length}
                    </span>
                    <span className="text-[11px] text-zinc-400">
                      {profile.quality_report.constant_columns.join(", ") || "None"}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700">
                    <span className="text-xs text-zinc-500 block">Leakage Risks</span>
                    <span className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1 block">
                      {profile.quality_report.detected_leakage_columns.length}
                    </span>
                    <span className="text-[11px] text-zinc-400">
                      {profile.quality_report.detected_leakage_columns.join(", ") || "None detected"}
                    </span>
                  </div>
                </div>

                {profile.quality_report.warnings.length > 0 && (
                  <div className="mt-6 space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                      Governance Warnings
                    </h4>
                    <div className="space-y-1.5">
                      {profile.quality_report.warnings.map((w, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20 text-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-900 text-xs"
                        >
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Tab 4: Human-Readable Markdown Summary */}
          {activeTab === "summary" && (
            <Card className="p-6">
              <CardHeader
                title="Machine-Generated Discovery Explanation"
                subtitle="Automatically drafted summary of the dataset profile for documentation and auditing."
                badge={<Sparkles className="w-4 h-4 text-emerald-600" />}
              />
              <pre className="mt-4 p-5 rounded-xl bg-zinc-950 text-zinc-100 font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {profile.human_readable_summary}
              </pre>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}
