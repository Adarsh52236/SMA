"use client";

import React, { useState } from "react";
import { PredictionRequest, PredictionResponse, HistoryItem } from "@/lib/types";
import { PredictionForm } from "@/components/prediction/PredictionForm";
import { PredictionResult } from "@/components/prediction/PredictionResult";
import { PredictionHistory } from "@/components/prediction/PredictionHistory";
import { Calculator, ArrowLeft } from "lucide-react";
import { Button } from "@/components/common/Button";

const STORAGE_KEY = "agroyield_session_history";

export default function PredictStudioPage() {
  const [currentResult, setCurrentResult] = useState<PredictionResponse | null>(null);
  const [currentRequest, setCurrentRequest] = useState<PredictionRequest | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Lazy state initialization from sessionStorage
  const [history, setHistory] = useState<HistoryItem[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const saveHistory = (newHistory: HistoryItem[]) => {
    setHistory(newHistory);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
    } catch {
      // Ignore quota/sessionStorage errors
    }
  };

  const handlePredictionSuccess = (response: PredictionResponse, request: PredictionRequest) => {
    setCurrentResult(response);
    setCurrentRequest(request);

    // Add to session history
    const newItem: HistoryItem = {
      id: response.request_id || `hist-${Date.now()}`,
      timestamp: new Date().toISOString(),
      request,
      response,
    };

    const updated = [newItem, ...history.slice(0, 9)]; // Keep max 10 recent
    saveHistory(updated);

    // Scroll smoothly to top of results
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSelectHistory = (item: HistoryItem) => {
    setCurrentResult(item.response);
    setCurrentRequest(item.request);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDeleteHistoryItem = (id: string) => {
    const updated = history.filter((h) => h.id !== id);
    saveHistory(updated);
  };

  const handleClearHistory = () => {
    saveHistory([]);
  };

  const handleReset = () => {
    setCurrentResult(null);
    setCurrentRequest(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="p-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300">
              <Calculator className="w-5 h-5" />
            </span>
            <span className="text-xs uppercase font-bold tracking-wider text-emerald-800 dark:text-emerald-400">
              Inference Studio
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-zinc-900 dark:text-zinc-50 tracking-tight">
            Multi-Crop Yield Prediction Studio
          </h1>
          <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 mt-1 max-w-2xl">
            Configure agroclimatic measurements and ISRIC SoilGrids 0–30 cm soil parameters across 7 supported crops
            (Soybean, Rice, Wheat, Cotton, Maize, Chickpea, Groundnut) in verified Maharashtra districts.
          </p>
        </div>

        {currentResult && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
            className="self-start sm:self-auto"
          >
            Edit Inputs
          </Button>
        )}
      </div>

      {/* Main Content: Result vs Form */}
      {currentResult && currentRequest ? (
        <PredictionResult
          result={currentResult}
          onReset={handleReset}
        />
      ) : (
        <PredictionForm
          onSuccess={handlePredictionSuccess}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
        />
      )}

      {/* Session History Component */}
      <PredictionHistory
        onSelect={handleSelectHistory}
        currentHistory={history}
        onClearHistory={handleClearHistory}
        onDeleteItem={handleDeleteHistoryItem}
      />
    </div>
  );
}
