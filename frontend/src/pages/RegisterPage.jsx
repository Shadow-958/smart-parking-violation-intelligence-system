import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "", full_name: "" });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(form);
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed. Check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-asphalt px-4">
      <div className="w-full max-w-sm border border-white/10 bg-asphalt-light p-8 text-paper">
        <h1 className="mb-1 font-display text-2xl">Create an account</h1>
        <p className="mb-6 font-mono text-xs text-paper/50">
          Report parking violations in your area
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Full name</label>
            <input
              value={form.full_name}
              onChange={update("full_name")}
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Username</label>
            <input
              value={form.username}
              onChange={update("username")}
              required
              minLength={3}
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={update("email")}
              required
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-xs uppercase text-paper/60">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={update("password")}
              required
              minLength={8}
              className="w-full border border-white/20 bg-asphalt px-3 py-2 text-paper focus-visible:outline-curb-yellow"
            />
          </div>

          {error && <p className="text-sm text-curb-red">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-curb-yellow py-2 font-display uppercase tracking-wide text-asphalt-dark disabled:opacity-50"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center font-mono text-xs text-paper/50">
          Already registered?{" "}
          <Link to="/login" className="text-curb-yellow">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
