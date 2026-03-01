# React + shadcn/ui Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a fully separate React SPA with shadcn/ui that consumes the existing Django REST API, replacing Django templates.

**Architecture:** Vite + React + TypeScript SPA in `frontend/`, consuming `http://localhost:8000/api/v1/`. JWT auth with tokens in memory/localStorage. shadcn/ui components themed with existing dark color palette.

**Tech Stack:** Vite, React 18, TypeScript, Tailwind CSS, shadcn/ui, React Router v6, TanStack Query, Axios, Zod, Lucide React

---

## Phase 1: Project Scaffolding

### Task 1: Initialize Vite + React + TypeScript

**Files:**
- Create: `frontend/` (scaffolded by Vite)

**Step 1: Clean existing frontend directory**

```bash
rm -rf frontend/.vite frontend/node_modules
```

**Step 2: Scaffold Vite project**

```bash
cd /Users/aaronroth/Documents/netaudit
npm create vite@latest frontend -- --template react-ts
```

**Step 3: Install dependencies**

```bash
cd frontend
npm install
npm install react-router-dom @tanstack/react-query axios zod @hookform/resolvers react-hook-form
```

**Step 4: Verify dev server starts**

```bash
npm run dev
```

Expected: Vite dev server running on http://localhost:5173 with React template page.

**Step 5: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript frontend"
```

---

### Task 2: Install and Configure Tailwind CSS

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/index.css` → rename to `frontend/src/globals.css`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`

**Step 1: Install Tailwind**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npm install -D tailwindcss @tailwindcss/vite
```

**Step 2: Configure Vite plugin**

Update `frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

**Step 3: Create globals.css with Tailwind directives**

Delete `frontend/src/index.css` and `frontend/src/App.css`. Create `frontend/src/globals.css`:

```css
@import "tailwindcss";
```

**Step 4: Update main.tsx to import globals.css**

Update `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./globals.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

**Step 5: Update tsconfig files for path aliases**

Update `frontend/tsconfig.json` to add:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Update `frontend/tsconfig.app.json` to include in `compilerOptions`:

```json
"baseUrl": ".",
"paths": {
  "@/*": ["./src/*"]
}
```

**Step 6: Simplify App.tsx to verify Tailwind works**

```tsx
function App() {
  return (
    <div className="min-h-screen bg-zinc-900 text-white flex items-center justify-center">
      <h1 className="text-3xl font-bold">Netaudit</h1>
    </div>
  );
}

export default App;
```

**Step 7: Verify Tailwind is working**

```bash
npm run dev
```

Expected: Dark background with white centered "Netaudit" heading.

**Step 8: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/
git commit -m "feat: configure Tailwind CSS with path aliases"
```

---

### Task 3: Install and Configure shadcn/ui with Custom Theme

**Files:**
- Create: `frontend/components.json`
- Create: `frontend/src/lib/utils.ts`
- Modify: `frontend/src/globals.css`

**Step 1: Install shadcn/ui**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx shadcn@latest init
```

When prompted:
- Style: Default
- Base color: Zinc
- CSS variables: Yes

This creates `components.json` and `src/lib/utils.ts`.

**Step 2: Override globals.css with custom dark theme**

Replace `frontend/src/globals.css` with the Netaudit dark theme mapped to shadcn CSS variables. The hex-to-HSL conversions for the existing palette:

- `#242424` → `0 0% 14%` (background)
- `#1a1a2e` → `240 27% 14%` (sidebar)
- `#2d2d2d` → `0 0% 18%` (card)
- `#64b5f6` → `207 89% 68%` (primary/accent)
- `#1976d2` → `210 79% 46%` (primary darker, for ring)
- `#e0e0e0` → `0 0% 88%` (foreground)
- `#b0b0c8` → `240 15% 74%` (muted-foreground)
- `#2a2a4a` → `240 28% 23%` (border)
- `#333333` → `0 0% 20%` (input)
- `#3a3a3a` → `0 0% 23%` (border alt)

```css
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));
  --color-sidebar: hsl(var(--sidebar-background));
  --color-sidebar-foreground: hsl(var(--sidebar-foreground));
  --color-sidebar-accent: hsl(var(--sidebar-accent));
  --color-sidebar-accent-foreground: hsl(var(--sidebar-accent-foreground));
  --color-sidebar-border: hsl(var(--sidebar-border));
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

@layer base {
  :root {
    --radius: 0.625rem;
  }

  /* Dark theme (always-on, matching existing Netaudit palette) */
  :root {
    --background: 0 0% 14%;
    --foreground: 0 0% 88%;

    --card: 0 0% 18%;
    --card-foreground: 0 0% 88%;

    --popover: 0 0% 18%;
    --popover-foreground: 0 0% 88%;

    --primary: 207 89% 68%;
    --primary-foreground: 0 0% 10%;

    --secondary: 240 28% 23%;
    --secondary-foreground: 0 0% 88%;

    --muted: 0 0% 20%;
    --muted-foreground: 240 15% 74%;

    --accent: 240 28% 23%;
    --accent-foreground: 0 0% 88%;

    --destructive: 0 72% 51%;
    --destructive-foreground: 0 0% 100%;

    --border: 240 28% 23%;
    --input: 0 0% 20%;
    --ring: 210 79% 46%;

    --sidebar-background: 240 27% 14%;
    --sidebar-foreground: 240 15% 74%;
    --sidebar-accent: 240 28% 23%;
    --sidebar-accent-foreground: 0 0% 100%;
    --sidebar-border: 240 28% 23%;
    --sidebar-primary: 207 89% 68%;
    --sidebar-primary-foreground: 0 0% 10%;
    --sidebar-ring: 210 79% 46%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

**Step 3: Install initial shadcn components we'll need**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx shadcn@latest add button card table badge input label separator avatar dropdown-menu dialog command breadcrumb sidebar sheet tooltip form select textarea checkbox popover
```

**Step 4: Verify theme renders correctly**

Update `App.tsx` temporarily:

```tsx
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <h1 className="text-3xl font-bold mb-4">Netaudit Theme Test</h1>
      <div className="flex gap-4 mb-4">
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="destructive">Destructive</Button>
        <Button variant="outline">Outline</Button>
      </div>
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Test Card</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Card content with muted text.</p>
        </CardContent>
      </Card>
    </div>
  );
}

export default App;
```

**Step 5: Verify**

```bash
npm run dev
```

