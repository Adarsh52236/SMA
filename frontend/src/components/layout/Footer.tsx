import React from "react";
import Link from "next/link";
import { Sprout, ExternalLink, ShieldCheck, Database } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 py-10 mt-auto transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand & Mission */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-400 font-semibold">
              <div className="w-7 h-7 rounded bg-emerald-700 dark:bg-emerald-600 flex items-center justify-center text-white">
                <Sprout className="w-4 h-4" />
              </div>
              <span className="text-zinc-900 dark:text-zinc-100 font-bold">
                AgroYield MH
              </span>
            </div>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 max-w-md leading-relaxed">
              Applied agricultural machine learning system for predicting rainfed Kharif soybean
              yields across Maharashtra from multi-decade meteorological observations and topsoil
              characteristics.
            </p>
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Strict anti-fabrication standards: zero synthetic observations.</span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider mb-3">
              Platform
            </h4>
            <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <li>
                <Link href="/" className="hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors">
                  Overview Dashboard
                </Link>
              </li>
              <li>
                <Link href="/predict" className="hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors">
                  Yield Prediction Studio
                </Link>
              </li>
              <li>
                <Link href="/insights" className="hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors">
                  Model Transparency & Metrics
                </Link>
              </li>
              <li>
                <Link href="/methodology" className="hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors">
                  Data & Modeling Methodology
                </Link>
              </li>
            </ul>
          </div>

          {/* Verified Data Sources */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-zinc-500" />
              <span>Data Provenance</span>
            </h4>
            <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <li>
                <a
                  href="https://aps.dac.gov.in/APY/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors"
                >
                  <span>DES Ministry of Agriculture</span>
                  <ExternalLink className="w-3 h-3 opacity-60" />
                </a>
              </li>
              <li>
                <a
                  href="https://power.larc.nasa.gov/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors"
                >
                  <span>NASA POWER Agroclimatology</span>
                  <ExternalLink className="w-3 h-3 opacity-60" />
                </a>
              </li>
              <li>
                <a
                  href="https://soilgrids.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors"
                >
                  <span>ISRIC SoilGrids 2.0 (0-30cm)</span>
                  <ExternalLink className="w-3 h-3 opacity-60" />
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Disclaimer */}
        <div className="pt-6 border-t border-zinc-200/80 dark:border-zinc-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500 dark:text-zinc-400">
          <p>
            © 2026 Maharashtra Crop Yield ML Project. Kharif Soybean Research Prototype.
          </p>
          <p className="text-zinc-500 text-center sm:text-right">
            End-of-season yield estimate based on retrospective weather; not an agronomic prescription.
          </p>
        </div>
      </div>
    </footer>
  );
}
