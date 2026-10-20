import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: "default" | "muted" | "bordered" | "gemini";
}

export function Card({
  children,
  className = "",
  variant = "default",
  ...props
}: CardProps) {
  const variantStyles = {
    default: "bg-white border border-slate-200/90 shadow-xs hover:border-slate-300 transition-colors",
    muted: "bg-slate-50/70 border border-slate-200/70",
    bordered: "bg-white border-2 border-dashed border-slate-200",
    gemini: "bg-white border border-indigo-100 shadow-[0_4px_20px_-4px_rgba(99,102,241,0.08)]",
  };

  return (
    <div
      className={`rounded-2xl p-6 transition-all ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  badge,
  action,
  className = "",
}: {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-4 border-b border-slate-100 ${className}`}>
      <div>
        <div className="flex items-center gap-2.5">
          <h3 className="text-base font-semibold tracking-tight text-slate-900">
            {title}
          </h3>
          {badge}
        </div>
        {subtitle && (
          <p className="text-xs text-slate-500 mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
      {action && <div className="flex items-center gap-2">{action}</div>}
    </div>
  );
}
