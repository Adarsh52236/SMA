import React from "react";
import { Sparkles, ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-slate-200 bg-slate-50/60 py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <span className="font-semibold text-slate-700">AgroYield AI</span>
            <span>•</span>
            <span>Trained on ICRISAT DLD, NASA POWER & ISRIC SoilGrids 2.0</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-slate-600">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              <span>Production Model v1.0.0</span>
            </span>
            <span>•</span>
            <span>End-of-season observed weather estimation</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
