"use client";

import React from "react";
import Link from "next/link";
import { Sparkles, Cpu } from "lucide-react";
import { ApiStatusBadge } from "./ApiStatusBadge";

export function Navbar() {
  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-white/95 border-b border-slate-200/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <Link
            href="/"
            className="flex items-center gap-3 group transition-opacity hover:opacity-90"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-sm shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold text-slate-900 leading-tight flex items-center gap-1.5">
                <span>AgroYield</span>
                <span className="gemini-gradient-text font-black">AI</span>
              </span>
              <span className="text-[11px] font-medium text-slate-500 leading-none">
                Crop Yield Prediction Platform
              </span>
            </div>
          </Link>

          {/* Model & System Governance Pills */}
          <div className="hidden md:flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs text-slate-600 font-medium">
              <Cpu className="w-3.5 h-3.5 text-indigo-600" />
              <span>Multi-Crop Random Forest • 7 Crops</span>
            </div>
          </div>

          {/* Service Status Indicator */}
          <div className="flex items-center gap-3">
            <ApiStatusBadge />
          </div>
        </div>
      </div>
    </header>
  );
}
