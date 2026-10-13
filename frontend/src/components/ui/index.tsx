import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { useId } from "react";

type Variant = "primary" | "secondary" | "danger" | "link";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  block?: boolean;
}

export function Button({ variant = "primary", block = false, className, type = "button", ...rest }: ButtonProps) {
  const classes = ["btn", `btn--${variant}`, block && "btn--block", className].filter(Boolean).join(" ");
  return <button type={type} className={classes} {...rest} />;
}

export function Notice({ tone = "info", children }: { tone?: "info" | "success" | "error"; children: ReactNode }) {
  return (
    <p className={`notice notice--${tone}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Field({ label, hint, ...input }: FieldProps) {
  const id = useId();
  return (
    <label className="field" htmlFor={id}>
      <span className="field__label">{label}</span>
      <input id={id} {...input} />
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-block" role="status">
      <span className="spinner" aria-hidden />
      {label && <span>{label}</span>}
    </div>
  );
}

export function Section({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="section">
      <div className="section__head">
        <h2>{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}
