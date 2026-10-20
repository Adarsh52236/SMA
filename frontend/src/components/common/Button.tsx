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
      "bg-emerald-700 hover:bg-emerald-800 text-white shadow-sm border border-emerald-800/80 active:bg-emerald-900 focus-visible:ring-2 focus-visible:ring-emerald-500",
    secondary:
      "bg-zinc-100 hover:bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700 active:bg-zinc-300 focus-visible:ring-2 focus-visible:ring-zinc-400",
    outline:
      "bg-transparent hover:bg-zinc-50 text-zinc-800 dark:text-zinc-200 border border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600 focus-visible:ring-2 focus-visible:ring-zinc-400",
    ghost:
      "bg-transparent hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 active:bg-zinc-200 focus-visible:ring-2 focus-visible:ring-zinc-400",
    danger:
      "bg-rose-700 hover:bg-rose-800 text-white shadow-sm border border-rose-800 focus-visible:ring-2 focus-visible:ring-rose-500",
  };

  const sizeStyles = {
    sm: "text-xs px-3 py-1.5 rounded-md font-medium gap-1.5",
    md: "text-sm px-4 py-2.5 rounded-lg font-medium gap-2",
    lg: "text-base px-5 py-3 rounded-xl font-semibold gap-2.5",
  };

  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center transition-all select-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-offset-2 dark:focus-visible:ring-offset-zinc-900 ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
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
