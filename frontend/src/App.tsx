import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
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
      <Toaster richColors position="top-right" />
    </QueryClientProvider>
  );
}
