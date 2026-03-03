import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { useRegistrationStatus } from "@/hooks/use-settings";

export function SignupPage() {
  const { register, isAuthenticated } = useAuth();
  const { data: regStatus, isLoading: regLoading } = useRegistrationStatus();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;

  if (regLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#1a1a2e" }}>
        <p className="text-[#b0b0c8]">Loading...</p>
      </div>
    );
  }

  if (regStatus && !regStatus.public_registration_enabled) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "#1a1a2e" }}>
        <div className="flex max-w-[900px] w-full min-h-[520px] rounded-2xl overflow-hidden shadow-2xl">
          <div
            className="hidden md:flex flex-col justify-center items-center p-10 relative overflow-hidden"
            style={{
              flex: "0 0 40%",
              background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
            }}
          >
            <div className="relative text-center">
              <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">Netaudit</h1>
              <p className="text-[#b0b0c8] text-lg font-light leading-relaxed">
                Network Configuration<br />Audit Platform
              </p>
            </div>
          </div>
          <div className="flex-1 flex flex-col justify-center items-center p-10" style={{ background: "#2d2d2d" }}>
            <h2 className="text-white text-2xl font-semibold mb-4">Registration Disabled</h2>
            <p className="text-[#888] text-sm text-center mb-6">
              Public registration is currently disabled. Please contact your administrator for access.
            </p>
            <Link
              to="/login"
              className="text-[#64b5f6] hover:underline text-sm"
            >
              Back to Sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password1 !== password2) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await register({ username, email, password1, password2 });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: Record<string, string[]> } };
      const data = axiosErr.response?.data;
      if (data) {
        const firstError = Object.values(data).flat()[0];
        setError(firstError || "Registration failed.");
      } else {
        setError("Registration failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "#1a1a2e" }}>
      <div className="flex max-w-[900px] w-full min-h-[520px] rounded-2xl overflow-hidden shadow-2xl">
        <div
          className="hidden md:flex flex-col justify-center items-center p-10 relative overflow-hidden"
          style={{
            flex: "0 0 40%",
            background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
          }}
        >
          <div className="relative text-center">
            <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">Netaudit</h1>
            <p className="text-[#b0b0c8] text-lg font-light leading-relaxed">
              Network Configuration<br />Audit Platform
            </p>
          </div>
        </div>

        <div className="flex-1 flex flex-col justify-center p-10" style={{ background: "#2d2d2d" }}>
          <div className="max-w-[400px] w-full">
            <h2 className="text-white text-3xl font-semibold mb-2">Create account</h2>
            <p className="text-[#888] text-sm mb-7">Sign up for a new account</p>

            {error && (
              <div className="rounded-lg p-3 mb-4" style={{ background: "rgba(183, 28, 28, 0.15)", border: "1px solid #b71c1c" }}>
                <p className="text-[#ef9a9a] text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <input type="text" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} required
                  className="w-full px-4 py-3 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }} />
              </div>
              <div className="mb-4">
                <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required
                  className="w-full px-4 py-3 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }} />
              </div>
              <div className="mb-4">
                <input type="password" placeholder="Password" value={password1} onChange={(e) => setPassword1(e.target.value)} required
                  className="w-full px-4 py-3 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }} />
              </div>
              <div className="mb-4">
                <input type="password" placeholder="Confirm Password" value={password2} onChange={(e) => setPassword2(e.target.value)} required
                  className="w-full px-4 py-3 rounded-[10px] text-sm text-[#e0e0e0] placeholder-[#666] focus:outline-none focus:border-[#64b5f6] focus:shadow-[0_0_0_3px_rgba(100,181,246,0.1)] transition-colors"
                  style={{ background: "#1a1a2e", border: "1px solid #3a3a5a" }} />
              </div>

              <button type="submit" disabled={loading}
                className="w-full py-3 mt-2 rounded-[10px] text-sm font-semibold text-white cursor-pointer transition-colors disabled:opacity-50"
                style={{ background: loading ? "#1565c0" : "#1976d2" }}
                onMouseOver={(e) => !loading && ((e.target as HTMLElement).style.background = "#1565c0")}
                onMouseOut={(e) => !loading && ((e.target as HTMLElement).style.background = "#1976d2")}>
                {loading ? "Creating account..." : "Create Account"}
              </button>
            </form>

            <div className="mt-6 text-center text-sm text-[#888]">
              <p>Already have an account?{" "}
                <Link to="/login" className="text-[#64b5f6] hover:underline">Sign in</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
