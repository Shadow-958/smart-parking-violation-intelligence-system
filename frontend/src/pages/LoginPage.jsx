import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Incorrect username or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt px-4">
      <div className="w-full max-w-sm border border-white/10 bg-asphalt-light p-8 text-paper">
        <h1 className="mb-1 font-display text-2xl">Sign in</h1>
        <p className="mb-6 font-mono text-xs text-paper/50">
          Smart Parking Violation Intelligence System
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>

          {error && <p className="text-sm text-curb-red">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-curb-yellow py-2 font-display uppercase tracking-wide text-asphalt-dark disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center font-mono text-xs text-paper/50">
          No account?{" "}
          <Link to="/register" className="text-curb-yellow">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