Expected: Dark background (#242424), card with slightly lighter bg (#2d2d2d), blue primary button (#64b5f6), proper text colors.

**Step 6: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/
git commit -m "feat: configure shadcn/ui with Netaudit dark theme"
```

---

## Phase 2: Foundation

### Task 4: TypeScript Types

**Files:**
- Create: `frontend/src/types/device.ts`
- Create: `frontend/src/types/rule.ts`
- Create: `frontend/src/types/audit.ts`
- Create: `frontend/src/types/schedule.ts`
- Create: `frontend/src/types/settings.ts`
- Create: `frontend/src/types/user.ts`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/types/index.ts`

**Step 1: Create all type files**

`frontend/src/types/api.ts`:

```typescript
/** Standard DRF paginated response */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** JWT auth tokens */
export interface AuthTokens {
  access: string;
  refresh: string;
}

/** Login credentials */
export interface LoginCredentials {
  username: string;
  password: string;
}

/** Registration data */
export interface RegisterData {
  username: string;
  email: string;
  password1: string;
  password2: string;
}
```

`frontend/src/types/user.ts`:

```typescript
export type UserRole = "admin" | "editor" | "viewer";

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_api_enabled: boolean;
  date_joined: string;
}
```

`frontend/src/types/device.ts`:

```typescript
export interface DeviceHeader {
  id?: number;
  key: string;
  value: string;
}

export interface Device {
  id: number;
  name: string;
  hostname: string;
  api_endpoint: string;
  effective_api_endpoint: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
  created_at: string;
  updated_at: string;
}

export interface DeviceGroup {
  id: number;
  name: string;
  description: string;
  devices: number[];
  device_count: number;
  created_at: string;
  updated_at: string;
}

export interface DeviceFormData {
  name: string;
  hostname: string;
  api_endpoint?: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
}

export interface DeviceGroupFormData {
  name: string;
  description: string;
  devices: number[];
}

export interface TestConnectionResult {
  status_code: number;
  content_length: number;
}
```

`frontend/src/types/rule.ts`:

```typescript
export type RuleType = "must_contain" | "must_not_contain" | "regex_match" | "regex_no_match";
export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface SimpleRule {
  id: number;
  name: string;
  description: string;
  rule_type: RuleType;
  pattern: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
  created_at: string;
  updated_at: string;
}

export interface CustomRule {
  id: number;
  name: string;
  description: string;
  filename: string;
  content: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
  created_at: string;
  updated_at: string;
}

export interface SimpleRuleFormData {
  name: string;
  description: string;
  rule_type: RuleType;
  pattern: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
}

export interface CustomRuleFormData {
  name: string;
  description: string;
  filename: string;
  content: string;
  severity: Severity;
  enabled: boolean;
  device: number | null;
  group: number | null;
}
```

`frontend/src/types/audit.ts`:

```typescript
export type AuditStatus = "pending" | "fetching_config" | "running_rules" | "completed" | "failed";
export type AuditTrigger = "manual" | "scheduled";
export type RuleOutcome = "passed" | "failed" | "error" | "skipped";

export interface AuditSummary {
  passed: number;
  failed: number;
  error: number;
  skipped?: number;
}

export interface RuleResult {
  id: number;
  audit_run: number;
  simple_rule: number | null;
  custom_rule: number | null;
  test_node_id: string;
  outcome: RuleOutcome;
  message: string;
  duration: number | null;
  severity: string;
  rule_name: string | null;
}

export interface AuditRun {
  id: number;
  device: number;
  device_name: string;
  status: AuditStatus;
  trigger: AuditTrigger;
  summary: AuditSummary | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AuditRunDetail extends AuditRun {
  results: RuleResult[];
  error_message: string;
  config_fetched_at: string | null;
}

export interface DashboardSummary {
  device_count: number;
  recent_audit_count: number;
  pass_rate: number;
}
```

`frontend/src/types/schedule.ts`:

```typescript
export interface AuditSchedule {
  id: number;
  device: number;
  name: string;
  cron_expression: string;
  enabled: boolean;
  django_q_schedule_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface AuditScheduleFormData {
  device: number;
  name: string;
  cron_expression: string;
  enabled: boolean;
}
```

`frontend/src/types/settings.ts`:

```typescript
export interface SiteSettings {
  default_api_endpoint: string;
}
```

`frontend/src/types/index.ts`:

```typescript
export * from "./api";
export * from "./user";
export * from "./device";
export * from "./rule";
export * from "./audit";
export * from "./schedule";
export * from "./settings";
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/types/
git commit -m "feat: add TypeScript types for all API models"
```

---

### Task 5: API Client with JWT Interceptor

**Files:**
- Create: `frontend/src/lib/api.ts`

**Step 1: Create the API client**

`frontend/src/lib/api.ts`:

```typescript
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token storage (in-memory for access, localStorage for refresh)
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setTokens(access: string, refresh: string): void {
  accessToken = access;
  localStorage.setItem("refresh_token", refresh);
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem("refresh_token");
}

export function getRefreshToken(): string | null {
  return localStorage.getItem("refresh_token");
}

// Request interceptor: attach access token
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 with token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token!);
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        });
        const { access, refresh } = response.data;
        setTokens(access, refresh);
        processQueue(null, access);
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/lib/api.ts
git commit -m "feat: add Axios API client with JWT interceptor"
```

---

### Task 6: Auth Context and Hook

**Files:**
- Create: `frontend/src/hooks/use-auth.tsx`

**Important backend prerequisite:** The dj-rest-auth config has `JWT_AUTH_HTTPONLY: True`. For a separate SPA, we need the refresh token in the response body. Update `backend/config/settings/base.py`:

```python
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,  # Changed: allow SPA to manage tokens
    "JWT_AUTH_RETURN_EXPIRATION": True,
}
```

**Step 1: Create auth context**

`frontend/src/hooks/use-auth.tsx`:

```tsx
import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import api, { setTokens, clearTokens, getRefreshToken, getAccessToken } from "@/lib/api";
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
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/hooks/use-auth.tsx
git commit -m "feat: add auth context with JWT login/logout/refresh"
```

---

### Task 7: API Query Hooks

**Files:**
- Create: `frontend/src/hooks/use-devices.ts`
- Create: `frontend/src/hooks/use-groups.ts`
- Create: `frontend/src/hooks/use-rules.ts`
- Create: `frontend/src/hooks/use-audits.ts`
- Create: `frontend/src/hooks/use-schedules.ts`
- Create: `frontend/src/hooks/use-settings.ts`
- Create: `frontend/src/hooks/use-users.ts`

**Step 1: Create all API hooks**

`frontend/src/hooks/use-devices.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Device, DeviceFormData, PaginatedResponse, TestConnectionResult } from "@/types";

export function useDevices(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["devices", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<Device>>("/devices/", { params });
      return response.data;
    },
  });
}

export function useDevice(id: number) {
  return useQuery({
    queryKey: ["devices", id],
    queryFn: async () => {
      const response = await api.get<Device>(`/devices/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceFormData) => {
      const response = await api.post<Device>("/devices/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });
}

export function useUpdateDevice(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceFormData) => {
      const response = await api.put<Device>(`/devices/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      queryClient.invalidateQueries({ queryKey: ["devices", id] });
    },
  });
}

export function useDeleteDevice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/devices/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["devices"] }),
  });
}

export function useTestConnection(id: number) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<TestConnectionResult>(`/devices/${id}/test_connection/`);
      return response.data;
    },
  });
}
```

`frontend/src/hooks/use-groups.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DeviceGroup, DeviceGroupFormData, PaginatedResponse } from "@/types";

export function useGroups(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["groups", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<DeviceGroup>>("/groups/", { params });
      return response.data;
    },
  });
}

export function useGroup(id: number) {
  return useQuery({
    queryKey: ["groups", id],
    queryFn: async () => {
      const response = await api.get<DeviceGroup>(`/groups/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceGroupFormData) => {
      const response = await api.post<DeviceGroup>("/groups/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useUpdateGroup(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: DeviceGroupFormData) => {
      const response = await api.put<DeviceGroup>(`/groups/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["groups", id] });
    },
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/groups/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["groups"] }),
  });
}

export function useRunGroupAudit(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await api.post(`/groups/${id}/run_audit/`);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audits"] }),
  });
}
```

`frontend/src/hooks/use-rules.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  SimpleRule, SimpleRuleFormData,
  CustomRule, CustomRuleFormData,
  PaginatedResponse,
} from "@/types";

// Simple Rules
export function useSimpleRules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["simple-rules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<SimpleRule>>("/rules/simple/", { params });
      return response.data;
    },
  });
}

export function useSimpleRule(id: number) {
  return useQuery({
    queryKey: ["simple-rules", id],
    queryFn: async () => {
      const response = await api.get<SimpleRule>(`/rules/simple/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateSimpleRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SimpleRuleFormData) => {
      const response = await api.post<SimpleRule>("/rules/simple/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simple-rules"] }),
  });
}

