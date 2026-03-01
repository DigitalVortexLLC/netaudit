import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import api, { setTokens, clearTokens, getRefreshToken } from "@/lib/api";
import type { User, LoginCredentials, RegisterData } from "@/types";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const response = await api.get("/auth/user/");
      setUser(response.data);
    } catch {
      setUser(null);
      clearTokens();
    }
  }, []);

  // On mount, try to restore session from refresh token
  useEffect(() => {
    const init = async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        setIsLoading(false);
        return;
      }
      try {
        const response = await api.post("/auth/token/refresh/", {
          refresh: refreshToken,
        });
        setTokens(response.data.access, response.data.refresh);
        await fetchUser();
      } catch {
        clearTokens();
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, [fetchUser]);

  const login = async (credentials: LoginCredentials) => {
    const response = await api.post("/auth/login/", credentials);
    setTokens(response.data.access, response.data.refresh);
    await fetchUser();
  };

  const register = async (data: RegisterData) => {
    const response = await api.post("/auth/register/", data);
    setTokens(response.data.access, response.data.refresh);
    await fetchUser();
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Logout even if API call fails
    }
    clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
