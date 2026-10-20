import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  disabled,
  className = "",
  ...props
}: ButtonProps) {
  const variantStyles = {
    primary:
      "bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:via-indigo-700 hover:to-purple-700 text-white shadow-sm hover:shadow-md active:opacity-95 focus-visible:ring-2 focus-visible:ring-indigo-500",
    secondary:
      "bg-slate-100 hover:bg-slate-200 text-slate-900 border border-slate-200 active:bg-slate-300 focus-visible:ring-2 focus-visible:ring-slate-400",
    outline:
      "bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 hover:border-slate-400 shadow-2xs focus-visible:ring-2 focus-visible:ring-slate-400",
    ghost:
      "bg-transparent hover:bg-slate-100 text-slate-700 active:bg-slate-200 focus-visible:ring-2 focus-visible:ring-slate-400",
    danger:
      "bg-rose-600 hover:bg-rose-700 text-white shadow-sm focus-visible:ring-2 focus-visible:ring-rose-500",
  };

  const sizeStyles = {
    sm: "text-xs px-3 py-1.5 rounded-lg font-medium gap-1.5",
    md: "text-sm px-4 py-2 rounded-xl font-medium gap-2",
    lg: "text-base px-5 py-2.5 rounded-xl font-semibold gap-2.5",
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center transition-all select-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-offset-2 ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        leftIcon && <span className="inline-flex shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="inline-flex shrink-0">{rightIcon}</span>}
    </button>
  );
}