export function useUpdateSimpleRule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SimpleRuleFormData) => {
      const response = await api.put<SimpleRule>(`/rules/simple/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simple-rules"] });
      queryClient.invalidateQueries({ queryKey: ["simple-rules", id] });
    },
  });
}

export function useDeleteSimpleRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/rules/simple/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["simple-rules"] }),
  });
}

// Custom Rules
export function useCustomRules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["custom-rules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<CustomRule>>("/rules/custom/", { params });
      return response.data;
    },
  });
}

export function useCustomRule(id: number) {
  return useQuery({
    queryKey: ["custom-rules", id],
    queryFn: async () => {
      const response = await api.get<CustomRule>(`/rules/custom/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateCustomRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomRuleFormData) => {
      const response = await api.post<CustomRule>("/rules/custom/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["custom-rules"] }),
  });
}

export function useUpdateCustomRule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomRuleFormData) => {
      const response = await api.put<CustomRule>(`/rules/custom/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-rules"] });
      queryClient.invalidateQueries({ queryKey: ["custom-rules", id] });
    },
  });
}

export function useDeleteCustomRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/rules/custom/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["custom-rules"] }),
  });
}

export function useValidateCustomRule(id: number) {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post(`/rules/custom/${id}/validate/`);
      return response.data;
    },
  });
}
```

`frontend/src/hooks/use-audits.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AuditRun, AuditRunDetail, AuditStatus,
  DashboardSummary, PaginatedResponse,
} from "@/types";

const IN_PROGRESS_STATUSES: AuditStatus[] = ["pending", "fetching_config", "running_rules"];

export function useAuditRuns(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["audits", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditRun>>("/audits/", { params });
      return response.data;
    },
  });
}

export function useAuditRun(id: number) {
  return useQuery({
    queryKey: ["audits", id],
    queryFn: async () => {
      const response = await api.get<AuditRunDetail>(`/audits/${id}/`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && IN_PROGRESS_STATUSES.includes(data.status)) {
        return 3000; // Poll every 3s while in progress
      }
      return false;
    },
  });
}

export function useAuditConfig(id: number) {
  return useQuery({
    queryKey: ["audits", id, "config"],
    queryFn: async () => {
      const response = await api.get(`/audits/${id}/config/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateAudit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (deviceId: number) => {
      const response = await api.post<AuditRun>("/audits/", { device: deviceId });
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["audits"] }),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const response = await api.get<DashboardSummary>("/dashboard/summary/");
      return response.data;
    },
  });
}
```

`frontend/src/hooks/use-schedules.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AuditSchedule, AuditScheduleFormData, PaginatedResponse } from "@/types";

export function useSchedules(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["schedules", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<AuditSchedule>>("/schedules/", { params });
      return response.data;
    },
  });
}

export function useSchedule(id: number) {
  return useQuery({
    queryKey: ["schedules", id],
    queryFn: async () => {
      const response = await api.get<AuditSchedule>(`/schedules/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AuditScheduleFormData) => {
      const response = await api.post<AuditSchedule>("/schedules/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });
}

export function useUpdateSchedule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AuditScheduleFormData) => {
      const response = await api.put<AuditSchedule>(`/schedules/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schedules"] });
      queryClient.invalidateQueries({ queryKey: ["schedules", id] });
    },
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/schedules/${id}/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedules"] }),
  });
}
```

`frontend/src/hooks/use-settings.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SiteSettings } from "@/types";

export function useSiteSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const response = await api.get<SiteSettings>("/settings/");
      return response.data;
    },
  });
}

export function useUpdateSiteSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SiteSettings) => {
      const response = await api.patch<SiteSettings>("/settings/", data);
      return response.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });
}
```

`frontend/src/hooks/use-users.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { User, PaginatedResponse } from "@/types";

export function useUsers(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<User>>("/auth/users/", { params });
      return response.data;
    },
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ["users", id],
    queryFn: async () => {
      const response = await api.get<User>(`/auth/users/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useUpdateUser(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<User>) => {
      const response = await api.patch<User>(`/auth/users/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["users", id] });
    },
  });
}
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/hooks/
git commit -m "feat: add TanStack Query hooks for all API resources"
```

---

### Task 8: Router Setup with Protected Routes

**Files:**
- Create: `frontend/src/components/protected-route.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create protected route component**

