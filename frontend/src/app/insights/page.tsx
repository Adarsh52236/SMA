"use client";

import React, { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { ModelMetadataResponse } from "@/lib/types";
import { MetricsOverview } from "@/components/insights/MetricsOverview";
import { FeatureImportanceChart } from "@/components/insights/FeatureImportanceChart";
import { DatasetProvenanceCard } from "@/components/insights/DatasetProvenanceCard";
import { Card, CardHeader } from "@/components/common/Card";
import { Alert } from "@/components/common/Alert";
import { LineChart, Table, RefreshCw } from "lucide-react";
import { Button } from "@/components/common/Button";

export default function ModelInsightsPage() {
  const [metadata, setMetadata] = useState<ModelMetadataResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;

    async function load() {
      try {
        const data = await api.getModelMetadata();
        if (!ignore) {
          setMetadata(data);
          setError(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Failed to connect to the backend metadata endpoint.");
          }
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      ignore = true;
    };
  }, []);

  const handleManualRefresh = async () => {
    setIsLoading(true);
    try {
      const data = await api.getModelMetadata();
      setMetadata(data);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to connect to the backend metadata endpoint.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300">
              <LineChart className="w-5 h-5" />
            </span>
            <span className="text-xs uppercase font-bold tracking-wider text-purple-800 dark:text-purple-400">
              Model Transparency
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
            Evaluation Metrics & Model Architecture
          </h1>
          <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl">
            Live governance manifest from <code>GET /api/v1/model/metadata</code> detailing chronological
            validation performance, untouched test metrics, and permutation feature importances.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleManualRefresh}
          isLoading={isLoading}
          leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
        >
          Refresh Metadata
        </Button>
      </div>

      {error && (
        <Alert variant="error" title="Backend Connection Issue">
          {error}
          <div className="mt-2">
            <button
              onClick={handleManualRefresh}
              className="text-xs font-semibold underline hover:no-underline"
            >
              Try reconnecting to backend
            </button>
          </div>
        </Alert>
      )}

      {/* 1. Evaluation Metrics Grid */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>1. Chronological Split Performance</span>
        </h2>
        <MetricsOverview metadata={metadata} isLoading={isLoading} />
      </section>

      {/* 2. Permutation Feature Importance */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>2. Model Explainability & Feature Drivers</span>
        </h2>
        <FeatureImportanceChart
          items={metadata?.global_feature_importance || []}
        />
      </section>

      {/* 3. Dataset Provenance Card */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <span>3. Data Provenance & Cryptographic Verification</span>
        </h2>
        <DatasetProvenanceCard
          sha256={metadata?.dataset_sha256}
          districts={metadata?.supported_districts}
          totalRows={194}
        />
      </section>

      {/* 4. Complete Feature Schema Registry Table */}
      {metadata?.supported_features && metadata.supported_features.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <span>4. Model Feature Schema Registry</span>
          </h2>
          <Card>
            <CardHeader
              title="Verified Predictor Specifications"
              subtitle="All 15 input columns expected by the trained scikit-learn preprocessing pipeline."
              badge={<Table className="w-4 h-4 text-emerald-600" />}
            />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800 text-zinc-500 uppercase tracking-wider font-semibold">
                    <th className="py-3 px-3">Feature Name</th>
                    <th className="py-3 px-3">Units</th>
                    <th className="py-3 px-3">Data Source</th>
                    <th className="py-3 px-3">Availability Time</th>
                    <th className="py-3 px-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60 font-mono">
                  {metadata.supported_features.map((feat) => (
                    <tr
                      key={feat.name}
                      className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/40 transition-colors"
                    >
                      <td className="py-2.5 px-3 font-semibold text-zinc-900 dark:text-zinc-100">
                        {feat.name}
                      </td>
                      <td className="py-2.5 px-3 text-emerald-700 dark:text-emerald-400">
                        {feat.units}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-zinc-600 dark:text-zinc-400">
                        {feat.source}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-zinc-500">
                        {feat.availability_time}
                      </td>
                      <td className="py-2.5 px-3 font-sans text-zinc-600 dark:text-zinc-300 max-w-xs">
                        {feat.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </section>
      )}
    </div>
  );
}
