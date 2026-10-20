"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sprout, LayoutDashboard, Calculator, LineChart, BookOpen, Menu, X } from "lucide-react";
import { ApiStatusBadge } from "./ApiStatusBadge";

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: "/", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
    { href: "/predict", label: "Yield Studio", icon: <Calculator className="w-4 h-4" /> },
    { href: "/insights", label: "Model Insights", icon: <LineChart className="w-4 h-4" /> },
    { href: "/methodology", label: "Methodology", icon: <BookOpen className="w-4 h-4" /> },
  ];

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-white/90 dark:bg-zinc-950/90 border-b border-zinc-200 dark:border-zinc-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Title */}
          <Link
            href="/"
            className="flex items-center gap-3 text-emerald-800 dark:text-emerald-400 font-semibold tracking-tight hover:opacity-90 transition-opacity"
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-700 dark:bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <Sprout className="w-5 h-5 text-emerald-100" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-bold text-zinc-900 dark:text-zinc-50 leading-tight">
                AgroYield <span className="text-emerald-700 dark:text-emerald-400 font-medium">MH</span>
              </span>
              <span className="text-[11px] font-normal text-zinc-500 dark:text-zinc-400 leading-none">
                Soybean Prediction System
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 shadow-xs"
                      : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800/60"
                  }`}
                >
                  <span className={isActive ? "text-emerald-700 dark:text-emerald-400" : "text-zinc-400 dark:text-zinc-500"}>
                    {link.icon}
                  </span>
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Service Status and Actions */}
          <div className="hidden sm:flex items-center gap-3">
            <ApiStatusBadge />
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center gap-2 sm:hidden">
            <ApiStatusBadge />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 focus:outline-none"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 pt-2 pb-4 space-y-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 font-semibold"
                    : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
                }`}
              >
                {link.icon}
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}