`frontend/src/components/protected-route.tsx`:

```tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
```

**Step 2: Create App.tsx with full router**

`frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/hooks/use-auth";
import { ProtectedRoute } from "@/components/protected-route";
import { AppLayout } from "@/components/layout/app-layout";

// Auth pages
import { LoginPage } from "@/pages/auth/login";
import { SignupPage } from "@/pages/auth/signup";
import { PasswordResetPage } from "@/pages/auth/password-reset";

// App pages
import { DashboardPage } from "@/pages/dashboard";
import { DeviceListPage } from "@/pages/devices/list";
import { DeviceDetailPage } from "@/pages/devices/detail";
import { DeviceFormPage } from "@/pages/devices/form";
import { GroupListPage } from "@/pages/groups/list";
import { GroupDetailPage } from "@/pages/groups/detail";
import { GroupFormPage } from "@/pages/groups/form";
import { SimpleRuleListPage } from "@/pages/rules/simple-list";
import { SimpleRuleFormPage } from "@/pages/rules/simple-form";
import { CustomRuleListPage } from "@/pages/rules/custom-list";
import { CustomRuleFormPage } from "@/pages/rules/custom-form";
import { AuditListPage } from "@/pages/audits/list";
import { AuditDetailPage } from "@/pages/audits/detail";
import { ScheduleListPage } from "@/pages/schedules/list";
import { ScheduleFormPage } from "@/pages/schedules/form";
import { SettingsPage } from "@/pages/settings";
import { UserListPage } from "@/pages/users/list";
import { UserEditPage } from "@/pages/users/edit";
import { ProfilePage } from "@/pages/profile";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public auth routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/password-reset" element={<PasswordResetPage />} />

            {/* Protected app routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/devices" element={<DeviceListPage />} />
                <Route path="/devices/new" element={<DeviceFormPage />} />
                <Route path="/devices/:id" element={<DeviceDetailPage />} />
                <Route path="/devices/:id/edit" element={<DeviceFormPage />} />
                <Route path="/groups" element={<GroupListPage />} />
                <Route path="/groups/new" element={<GroupFormPage />} />
                <Route path="/groups/:id" element={<GroupDetailPage />} />
                <Route path="/groups/:id/edit" element={<GroupFormPage />} />
                <Route path="/rules/simple" element={<SimpleRuleListPage />} />
                <Route path="/rules/simple/new" element={<SimpleRuleFormPage />} />
                <Route path="/rules/simple/:id/edit" element={<SimpleRuleFormPage />} />
                <Route path="/rules/custom" element={<CustomRuleListPage />} />
                <Route path="/rules/custom/new" element={<CustomRuleFormPage />} />
                <Route path="/rules/custom/:id/edit" element={<CustomRuleFormPage />} />
                <Route path="/audits" element={<AuditListPage />} />
                <Route path="/audits/:id" element={<AuditDetailPage />} />
                <Route path="/schedules" element={<ScheduleListPage />} />
                <Route path="/schedules/new" element={<ScheduleFormPage />} />
                <Route path="/schedules/:id/edit" element={<ScheduleFormPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/users" element={<UserListPage />} />
                <Route path="/users/:id/edit" element={<UserEditPage />} />
                <Route path="/profile" element={<ProfilePage />} />
              </Route>
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

**Note:** This won't compile yet since the page components don't exist. That's expected — they'll be created in later tasks. For now, create stub exports for each page so the router compiles.

**Step 3: Create stub pages**

Create a stub for each page that just exports a placeholder component. Example pattern for each:

`frontend/src/pages/dashboard.tsx`:
```tsx
export function DashboardPage() {
  return <div className="p-6"><h1 className="text-2xl font-bold">Dashboard</h1></div>;
}
```

Create the same pattern for ALL pages listed in the router. Each file should export the named component matching the import in App.tsx.

Files to create:
- `frontend/src/pages/auth/login.tsx` → `LoginPage`
- `frontend/src/pages/auth/signup.tsx` → `SignupPage`
- `frontend/src/pages/auth/password-reset.tsx` → `PasswordResetPage`
- `frontend/src/pages/dashboard.tsx` → `DashboardPage`
- `frontend/src/pages/devices/list.tsx` → `DeviceListPage`
- `frontend/src/pages/devices/detail.tsx` → `DeviceDetailPage`
- `frontend/src/pages/devices/form.tsx` → `DeviceFormPage`
- `frontend/src/pages/groups/list.tsx` → `GroupListPage`
- `frontend/src/pages/groups/detail.tsx` → `GroupDetailPage`
- `frontend/src/pages/groups/form.tsx` → `GroupFormPage`
- `frontend/src/pages/rules/simple-list.tsx` → `SimpleRuleListPage`
- `frontend/src/pages/rules/simple-form.tsx` → `SimpleRuleFormPage`
- `frontend/src/pages/rules/custom-list.tsx` → `CustomRuleListPage`
- `frontend/src/pages/rules/custom-form.tsx` → `CustomRuleFormPage`
- `frontend/src/pages/audits/list.tsx` → `AuditListPage`
- `frontend/src/pages/audits/detail.tsx` → `AuditDetailPage`
- `frontend/src/pages/schedules/list.tsx` → `ScheduleListPage`
- `frontend/src/pages/schedules/form.tsx` → `ScheduleFormPage`
- `frontend/src/pages/settings.tsx` → `SettingsPage`
- `frontend/src/pages/users/list.tsx` → `UserListPage`
- `frontend/src/pages/users/edit.tsx` → `UserEditPage`
- `frontend/src/pages/profile.tsx` → `ProfilePage`

**Step 4: Create stub AppLayout**

`frontend/src/components/layout/app-layout.tsx`:
```tsx
import { Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

**Step 5: Verify it compiles**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npm run dev
```

Expected: App loads, shows "Dashboard" heading. Navigating to `/login` shows "Login" stub.

**Step 6: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/
git commit -m "feat: add router with protected routes and stub pages"
```

---

## Phase 3: Layout Shell

### Task 9: Sidebar Navigation

**Files:**
- Create: `frontend/src/components/layout/app-sidebar.tsx`
- Modify: `frontend/src/components/layout/app-layout.tsx`

**Step 1: Build the sidebar**

`frontend/src/components/layout/app-sidebar.tsx`:

```tsx
import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, Server, FolderTree, Shield, Code,
  ClipboardCheck, Clock, Settings, Users, LogOut, UserCircle,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, exact: true },
  { label: "Devices", href: "/devices", icon: Server },
  { label: "Groups", href: "/groups", icon: FolderTree },
  { label: "Simple Rules", href: "/rules/simple", icon: Shield },
  { label: "Custom Rules", href: "/rules/custom", icon: Code },
  { label: "Audits", href: "/audits", icon: ClipboardCheck },
  { label: "Schedules", href: "/schedules", icon: Clock },
  { label: "Settings", href: "/settings", icon: Settings },
];

const adminItems = [
  { label: "Users", href: "/users", icon: Users },
];

function isActive(pathname: string, href: string, exact?: boolean): boolean {
  if (exact) return pathname === href;
  return pathname.startsWith(href);
}

const roleBadgeVariant = (role: string) => {
  switch (role) {
    case "admin": return "destructive";
    case "editor": return "default";
    default: return "secondary";
  }
};

export function AppSidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  const allItems = user?.role === "admin"
    ? [...navItems, ...adminItems]
    : navItems;

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-56 flex-col bg-sidebar border-r border-sidebar-border">
      {/* Header */}
      <div className="flex h-14 items-center border-b border-sidebar-border px-5">
        <Link to="/" className="text-lg font-semibold text-white hover:no-underline">
          Netaudit
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2">
        <ul className="space-y-0.5 px-2">
          {allItems.map((item) => {
            const active = isActive(location.pathname, item.href, item.exact);
            return (
              <li key={item.href}>
                <Link
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:no-underline",
                    active
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User footer */}
      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-white truncate">
            {user?.username}
          </span>
          <Badge variant={roleBadgeVariant(user?.role || "viewer")} className="text-xs">
            {user?.role}
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/profile"
            className="text-xs text-sidebar-foreground hover:text-white hover:no-underline flex items-center gap-1"
          >
            <UserCircle className="h-3 w-3" />
            Profile
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="h-auto p-0 text-xs text-sidebar-foreground hover:text-white"
          >
            <LogOut className="h-3 w-3 mr-1" />
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );
}
```

**Step 2: Update AppLayout to include sidebar**

`frontend/src/components/layout/app-layout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />
      <div className="pl-56">
        <AppHeader />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/layout/
git commit -m "feat: add sidebar navigation with Lucide icons"
```

---

### Task 10: Header with Breadcrumbs and Command Palette Trigger

**Files:**
- Create: `frontend/src/components/layout/app-header.tsx`

**Step 1: Create the header**

`frontend/src/components/layout/app-header.tsx`:

```tsx
import { useLocation, Link } from "react-router-dom";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const routeLabels: Record<string, string> = {
  "": "Dashboard",
  devices: "Devices",
  groups: "Groups",
  rules: "Rules",
  simple: "Simple Rules",
  custom: "Custom Rules",
  audits: "Audits",
  schedules: "Schedules",
  settings: "Settings",
  users: "Users",
  profile: "Profile",
  new: "New",
  edit: "Edit",
};

export function AppHeader() {
  const location = useLocation();
  const { user } = useAuth();
  const segments = location.pathname.split("/").filter(Boolean);

  const breadcrumbs = segments.map((segment, index) => {
    const path = "/" + segments.slice(0, index + 1).join("/");
    const label = routeLabels[segment] || (segment.match(/^\d+$/) ? `#${segment}` : segment);
    const isLast = index === segments.length - 1;
    return { path, label, isLast };
  });

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center border-b border-border bg-background px-6">
      <Breadcrumb className="flex-1">
        <BreadcrumbList>
          <BreadcrumbItem>
            {segments.length === 0 ? (
              <BreadcrumbPage>Dashboard</BreadcrumbPage>
            ) : (
              <BreadcrumbLink asChild>
                <Link to="/">Dashboard</Link>
              </BreadcrumbLink>
            )}
          </BreadcrumbItem>
          {breadcrumbs.map((crumb) => (
            <span key={crumb.path} className="contents">
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {crumb.isLast ? (
                  <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink asChild>
                    <Link to={crumb.path}>{crumb.label}</Link>
                  </BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </span>
          ))}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-muted-foreground"
          onClick={() => {
            document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", metaKey: true }));
          }}
        >
          <Search className="h-4 w-4" />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>

        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-primary text-primary-foreground text-xs">
            {user?.username?.charAt(0).toUpperCase() || "U"}
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/layout/app-header.tsx
git commit -m "feat: add header with breadcrumbs and search trigger"
```

---

### Task 11: Command Palette

**Files:**
- Create: `frontend/src/components/layout/command-palette.tsx`
- Modify: `frontend/src/components/layout/app-layout.tsx`

**Step 1: Create command palette**

`frontend/src/components/layout/command-palette.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Server, FolderTree, Shield, Code,
  ClipboardCheck, Clock, Settings, Users, UserCircle,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useAuth } from "@/hooks/use-auth";

const pages = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, group: "Pages" },
  { label: "Devices", href: "/devices", icon: Server, group: "Pages" },
  { label: "Groups", href: "/groups", icon: FolderTree, group: "Pages" },
  { label: "Simple Rules", href: "/rules/simple", icon: Shield, group: "Pages" },
  { label: "Custom Rules", href: "/rules/custom", icon: Code, group: "Pages" },
  { label: "Audits", href: "/audits", icon: ClipboardCheck, group: "Pages" },
  { label: "Schedules", href: "/schedules", icon: Clock, group: "Pages" },
  { label: "Settings", href: "/settings", icon: Settings, group: "Pages" },
  { label: "Profile", href: "/profile", icon: UserCircle, group: "Pages" },
];

