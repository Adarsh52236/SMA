"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiStatus } from "@/lib/types";
import { RefreshCw } from "lucide-react";

export function ApiStatusBadge() {
  const [status, setStatus] = useState<ApiStatus>({
    isChecking: true,
    backendReachable: false,
    modelReady: false,
    lastChecked: null,
  });

  const checkStatus = async () => {
    try {
      const readyRes = await api.checkReadiness();
      if (readyRes.status === "ready") {
        setStatus({
          isChecking: false,
          backendReachable: true,
          modelReady: true,
          modelName: readyRes.model_name || "Random_Forest",
          lastChecked: new Date(),
        });
      } else {
        setStatus({
          isChecking: false,
          backendReachable: true,
          modelReady: false,
          errorMessage: readyRes.detail || "Model not loaded",
          lastChecked: new Date(),
        });
      }
    } catch {
      // Check health as a fallback
      try {
        const healthRes = await api.checkHealth();
        setStatus({
          isChecking: false,
          backendReachable: true,
          modelReady: healthRes.model_loaded,
          lastChecked: new Date(),
          errorMessage: healthRes.model_loaded ? undefined : "Model artifact unloaded",
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Service unreachable";
        setStatus({
          isChecking: false,
          backendReachable: false,
          modelReady: false,
          lastChecked: new Date(),
          errorMessage: message,
        });
      }
    }
  };

  useEffect(() => {
    let ignore = false;

    async function probe() {
      try {
        const readyRes = await api.checkReadiness();
        if (!ignore) {
          if (readyRes.status === "ready") {
            setStatus({
              isChecking: false,
              backendReachable: true,
              modelReady: true,
              modelName: readyRes.model_name || "Random_Forest",
              lastChecked: new Date(),
            });
          } else {
            setStatus({
              isChecking: false,
              backendReachable: true,
              modelReady: false,
              errorMessage: readyRes.detail || "Model not loaded",
              lastChecked: new Date(),
            });
          }
        }
      } catch {
        try {
          const healthRes = await api.checkHealth();
          if (!ignore) {
            setStatus({
              isChecking: false,
              backendReachable: true,
              modelReady: healthRes.model_loaded,
              lastChecked: new Date(),
              errorMessage: healthRes.model_loaded ? undefined : "Model artifact unloaded",
            });
          }
        } catch (err: unknown) {
          if (!ignore) {
            const message = err instanceof Error ? err.message : "Service unreachable";
            setStatus({
              isChecking: false,
              backendReachable: false,
              modelReady: false,
              lastChecked: new Date(),
              errorMessage: message,
            });
          }
        }
      }
    }

    probe();

    const handleFocus = () => {
      probe();
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      ignore = true;
      window.removeEventListener("focus", handleFocus);
    };
  }, []);

  let dotColor = "bg-amber-500 animate-pulse";
  let label = "Connecting...";
  let tooltip = "Checking backend connectivity";

  if (!status.isChecking) {
    if (status.modelReady) {
      dotColor = "bg-emerald-500";
      label = status.modelName ? `Ready: ${status.modelName}` : "Model Ready";
      tooltip = "Trained model artifact loaded and ready for prediction";
    } else if (status.backendReachable) {
      dotColor = "bg-amber-500";
      label = "Model Unready";
      tooltip = status.errorMessage || "Backend online, but model artifact is not loaded";
    } else {
      dotColor = "bg-rose-500";
      label = "Backend Offline";
      tooltip = status.errorMessage || "Cannot reach FastAPI backend. Check Render / local server.";
    }
  }

  return (
    <div className="flex items-center gap-2">
      <div
        className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/80 text-zinc-700 dark:text-zinc-300"
        title={tooltip}
      >
        <span className={`w-2 h-2 rounded-full ${dotColor}`} />
        <span className="font-mono tracking-tight">{label}</span>
      </div>
      <button
        onClick={() => {
          setStatus((prev) => ({ ...prev, isChecking: true }));
          checkStatus();
        }}
        disabled={status.isChecking}
        className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
        title="Refresh service status"
        aria-label="Refresh status"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${status.isChecking ? "animate-spin text-emerald-600" : ""}`} />
      </button>
    </div>
  );
}
