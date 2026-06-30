"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { login } from "@/lib/api";
import { saveSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await login(email, password);
      saveSession(res.access_token, res.role);
      router.replace("/");
    } catch (err) {
      setError("Invalid email or password.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <Logo size={44} />
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-content">
              Edge-Surveillance-Node
            </h1>
            <p className="text-sm text-content-muted">Sign in to the fleet console</p>
          </div>
        </div>
        <form onSubmit={submit} className="card space-y-4 p-6">
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-wide text-content-faint">Email</label>
            <input
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface-overlay px-3 py-2 text-sm text-content focus:border-accent/50 focus:outline-none"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs uppercase tracking-wide text-content-faint">Password</label>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-surface-border bg-surface-overlay px-3 py-2 text-sm text-content focus:border-accent/50 focus:outline-none"
            />
          </div>
          {error && <p className="text-sm text-status-error">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-surface transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