const adminPages = [
  { label: "Users", href: "/users", icon: Users, group: "Admin" },
];

const actions = [
  { label: "Add Device", href: "/devices/new", icon: Server, group: "Actions" },
  { label: "Add Group", href: "/groups/new", icon: FolderTree, group: "Actions" },
  { label: "Add Simple Rule", href: "/rules/simple/new", icon: Shield, group: "Actions" },
  { label: "Add Custom Rule", href: "/rules/custom/new", icon: Code, group: "Actions" },
  { label: "Add Schedule", href: "/schedules/new", icon: Clock, group: "Actions" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (href: string) => {
    setOpen(false);
    navigate(href);
  };

  const allPages = user?.role === "admin" ? [...pages, ...adminPages] : pages;

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Pages">
          {allPages.map((page) => (
            <CommandItem key={page.href} onSelect={() => runCommand(page.href)}>
              <page.icon className="mr-2 h-4 w-4" />
              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Actions">
          {actions.map((action) => (
            <CommandItem key={action.href} onSelect={() => runCommand(action.href)}>
              <action.icon className="mr-2 h-4 w-4" />
              {action.label}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
```

**Step 2: Add CommandPalette to AppLayout**

Update `frontend/src/components/layout/app-layout.tsx`:

```tsx
import { Outlet } from "react-router-dom";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { AppHeader } from "@/components/layout/app-header";
import { CommandPalette } from "@/components/layout/command-palette";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppSidebar />
      <div className="pl-56">
        <AppHeader />
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
```

**Step 3: Verify**

```bash
npm run dev
```

Expected: Cmd+K opens command palette dialog. Selecting an item navigates to that page.

**Step 4: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/layout/
git commit -m "feat: add command palette with Cmd+K navigation"
```

---

### Task 12: Badge Components

**Files:**
- Create: `frontend/src/components/badges.tsx`

**Step 1: Create badge components matching existing color palette**

`frontend/src/components/badges.tsx`:

```tsx
import { cn } from "@/lib/utils";
import type { AuditStatus, AuditTrigger, RuleOutcome, Severity } from "@/types";

interface StatusBadgeProps {
  status: AuditStatus;
  className?: string;
}

const statusStyles: Record<AuditStatus, string> = {
  pending: "bg-[#4a148c] text-[#ce93d8]",
  fetching_config: "bg-[#0d47a1] text-[#90caf9]",
  running_rules: "bg-[#0d47a1] text-[#90caf9]",
  completed: "bg-[#1b5e20] text-[#a5d6a7]",
  failed: "bg-[#b71c1c] text-[#ef9a9a]",
};

const statusLabels: Record<AuditStatus, string> = {
  pending: "Pending",
  fetching_config: "Fetching Config",
  running_rules: "Running Rules",
  completed: "Completed",
  failed: "Failed",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      statusStyles[status],
      className
    )}>
      {statusLabels[status]}
    </span>
  );
}

interface TriggerBadgeProps {
  trigger: AuditTrigger;
  className?: string;
}

const triggerStyles: Record<AuditTrigger, string> = {
  manual: "bg-[#37474f] text-[#b0bec5]",
  scheduled: "bg-[#1a237e] text-[#9fa8da]",
};

export function TriggerBadge({ trigger, className }: TriggerBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      triggerStyles[trigger],
      className
    )}>
      {trigger}
    </span>
  );
}

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

const severityStyles: Record<Severity, string> = {
  critical: "bg-[#b71c1c] text-[#ef9a9a]",
  high: "bg-[#e65100] text-[#ffcc80]",
  medium: "bg-[#f57f17] text-[#fff9c4]",
  low: "bg-[#1565c0] text-[#90caf9]",
  info: "bg-[#37474f] text-[#b0bec5]",
};

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      severityStyles[severity],
      className
    )}>
      {severity}
    </span>
  );
}

interface OutcomeBadgeProps {
  outcome: RuleOutcome;
  className?: string;
}

const outcomeStyles: Record<RuleOutcome, string> = {
  passed: "bg-[#1b5e20] text-[#a5d6a7]",
  failed: "bg-[#b71c1c] text-[#ef9a9a]",
  error: "bg-[#e65100] text-[#ffcc80]",
  skipped: "bg-[#37474f] text-[#b0bec5]",
};

export function OutcomeBadge({ outcome, className }: OutcomeBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      outcomeStyles[outcome],
      className
    )}>
      {outcome}
    </span>
  );
}

interface EnabledBadgeProps {
  enabled: boolean;
  className?: string;
}

export function EnabledBadge({ enabled, className }: EnabledBadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
      enabled ? "bg-[#1b5e20] text-[#a5d6a7]" : "bg-[#616161] text-[#bdbdbd]",
      className
    )}>
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/badges.tsx
git commit -m "feat: add badge components matching existing color palette"
```

---

### Task 13: Reusable Data Table Component

**Files:**
- Create: `frontend/src/components/data-table/data-table.tsx`
- Create: `frontend/src/components/data-table/data-table-pagination.tsx`

**Step 1: Install TanStack Table**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npm install @tanstack/react-table
```

**Step 2: Create data table**

`frontend/src/components/data-table/data-table.tsx`:

```tsx
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { DataTablePagination } from "./data-table-pagination";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  pageCount?: number;
  page?: number;
  onPageChange?: (page: number) => void;
  totalCount?: number;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  pageCount,
  page,
  onPageChange,
  totalCount,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
    manualPagination: true,
    pageCount: pageCount ?? -1,
  });

  return (
    <div>
      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {pageCount && pageCount > 1 && (
        <DataTablePagination
          page={page ?? 1}
          pageCount={pageCount}
          totalCount={totalCount ?? 0}
          onPageChange={onPageChange ?? (() => {})}
        />
      )}
    </div>
  );
}

// Sortable header helper
export function SortableHeader({ column, children }: { column: any; children: React.ReactNode }) {
  return (
    <button
      className="flex items-center gap-1 hover:text-foreground"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {children}
      <ArrowUpDown className="h-3 w-3" />
    </button>
  );
}
```

`frontend/src/components/data-table/data-table-pagination.tsx`:

```tsx
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

interface DataTablePaginationProps {
  page: number;
  pageCount: number;
  totalCount: number;
  onPageChange: (page: number) => void;
}

export function DataTablePagination({
  page,
  pageCount,
  totalCount,
  onPageChange,
}: DataTablePaginationProps) {
  return (
    <div className="flex items-center justify-between py-4">
      <p className="text-sm text-muted-foreground">
        {totalCount} total result{totalCount !== 1 ? "s" : ""}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm text-muted-foreground">
          Page {page} of {pageCount}
        </span>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8"
          onClick={() => onPageChange(pageCount)}
          disabled={page >= pageCount}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/data-table/
git commit -m "feat: add reusable data table with pagination"
```

---

### Task 14: Backend Config Change for SPA Auth

**Files:**
- Modify: `backend/config/settings/base.py`

**Step 1: Update REST_AUTH setting**

Change `JWT_AUTH_HTTPONLY` from `True` to `False` so the refresh token is returned in the JSON response body (required for a separate SPA):

```python
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_RETURN_EXPIRATION": True,
}
```

**Step 2: Add CORS credentials support in development settings**

In `backend/config/settings/development.py`, add:

```python
CORS_ALLOW_CREDENTIALS = True
```

**Step 3: Verify Django still starts**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python manage.py runserver --settings=config.settings.development
```

Expected: Server starts without errors.

**Step 4: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add backend/config/settings/
git commit -m "feat: configure JWT for SPA auth (httponly=false, cors credentials)"
```

---

## Phase 4: Auth Pages

### Task 15: Login Page

**Files:**
- Modify: `frontend/src/pages/auth/login.tsx`

**Step 1: Build the login page preserving existing auth card design**

`frontend/src/pages/auth/login.tsx`:

```tsx
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
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
    } catch (err: any) {
      setError(err.response?.data?.non_field_errors?.[0] || "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "#1a1a2e" }}>
      <div className="flex max-w-[900px] w-full min-h-[520px] rounded-2xl overflow-hidden shadow-2xl">
        {/* Brand panel */}
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
                  placeholder="Username"
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
                >
                  {showPassword ? "Hide" : "Show"}
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

            <div className="mt-6 text-center text-sm text-[#888]">
              <p>
                Don't have an account?{" "}
                <Link to="/signup" className="text-[#64b5f6] hover:underline">
                  Create one
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/auth/login.tsx
git commit -m "feat: add login page matching existing auth card design"
```

---

### Task 16: Signup and Password Reset Pages

**Files:**
- Modify: `frontend/src/pages/auth/signup.tsx`
- Modify: `frontend/src/pages/auth/password-reset.tsx`

**Step 1: Create signup page**

Follow the exact same visual pattern as the login page (brand panel + form panel). The signup form fields are: username, email, password1, password2. Use the `register` function from `useAuth`.

**Step 2: Create password reset page**

Simpler form with just email field. Submit to `/api/v1/auth/password/reset/`. Same visual wrapper (brand panel + form panel).

**Step 3: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/auth/
git commit -m "feat: add signup and password reset pages"
```

---

## Phase 5: App Pages

### Task 17: Dashboard Page

**Files:**
- Modify: `frontend/src/pages/dashboard.tsx`

**Step 1: Build the dashboard**

`frontend/src/pages/dashboard.tsx`:

```tsx
import { Link } from "react-router-dom";
import { Server, ClipboardCheck, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDashboardSummary, useAuditRuns } from "@/hooks/use-audits";
import { StatusBadge, TriggerBadge } from "@/components/badges";

export function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: recentAudits, isLoading: auditsLoading } = useAuditRuns({
    ordering: "-created_at",
    page_size: "10",
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Devices
            </CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-white">
              {summaryLoading ? "—" : summary?.device_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Recent Audits (24h)
            </CardTitle>
            <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-white">
              {summaryLoading ? "—" : summary?.recent_audit_count ?? 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pass Rate (7d)
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-white">
              {summaryLoading ? "—" : `${Math.round((summary?.pass_rate ?? 0) * 100)}%`}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent audits table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Audits</CardTitle>
        </CardHeader>
        <CardContent>
          {auditsLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentAudits?.results.map((audit) => (
                  <TableRow key={audit.id}>
                    <TableCell>
                      <Link to={`/audits/${audit.id}`} className="text-primary hover:underline">
                        {audit.device_name}
                      </Link>
                    </TableCell>
                    <TableCell><StatusBadge status={audit.status} /></TableCell>
                    <TableCell><TriggerBadge trigger={audit.trigger} /></TableCell>
                    <TableCell className="text-sm">
                      {audit.summary
                        ? `${audit.summary.passed}P / ${audit.summary.failed}F`
                        : "—"
                      }
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(audit.created_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/dashboard.tsx
git commit -m "feat: add dashboard page with summary cards and recent audits"
```

---

### Task 18: Device Pages (List, Detail, Form)

**Files:**
- Modify: `frontend/src/pages/devices/list.tsx`
- Modify: `frontend/src/pages/devices/detail.tsx`
- Modify: `frontend/src/pages/devices/form.tsx`

**Step 1: Device list page**

Build a list page with:
- Page header with "Devices" title and "Add Device" button (linked to `/devices/new`)
- DataTable with columns: Name (link to detail), Hostname, Endpoint, Enabled (badge), Groups count, Actions (Edit/Delete buttons)
- Delete uses `useDeleteDevice` mutation with a shadcn `AlertDialog` for confirmation
- Pagination using query params `?page=N`

**Step 2: Device detail page**

Build a detail page with:
- Page header with device name and Edit/Delete/Test Connection buttons
- Card with detail grid: Name, Hostname, API Endpoint, Effective Endpoint, Enabled, Created, Updated
- Card for headers table (key-value pairs)
- Card for group memberships (list of group names with links)
- Test Connection button triggers `useTestConnection` mutation and shows result

**Step 3: Device form page**

Build a create/edit form with:
- Check `useParams().id` — if present, load device with `useDevice(id)` and pre-fill form
- Form fields: name (input), hostname (input), api_endpoint (input), enabled (checkbox), groups (multi-select)
- Dynamic headers section: list of key/value pairs with Add/Remove buttons
- Submit calls `useCreateDevice` or `useUpdateDevice`
- On success, navigate to `/devices`
- Zod schema for validation

**Step 4: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/devices/
git commit -m "feat: add device list, detail, and form pages"
```

---

### Task 19: Group Pages (List, Detail, Form)

**Files:**
- Modify: `frontend/src/pages/groups/list.tsx`
- Modify: `frontend/src/pages/groups/detail.tsx`
- Modify: `frontend/src/pages/groups/form.tsx`

Follow the same patterns as device pages:
- **List:** DataTable with columns: Name (link), Description (truncated), Device Count, Actions. "Add Group" button.
- **Detail:** Group info card + member devices table + "Run Audit" button (triggers `useRunGroupAudit`).
- **Form:** name (input), description (textarea), devices (multi-select from device list).

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/groups/
git commit -m "feat: add group list, detail, and form pages"
```

---

### Task 20: Simple Rule Pages (List, Form)

**Files:**
- Modify: `frontend/src/pages/rules/simple-list.tsx`
- Modify: `frontend/src/pages/rules/simple-form.tsx`

- **List:** DataTable columns: Name, Rule Type, Pattern (truncated), Severity (badge), Enabled (badge), Scope (device or group name), Actions.
- **Form:** name, description, rule_type (select: must_contain, must_not_contain, regex_match, regex_no_match), pattern (textarea), severity (select), enabled (checkbox), device (select, optional), group (select, optional).

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/rules/simple-list.tsx frontend/src/pages/rules/simple-form.tsx
git commit -m "feat: add simple rule list and form pages"
```

---

### Task 21: Custom Rule Pages (List, Form)

**Files:**
- Modify: `frontend/src/pages/rules/custom-list.tsx`
- Modify: `frontend/src/pages/rules/custom-form.tsx`

- **List:** DataTable columns: Name, Filename, Severity (badge), Enabled (badge), Scope, Actions.
- **Form:** name, description, filename (with validation: must start with `test_` and end with `.py`), content (monospace textarea, tall), severity (select), enabled (checkbox), device (select), group (select). Include "Validate" button that calls `useValidateCustomRule`.

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/rules/custom-list.tsx frontend/src/pages/rules/custom-form.tsx
git commit -m "feat: add custom rule list and form pages"
```

---

### Task 22: Audit Pages (List, Detail with Polling)

**Files:**
- Modify: `frontend/src/pages/audits/list.tsx`
- Modify: `frontend/src/pages/audits/detail.tsx`

- **List:** DataTable columns: Device (link to audit detail), Status (badge), Trigger (badge), Summary (passed/failed counts), Date. No create/edit actions from this list (audits are created from device/group detail pages).

- **Detail:**
  - Audit info card: device name (link), status (badge with spinner if in-progress), trigger, timestamps
  - Results table: Rule Name, Outcome (badge), Severity (badge), Duration, Message
  - Config snapshot viewer (collapsible card with `<pre>` monospace block)
  - Error message display if status is "failed"
  - **Polling:** `useAuditRun(id)` already has `refetchInterval` that polls every 3s while in-progress

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/audits/
git commit -m "feat: add audit list and detail pages with real-time polling"
```

---

### Task 23: Schedule Pages (List, Form)

**Files:**
- Modify: `frontend/src/pages/schedules/list.tsx`
- Modify: `frontend/src/pages/schedules/form.tsx`

- **List:** DataTable columns: Name, Device name, Cron Expression, Enabled (badge), Actions.
- **Form:** name, device (select), cron_expression (input with help text showing cron format), enabled (checkbox).

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/schedules/
git commit -m "feat: add schedule list and form pages"
```

---

### Task 24: Settings Page

**Files:**
- Modify: `frontend/src/pages/settings.tsx`

Build a simple settings page:
- Card with form containing single field: `default_api_endpoint` (URL input)
- Help text: "Base URL for device API endpoints. Each device's endpoint will be constructed as {base_url}/{device_name}"
- Submit calls `useUpdateSiteSettings`
- Success message toast or inline

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/settings.tsx
git commit -m "feat: add settings page"
```

---

### Task 25: User Management Pages (Admin Only)

**Files:**
- Modify: `frontend/src/pages/users/list.tsx`
- Modify: `frontend/src/pages/users/edit.tsx`

- **List:** DataTable columns: Username, Email, Role (badge), API Enabled (badge), Joined Date. Edit action only. Guard: redirect non-admins to `/`.
- **Edit:** Form with role (select: admin, editor, viewer), is_api_enabled (checkbox). Username and email shown as read-only.

**Note:** The user management API endpoint may need to be confirmed/added. Check if `GET /api/v1/auth/users/` exists; if not, a backend ViewSet for User listing/editing will need to be added. The accounts app may already have this — check `accounts/urls.py`.

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/users/
git commit -m "feat: add user management pages (admin only)"
```

---

### Task 26: Profile Page

**Files:**
- Modify: `frontend/src/pages/profile.tsx`

Build a profile page:
- Card showing: username, email, role (badge), member since date
- Password change section with current_password, new_password1, new_password2 fields
- Submit password change to `/api/v1/auth/password/change/`

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/pages/profile.tsx
git commit -m "feat: add profile page with password change"
```

---

## Phase 6: Polish & Verification

### Task 27: Delete Confirmation Dialog

**Files:**
- Create: `frontend/src/components/delete-dialog.tsx`

Create a reusable delete confirmation dialog using shadcn `AlertDialog`:

```tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

interface DeleteDialogProps {
  name: string;
  onConfirm: () => void;
  loading?: boolean;
}

export function DeleteDialog({ name, onConfirm, loading }: DeleteDialogProps) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive" size="sm">
          <Trash2 className="h-4 w-4" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete "{name}"?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently delete this item.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={loading}>
            {loading ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/components/delete-dialog.tsx
git commit -m "feat: add reusable delete confirmation dialog"
```

---

### Task 28: Toast Notifications

**Files:**
- Install and configure shadcn toast/sonner component

**Step 1: Install sonner (shadcn's toast solution)**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx shadcn@latest add sonner
```

**Step 2: Add Toaster to App.tsx**

Add `<Toaster />` from sonner inside the providers in `App.tsx`.

**Step 3: Use in mutations**

Add `toast.success("Device created")` / `toast.error("Failed to delete")` calls to mutation `onSuccess`/`onError` callbacks across all form pages.

**Commit:**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/src/
git commit -m "feat: add toast notifications for mutations"
```

---

### Task 29: Final Verification and Cleanup

**Step 1: Run TypeScript check**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx tsc --noEmit
```

Fix any type errors.

**Step 2: Run build**

```bash
npm run build
```

Fix any build errors.

**Step 3: Manual smoke test**

With Django API running on :8000 and Vite on :5173:
1. Navigate to login page
2. Log in with existing credentials
3. Verify dashboard loads with data
4. Navigate through all sidebar links
5. Test Cmd+K command palette
6. Create/edit/delete a device
7. Run an audit and watch polling
8. Verify breadcrumbs update correctly

**Step 4: Clean up any remaining Vite template files**

Remove any files from the original Vite scaffold that aren't used:
- `frontend/src/assets/react.svg`
- `frontend/public/vite.svg`

**Step 5: Commit**

```bash
cd /Users/aaronroth/Documents/netaudit
git add frontend/
git commit -m "chore: cleanup and verify frontend build"
```

---

## Summary

**Total tasks:** 29
**Phases:** 6 (Scaffolding → Foundation → Layout Shell → Auth Pages → App Pages → Polish)

**Key dependencies:**
- Tasks 1-3 must run sequentially (project setup)
- Task 14 (backend config) can run in parallel with frontend tasks
- Tasks 4-8 are foundation and must complete before page tasks
- Tasks 9-13 (layout components) must complete before page tasks
- Tasks 17-26 (pages) can be parallelized after layout is ready
- Tasks 27-29 (polish) run after all pages are built

**Backend changes required:**
- Task 14: `JWT_AUTH_HTTPONLY: False` in settings
- Task 25: May need a User list/edit API if one doesn't exist
