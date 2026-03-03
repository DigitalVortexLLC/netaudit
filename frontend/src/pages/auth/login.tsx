import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useRegistrationStatus } from "@/hooks/use-settings";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const { data: regStatus } = useRegistrationStatus();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ username, password });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { non_field_errors?: string[] } } };
      setError(axiosErr.response?.data?.non_field_errors?.[0] || "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "#1a1a2e" }}>
      <div className="flex max-w-[900px] w-full min-h-[520px] rounded-2xl overflow-hidden" style={{ boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)", border: "1px solid rgba(255, 255, 255, 0.06)" }}>
        {/* Brand panel */}
        <div
          className="hidden md:flex flex-col justify-between items-center p-10 relative overflow-hidden"
          style={{
            flex: "0 0 40%",
            background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
          }}
        >
          <div className="flex-1" />
          <div className="relative text-center">
            <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">Netaudit</h1>
            <p className="text-[#b0b0c8] text-lg font-light leading-relaxed">
              Network Compliance,<br />Automated.
            </p>
          </div>
          <div className="flex-1" />
          <p className="text-[#64b5f6] text-xs opacity-70 text-center">
            Continuous auditing for network device configurations
          </p>
        </div>

        {/* Form panel */}
        <div className="flex-1 flex flex-col justify-center p-10" style={{ background: "#2d2d2d" }}>
          <div className="max-w-[400px] w-full">
            <h2 className="text-white text-3xl font-semibold mb-2">Welcome back</h2>
            <p className="text-[#888] text-sm mb-7">Sign in to your account</p>

            {error && (
              <div className="rounded-lg p-3 mb-4" style={{ background: "rgba(183, 28, 28, 0.15)", border: "1px solid #b71c1c" }}>
                <p className="text-[#ef9a9a] text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Username or email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }}
                />
              </div>
              <div className="mb-4 relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 pr-12 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#666] hover:text-[#b0b0c8] transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                    {showPassword && <path d="M1 1l22 22" />}
                  </svg>
                </button>
              </div>

              <div className="flex justify-between items-center mb-4">
                <label className="flex items-center gap-2 text-[#b0b0c8] text-sm cursor-pointer">
                  <input type="checkbox" className="accent-[#1976d2]" />
                  Remember me
                </label>
                <Link to="/password-reset" className="text-sm text-[#64b5f6] hover:underline">
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 mt-2 rounded-[10px] text-sm font-semibold text-white cursor-pointer transition-colors disabled:opacity-50"
                style={{ background: loading ? "#1565c0" : "#1976d2" }}
                onMouseOver={(e) => !loading && ((e.target as HTMLElement).style.background = "#1565c0")}
                onMouseOut={(e) => !loading && ((e.target as HTMLElement).style.background = "#1976d2")}
              >
                {loading ? "Signing in..." : "Sign In"}
              </button>
            </form>

            <div className="flex items-center gap-4 my-5">
              <div className="flex-1 h-px bg-[#3a3a5a]" />
              <span className="text-[#666] text-xs">or</span>
              <div className="flex-1 h-px bg-[#3a3a5a]" />
            </div>

            <button
              type="button"
              className="w-full py-3 rounded-[10px] text-sm font-semibold text-white cursor-pointer transition-colors"
              style={{ background: "#2a2a4a", border: "1px solid #3a3a5a" }}
              onMouseOver={(e) => ((e.target as HTMLElement).style.background = "#35355a")}
              onMouseOut={(e) => ((e.target as HTMLElement).style.background = "#2a2a4a")}
            >
              Sign in with Passkey
            </button>

            {regStatus?.public_registration_enabled !== false && (
              <div className="mt-6 text-center text-sm text-[#888]">
                <p>
                  Don&apos;t have an account?{" "}
                  <Link to="/signup" className="text-[#64b5f6] hover:underline">
                    Create one
                  </Link>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
