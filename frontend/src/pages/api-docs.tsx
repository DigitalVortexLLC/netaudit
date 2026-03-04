import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Lock,
  Globe,
  Copy,
  Check,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

interface Field {
  name: string;
  type: string;
  description: string;
  readOnly?: boolean;
  writeOnly?: boolean;
  required?: boolean;
}

interface Endpoint {
  method: HttpMethod;
  path: string;
  summary: string;
  description?: string;
  auth?: boolean;
  requestBody?: Field[];
  responseFields?: Field[];
}

interface EndpointSection {
  title: string;
  basePath: string;
  description: string;
  endpoints: Endpoint[];
}

/* ------------------------------------------------------------------ */
/*  API data                                                           */
/* ------------------------------------------------------------------ */

const BASE_URL = "/api/v1";

const sections: EndpointSection[] = [
  /* ── Authentication ─────────────────────────────────────────────── */
  {
    title: "Authentication",
    basePath: "/auth",
    description:
      "Register, log in, manage tokens, and change passwords. All protected endpoints require a Bearer token in the Authorization header.",
    endpoints: [
      {
        method: "POST",
        path: "/auth/login/",
        summary: "Log in",
        description: "Authenticate with username and password. Returns JWT access and refresh tokens.",
        auth: false,
        requestBody: [
          { name: "username", type: "string", description: "Account username", required: true },
          { name: "password", type: "string", description: "Account password", required: true },
        ],
        responseFields: [
          { name: "access", type: "string", description: "Short-lived JWT access token" },
          { name: "refresh", type: "string", description: "Long-lived JWT refresh token" },
          { name: "user", type: "object", description: "Authenticated user details" },
        ],
      },
      {
        method: "POST",
        path: "/auth/logout/",
        summary: "Log out",
        description: "Invalidate the current session.",
        auth: true,
      },
      {
        method: "POST",
        path: "/auth/register/",
        summary: "Register a new account",
        description: "Create a new user account. Public registration must be enabled in site settings.",
        auth: false,
        requestBody: [
          { name: "username", type: "string", description: "Desired username", required: true },
          { name: "email", type: "string", description: "Email address", required: true },
          { name: "password1", type: "string", description: "Password", required: true },
          { name: "password2", type: "string", description: "Password confirmation", required: true },
        ],
      },
      {
        method: "POST",
        path: "/auth/token/refresh/",
        summary: "Refresh access token",
        description: "Exchange a valid refresh token for a new access/refresh pair.",
        auth: false,
        requestBody: [
          { name: "refresh", type: "string", description: "Current refresh token", required: true },
        ],
        responseFields: [
          { name: "access", type: "string", description: "New access token" },
          { name: "refresh", type: "string", description: "New refresh token" },
        ],
      },
      {
        method: "POST",
        path: "/auth/password/change/",
        summary: "Change password",
        description: "Change the password for the currently authenticated user.",
        auth: true,
        requestBody: [
          { name: "old_password", type: "string", description: "Current password", required: true },
          { name: "new_password1", type: "string", description: "New password", required: true },
          { name: "new_password2", type: "string", description: "New password confirmation", required: true },
        ],
      },
    ],
  },

  /* ── Users ──────────────────────────────────────────────────────── */
  {
    title: "Users",
    basePath: "/auth/users",
    description: "Manage user accounts. Admin role required.",
    endpoints: [
      {
        method: "GET",
        path: "/auth/users/",
        summary: "List users",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "User ID" },
          { name: "username", type: "string", description: "Username" },
          { name: "email", type: "string", description: "Email address" },
          { name: "role", type: "string", description: "Role: admin, editor, or viewer" },
          { name: "is_api_enabled", type: "boolean", description: "Whether API access is enabled" },
          { name: "is_active", type: "boolean", description: "Whether the account is active" },
          { name: "date_joined", type: "datetime", description: "Account creation date" },
        ],
      },
      {
        method: "GET",
        path: "/auth/users/{id}/",
        summary: "Get user details",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/auth/users/{id}/",
        summary: "Update user",
        description: "Update a user's role or API access. Only admin-writable fields: role, is_api_enabled, is_active.",
        auth: true,
        requestBody: [
          { name: "role", type: "string", description: "New role: admin, editor, or viewer" },
          { name: "is_api_enabled", type: "boolean", description: "Enable/disable API access" },
          { name: "is_active", type: "boolean", description: "Enable/disable account" },
        ],
      },
      {
        method: "PATCH",
        path: "/auth/users/{id}/toggle_active/",
        summary: "Toggle user active status",
        description: "Flip the is_active flag for the user.",
        auth: true,
      },
    ],
  },

  /* ── Devices ────────────────────────────────────────────────────── */
  {
    title: "Devices",
    basePath: "/devices",
    description: "Manage network devices that can be audited.",
    endpoints: [
      {
        method: "GET",
        path: "/devices/",
        summary: "List devices",
        description: "Supports filtering by enabled, search by name/hostname, ordering by name/created_at. Paginated.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Device ID" },
          { name: "name", type: "string", description: "Device name (unique)" },
          { name: "hostname", type: "string", description: "Device hostname or IP" },
          { name: "api_endpoint", type: "string | null", description: "Custom API endpoint URL" },
          { name: "effective_api_endpoint", type: "string", description: "Resolved API endpoint (device or site default)", readOnly: true },
          { name: "enabled", type: "boolean", description: "Whether the device is enabled" },
          { name: "headers", type: "array", description: "Custom HTTP headers [{key, value}]" },
          { name: "groups", type: "integer[]", description: "IDs of groups this device belongs to" },
          { name: "config_source", type: "object | null", description: "Config source configuration (SSH)" },
          { name: "last_fetched_config", type: "string", description: "Last fetched config text", readOnly: true },
          { name: "config_fetched_at", type: "datetime | null", description: "When config was last fetched", readOnly: true },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/devices/",
        summary: "Create device",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Unique device name", required: true },
          { name: "hostname", type: "string", description: "Hostname or IP address", required: true },
          { name: "api_endpoint", type: "string", description: "Custom API endpoint URL" },
          { name: "enabled", type: "boolean", description: "Enable this device (default: true)" },
          { name: "headers", type: "array", description: 'Custom HTTP headers: [{key: "X-Token", value: "abc"}]' },
          { name: "groups", type: "integer[]", description: "Group IDs to assign" },
          {
            name: "config_source",
            type: "object | null",
            description: 'SSH config source: {source_type: "ssh", netmiko_device_type: 1, hostname: "...", username: "...", password: "..."}',
          },
        ],
      },
      {
        method: "GET",
        path: "/devices/{id}/",
        summary: "Get device details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/devices/{id}/",
        summary: "Replace device",
        description: "Full update of a device. All required fields must be provided.",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/devices/{id}/",
        summary: "Partial update device",
        description: "Update individual fields on a device.",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/devices/{id}/",
        summary: "Delete device",
        auth: true,
      },
      {
        method: "POST",
        path: "/devices/{id}/test_connection/",
        summary: "Test device connection",
        description: "Send a test HTTP GET to the device's API endpoint and return the result.",
        auth: true,
        responseFields: [
          { name: "success", type: "boolean", description: "Whether the connection succeeded" },
          { name: "status_code", type: "integer", description: "HTTP status code from the device" },
          { name: "content_length", type: "integer", description: "Response content length in bytes" },
          { name: "error", type: "string", description: "Error message if failed" },
        ],
      },
      {
        method: "POST",
        path: "/devices/{id}/fetch_config/",
        summary: "Fetch device config",
        description: "Queue a background task to fetch the device's running configuration via its config source.",
        auth: true,
        responseFields: [
          { name: "status", type: "string", description: '"queued"' },
          { name: "device_id", type: "integer", description: "Device ID" },
        ],
      },
    ],
  },

  /* ── Device Groups ──────────────────────────────────────────────── */
  {
    title: "Device Groups",
    basePath: "/groups",
    description: "Organize devices into groups for batch operations.",
    endpoints: [
      {
        method: "GET",
        path: "/groups/",
        summary: "List groups",
        description: "Searchable by name and description.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Group ID" },
          { name: "name", type: "string", description: "Group name (unique)" },
          { name: "description", type: "string", description: "Group description" },
          { name: "devices", type: "integer[]", description: "Device IDs in this group" },
          { name: "device_count", type: "integer", description: "Number of devices", readOnly: true },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/groups/",
        summary: "Create group",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Unique group name", required: true },
          { name: "description", type: "string", description: "Group description" },
          { name: "devices", type: "integer[]", description: "Device IDs to add" },
        ],
      },
      {
        method: "GET",
        path: "/groups/{id}/",
        summary: "Get group details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/groups/{id}/",
        summary: "Replace group",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/groups/{id}/",
        summary: "Partial update group",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/groups/{id}/",
        summary: "Delete group",
        auth: true,
      },
      {
        method: "POST",
        path: "/groups/{id}/run_audit/",
        summary: "Run audit on all group devices",
        description: "Trigger an audit for every enabled device in the group.",
        auth: true,
        responseFields: [
          { name: "audits_started", type: "integer", description: "Number of audits queued" },
          { name: "group", type: "string", description: "Group name" },
        ],
      },
    ],
  },

  /* ── Simple Rules ───────────────────────────────────────────────── */
  {
    title: "Simple Rules",
    basePath: "/rules/simple",
    description:
      "Declarative rules that check device configs against string or regex patterns.",
    endpoints: [
      {
        method: "GET",
        path: "/rules/simple/",
        summary: "List simple rules",
        description: "Filterable by device, group, enabled, severity, rule_type. Searchable by name, description, pattern.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Rule ID" },
          { name: "name", type: "string", description: "Rule name" },
          { name: "description", type: "string", description: "Rule description" },
          { name: "rule_type", type: "string", description: "must_contain, must_not_contain, regex_match, or regex_no_match" },
          { name: "pattern", type: "string", description: "String literal or regex pattern" },
          { name: "severity", type: "string", description: "critical, high, medium, low, or info" },
          { name: "enabled", type: "boolean", description: "Whether the rule is enabled" },
          { name: "device", type: "integer | null", description: "Target device ID (null = all devices)" },
          { name: "group", type: "integer | null", description: "Target group ID (null = not group-scoped)" },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/rules/simple/",
        summary: "Create simple rule",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Rule name", required: true },
          { name: "description", type: "string", description: "Rule description" },
          { name: "rule_type", type: "string", description: "must_contain | must_not_contain | regex_match | regex_no_match", required: true },
          { name: "pattern", type: "string", description: "String literal or regex pattern", required: true },
          { name: "severity", type: "string", description: "critical | high | medium | low | info (default: medium)" },
          { name: "enabled", type: "boolean", description: "Enable this rule (default: true)" },
          { name: "device", type: "integer | null", description: "Target device ID (null = all devices)" },
          { name: "group", type: "integer | null", description: "Target group ID" },
        ],
      },
      {
        method: "GET",
        path: "/rules/simple/{id}/",
        summary: "Get simple rule details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/rules/simple/{id}/",
        summary: "Replace simple rule",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/rules/simple/{id}/",
        summary: "Partial update simple rule",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/rules/simple/{id}/",
        summary: "Delete simple rule",
        auth: true,
      },
    ],
  },

  /* ── Custom Rules ───────────────────────────────────────────────── */
  {
    title: "Custom Rules",
    basePath: "/rules/custom",
    description:
      "User-supplied pytest files executed during audit runs. Content is validated via AST checks.",
    endpoints: [
      {
        method: "GET",
        path: "/rules/custom/",
        summary: "List custom rules",
        description: "Filterable by device, group, enabled, severity. Searchable by name, description, filename.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Rule ID" },
          { name: "name", type: "string", description: "Rule name" },
          { name: "description", type: "string", description: "Rule description" },
          { name: "filename", type: "string", description: "Test filename (must start with test_ and end with .py)" },
          { name: "content", type: "string", description: "Python source code of the pytest test" },
          { name: "severity", type: "string", description: "critical, high, medium, low, or info" },
          { name: "enabled", type: "boolean", description: "Whether the rule is enabled" },
          { name: "device", type: "integer | null", description: "Target device ID" },
          { name: "group", type: "integer | null", description: "Target group ID" },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/rules/custom/",
        summary: "Create custom rule",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Rule name", required: true },
          { name: "description", type: "string", description: "Rule description" },
          { name: "filename", type: "string", description: "Test filename (e.g. test_ntp.py)", required: true },
          { name: "content", type: "string", description: "Python pytest source code", required: true },
          { name: "severity", type: "string", description: "critical | high | medium | low | info" },
          { name: "enabled", type: "boolean", description: "Enable this rule (default: true)" },
          { name: "device", type: "integer | null", description: "Target device ID" },
          { name: "group", type: "integer | null", description: "Target group ID" },
        ],
      },
      {
        method: "GET",
        path: "/rules/custom/{id}/",
        summary: "Get custom rule details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/rules/custom/{id}/",
        summary: "Replace custom rule",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/rules/custom/{id}/",
        summary: "Partial update custom rule",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/rules/custom/{id}/",
        summary: "Delete custom rule",
        auth: true,
      },
      {
        method: "POST",
        path: "/rules/custom/{id}/validate/",
        summary: "Validate saved rule",
        description: "Run AST security checks on a saved custom rule.",
        auth: true,
        responseFields: [
          { name: "valid", type: "boolean", description: "Whether the rule passed validation" },
          { name: "errors", type: "array", description: "Validation errors [{line, message}]" },
        ],
      },
      {
        method: "POST",
        path: "/rules/custom/validate-content/",
        summary: "Validate rule content",
        description: "Validate arbitrary Python content without saving it first.",
        auth: true,
        requestBody: [
          { name: "content", type: "string", description: "Python source code to validate", required: true },
        ],
        responseFields: [
          { name: "valid", type: "boolean", description: "Whether the content passed validation" },
          { name: "errors", type: "array", description: "Validation errors [{line, message}]" },
        ],
      },
      {
        method: "POST",
        path: "/rules/custom/test-run/",
        summary: "Test-run a custom rule",
        description: "Execute a custom rule against a device's config and return the results without creating an audit.",
        auth: true,
        requestBody: [
          { name: "content", type: "string", description: "Python pytest source code", required: true },
          { name: "device_id", type: "integer", description: "Device to test against", required: true },
        ],
        responseFields: [
          { name: "passed", type: "boolean", description: "Whether all tests passed" },
          { name: "output", type: "string", description: "Test output text" },
          { name: "duration", type: "number", description: "Execution time in seconds" },
          { name: "summary", type: "object", description: "Test summary counts" },
        ],
      },
    ],
  },

  /* ── Audit Runs ─────────────────────────────────────────────────── */
  {
    title: "Audit Runs",
    basePath: "/audits",
    description:
      "Trigger, list, and inspect audit runs. Each audit run fetches a device's config and executes all matching rules against it.",
    endpoints: [
      {
        method: "GET",
        path: "/audits/",
        summary: "List audit runs",
        description: "Filterable by device, status, trigger, tags. Paginated.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Audit run ID" },
          { name: "device", type: "integer", description: "Device ID" },
          { name: "device_name", type: "string", description: "Device name" },
          { name: "status", type: "string", description: "pending, fetching_config, running_rules, completed, or failed" },
          { name: "trigger", type: "string", description: "manual or scheduled" },
          { name: "summary", type: "object | null", description: "{passed, failed, error} counts" },
          { name: "started_at", type: "datetime | null", description: "When the audit started" },
          { name: "completed_at", type: "datetime | null", description: "When the audit finished" },
          { name: "created_at", type: "datetime", description: "Creation timestamp" },
          { name: "tags", type: "array", description: "Tags attached to this audit" },
        ],
      },
      {
        method: "POST",
        path: "/audits/",
        summary: "Trigger a new audit",
        description: "Queue an audit for the specified device.",
        auth: true,
        requestBody: [
          { name: "device", type: "integer", description: "Device ID to audit", required: true },
        ],
      },
      {
        method: "GET",
        path: "/audits/{id}/",
        summary: "Get audit run details",
        description: "Returns full audit details including results, tags, and comments.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Audit run ID" },
          { name: "device", type: "integer", description: "Device ID" },
          { name: "device_name", type: "string", description: "Device name" },
          { name: "status", type: "string", description: "Audit status" },
          { name: "trigger", type: "string", description: "Trigger type" },
          { name: "summary", type: "object | null", description: "Result summary" },
          { name: "error_message", type: "string", description: "Error details if failed" },
          { name: "config_fetched_at", type: "datetime | null", description: "When config was fetched" },
          { name: "results", type: "array", description: "Array of rule results" },
          { name: "tags", type: "array", description: "Tags attached to this audit" },
          { name: "comments", type: "array", description: "Comments on this audit" },
        ],
      },
      {
        method: "GET",
        path: "/audits/{id}/results/",
        summary: "Get rule results",
        description: "Return all individual rule results for this audit.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Result ID" },
          { name: "audit_run", type: "integer", description: "Audit run ID" },
          { name: "simple_rule", type: "integer | null", description: "Simple rule ID" },
          { name: "custom_rule", type: "integer | null", description: "Custom rule ID" },
          { name: "rule_name", type: "string | null", description: "Rule name" },
          { name: "test_node_id", type: "string", description: "Pytest node ID" },
          { name: "outcome", type: "string", description: "passed, failed, error, or skipped" },
          { name: "message", type: "string", description: "Result message" },
          { name: "duration", type: "number | null", description: "Execution time in seconds" },
          { name: "severity", type: "string", description: "Rule severity" },
        ],
      },
      {
        method: "GET",
        path: "/audits/{id}/config/",
        summary: "Get config snapshot",
        description: "Return the config snapshot captured during the audit.",
        auth: true,
        responseFields: [
          { name: "config", type: "string", description: "Device configuration text" },
        ],
      },
      {
        method: "GET",
        path: "/audits/{id}/tags/",
        summary: "List audit tags",
        auth: true,
      },
      {
        method: "POST",
        path: "/audits/{id}/tags/",
        summary: "Add tag to audit",
        auth: true,
        requestBody: [
          { name: "tag_id", type: "integer", description: "Existing tag ID (use tag_id or name)" },
          { name: "name", type: "string", description: "Tag name (creates if needed)" },
        ],
      },
      {
        method: "DELETE",
        path: "/audits/{id}/tags/{tag_id}/",
        summary: "Remove tag from audit",
        auth: true,
      },
      {
        method: "GET",
        path: "/audits/{id}/comments/",
        summary: "List audit comments",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Comment ID" },
          { name: "author", type: "integer", description: "Author user ID" },
          { name: "author_name", type: "string", description: "Author username" },
          { name: "content", type: "string", description: "Comment text" },
          { name: "created_at", type: "datetime", description: "Creation timestamp" },
          { name: "updated_at", type: "datetime", description: "Last update timestamp" },
        ],
      },
      {
        method: "POST",
        path: "/audits/{id}/comments/",
        summary: "Add comment to audit",
        auth: true,
        requestBody: [
          { name: "content", type: "string", description: "Comment text", required: true },
        ],
      },
      {
        method: "PUT",
        path: "/audits/{id}/comments/{comment_id}/",
        summary: "Update a comment",
        description: "Only the comment's author can update it.",
        auth: true,
        requestBody: [
          { name: "content", type: "string", description: "Updated comment text", required: true },
        ],
      },
      {
        method: "DELETE",
        path: "/audits/{id}/comments/{comment_id}/",
        summary: "Delete a comment",
        description: "Only the comment's author can delete it.",
        auth: true,
      },
    ],
  },

  /* ── Schedules ──────────────────────────────────────────────────── */
  {
    title: "Audit Schedules",
    basePath: "/schedules",
    description: "Create cron-based schedules to automatically audit devices.",
    endpoints: [
      {
        method: "GET",
        path: "/schedules/",
        summary: "List schedules",
        description: "Filterable by device and enabled.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Schedule ID" },
          { name: "device", type: "integer", description: "Device ID" },
          { name: "name", type: "string", description: "Schedule name" },
          { name: "cron_expression", type: "string", description: 'Cron expression (e.g. "0 */6 * * *")' },
          { name: "enabled", type: "boolean", description: "Whether the schedule is active" },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/schedules/",
        summary: "Create schedule",
        auth: true,
        requestBody: [
          { name: "device", type: "integer", description: "Device ID", required: true },
          { name: "name", type: "string", description: "Schedule name", required: true },
          { name: "cron_expression", type: "string", description: 'Cron expression (e.g. "0 */6 * * *")', required: true },
          { name: "enabled", type: "boolean", description: "Enable this schedule (default: true)" },
        ],
      },
      {
        method: "GET",
        path: "/schedules/{id}/",
        summary: "Get schedule details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/schedules/{id}/",
        summary: "Replace schedule",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/schedules/{id}/",
        summary: "Partial update schedule",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/schedules/{id}/",
        summary: "Delete schedule",
        auth: true,
      },
    ],
  },

  /* ── Tags ───────────────────────────────────────────────────────── */
  {
    title: "Tags",
    basePath: "/tags",
    description: "Manage tags used to categorize audit runs.",
    endpoints: [
      {
        method: "GET",
        path: "/tags/",
        summary: "List all tags",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Tag ID" },
          { name: "name", type: "string", description: "Tag name (unique, max 50 chars)" },
          { name: "created_at", type: "datetime", description: "Creation timestamp" },
        ],
      },
      {
        method: "POST",
        path: "/tags/",
        summary: "Create tag",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Tag name (max 50 chars)", required: true },
        ],
      },
      {
        method: "DELETE",
        path: "/tags/{id}/",
        summary: "Delete tag",
        auth: true,
      },
    ],
  },

  /* ── Dashboard ──────────────────────────────────────────────────── */
  {
    title: "Dashboard",
    basePath: "/dashboard",
    description: "Aggregated dashboard statistics.",
    endpoints: [
      {
        method: "GET",
        path: "/dashboard/summary/",
        summary: "Get dashboard summary",
        description: "Returns aggregated statistics for the dashboard cards.",
        auth: true,
        responseFields: [
          { name: "device_count", type: "integer", description: "Total number of devices" },
          { name: "recent_audit_count", type: "integer", description: "Audits in the last 24 hours" },
          { name: "pass_rate", type: "number", description: "7-day pass rate percentage" },
          { name: "failed_rule_count_24h", type: "integer", description: "Failed rules in the last 24 hours" },
        ],
      },
    ],
  },

  /* ── Netmiko Device Types ───────────────────────────────────────── */
  {
    title: "Netmiko Device Types",
    basePath: "/netmiko-device-types",
    description: "Manage SSH device type definitions used for config fetching.",
    endpoints: [
      {
        method: "GET",
        path: "/netmiko-device-types/",
        summary: "List device types",
        description: "Searchable by name and driver.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Device type ID" },
          { name: "name", type: "string", description: "Display name" },
          { name: "driver", type: "string", description: "Netmiko driver identifier" },
          { name: "default_command", type: "string", description: 'Default show command (e.g. "show running-config")' },
          { name: "description", type: "string", description: "Description" },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/netmiko-device-types/",
        summary: "Create device type",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Display name", required: true },
          { name: "driver", type: "string", description: "Netmiko driver identifier", required: true },
          { name: "default_command", type: "string", description: "Default show command", required: true },
          { name: "description", type: "string", description: "Description" },
        ],
      },
      {
        method: "GET",
        path: "/netmiko-device-types/{id}/",
        summary: "Get device type details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/netmiko-device-types/{id}/",
        summary: "Replace device type",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/netmiko-device-types/{id}/",
        summary: "Partial update device type",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/netmiko-device-types/{id}/",
        summary: "Delete device type",
        auth: true,
      },
    ],
  },

  /* ── Webhook Providers ──────────────────────────────────────────── */
  {
    title: "Webhook Providers",
    basePath: "/notifications/webhooks",
    description:
      "Configure external webhooks that receive notifications when audits complete.",
    endpoints: [
      {
        method: "GET",
        path: "/notifications/webhooks/",
        summary: "List webhook providers",
        description: "Searchable by name and URL.",
        auth: true,
        responseFields: [
          { name: "id", type: "integer", description: "Provider ID" },
          { name: "name", type: "string", description: "Provider name" },
          { name: "url", type: "string", description: "Webhook URL" },
          { name: "enabled", type: "boolean", description: "Whether the provider is active" },
          { name: "trigger_mode", type: "string", description: "per_audit or per_rule" },
          { name: "headers", type: "array", description: "Custom headers [{key, value}]" },
          { name: "created_at", type: "datetime", description: "Creation timestamp", readOnly: true },
          { name: "updated_at", type: "datetime", description: "Last update timestamp", readOnly: true },
        ],
      },
      {
        method: "POST",
        path: "/notifications/webhooks/",
        summary: "Create webhook provider",
        auth: true,
        requestBody: [
          { name: "name", type: "string", description: "Provider name", required: true },
          { name: "url", type: "string", description: "Webhook URL", required: true },
          { name: "enabled", type: "boolean", description: "Enable this provider (default: true)" },
          { name: "trigger_mode", type: "string", description: "per_audit (default) or per_rule" },
          { name: "headers", type: "array", description: 'Custom headers: [{key: "Authorization", value: "Bearer ..."}]' },
        ],
      },
      {
        method: "GET",
        path: "/notifications/webhooks/{id}/",
        summary: "Get webhook provider details",
        auth: true,
      },
      {
        method: "PUT",
        path: "/notifications/webhooks/{id}/",
        summary: "Replace webhook provider",
        auth: true,
      },
      {
        method: "PATCH",
        path: "/notifications/webhooks/{id}/",
        summary: "Partial update webhook provider",
        auth: true,
      },
      {
        method: "DELETE",
        path: "/notifications/webhooks/{id}/",
        summary: "Delete webhook provider",
        auth: true,
      },
      {
        method: "POST",
        path: "/notifications/webhooks/{id}/test/",
        summary: "Send test webhook",
        description: "Fire a test payload to the webhook URL.",
        auth: true,
        responseFields: [
          { name: "success", type: "boolean", description: "Whether the test succeeded" },
          { name: "status_code", type: "integer", description: "HTTP status code returned" },
          { name: "error", type: "string", description: "Error message if failed" },
        ],
      },
    ],
  },

  /* ── Site Settings ──────────────────────────────────────────────── */
  {
    title: "Site Settings",
    basePath: "/settings",
    description: "Global configuration for the Netaudit instance.",
    endpoints: [
      {
        method: "GET",
        path: "/settings/",
        summary: "Get site settings",
        auth: true,
        responseFields: [
          { name: "default_api_endpoint", type: "string", description: "Default API endpoint used when a device has none" },
          { name: "slack_webhook_url", type: "string", description: "Slack incoming webhook URL" },
          { name: "public_registration_enabled", type: "boolean", description: "Whether public signup is allowed" },
        ],
      },
      {
        method: "PUT",
        path: "/settings/",
        summary: "Replace site settings",
        auth: true,
        requestBody: [
          { name: "default_api_endpoint", type: "string", description: "Default API endpoint URL" },
          { name: "slack_webhook_url", type: "string", description: "Slack webhook URL" },
          { name: "public_registration_enabled", type: "boolean", description: "Enable/disable public registration" },
        ],
      },
      {
        method: "PATCH",
        path: "/settings/",
        summary: "Partial update site settings",
        auth: true,
      },
      {
        method: "POST",
        path: "/settings/test-slack/",
        summary: "Test Slack webhook",
        description: "Send a test message to the provided Slack webhook URL.",
        auth: true,
        requestBody: [
          { name: "webhook_url", type: "string", description: "Slack webhook URL to test", required: true },
        ],
        responseFields: [
          { name: "success", type: "boolean", description: "Whether the message was sent" },
          { name: "error", type: "string", description: "Error message if failed" },
        ],
      },
      {
        method: "GET",
        path: "/settings/registration-status/",
        summary: "Check registration status",
        description: "Public endpoint (no auth required) to check if signup is enabled.",
        auth: false,
        responseFields: [
          { name: "public_registration_enabled", type: "boolean", description: "Whether public registration is enabled" },
        ],
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const methodColors: Record<HttpMethod, string> = {
  GET: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  POST: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  PUT: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  PATCH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  DELETE: "bg-red-500/15 text-red-400 border-red-500/30",
};

function MethodBadge({ method }: { method: HttpMethod }) {
  return (
    <span
      className={cn(
        "inline-flex min-w-[62px] items-center justify-center rounded border px-2 py-0.5 text-xs font-bold tracking-wide",
        methodColors[method],
      )}
    >
      {method}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-6 w-6 text-muted-foreground hover:text-foreground"
      onClick={handleCopy}
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
    </Button>
  );
}

function FieldsTable({ fields, label }: { fields: Field[]; label: string }) {
  return (
    <div className="mt-3">
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[180px]">Field</TableHead>
            <TableHead className="w-[120px]">Type</TableHead>
            <TableHead>Description</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {fields.map((f) => (
            <TableRow key={f.name}>
              <TableCell className="font-mono text-xs">
                {f.name}
                {f.required && <span className="ml-1 text-red-400">*</span>}
                {f.readOnly && (
                  <Badge variant="outline" className="ml-1.5 text-[10px] py-0 px-1">
                    read-only
                  </Badge>
                )}
                {f.writeOnly && (
                  <Badge variant="outline" className="ml-1.5 text-[10px] py-0 px-1">
                    write-only
                  </Badge>
                )}
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {f.type}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {f.description}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Endpoint row                                                       */
/* ------------------------------------------------------------------ */

function EndpointRow({ ep }: { ep: Endpoint }) {
  const [open, setOpen] = useState(false);
  const hasDetail = ep.description || ep.requestBody || ep.responseFields;
  const fullPath = `${BASE_URL}${ep.path}`;

  return (
    <div className="border-b border-border last:border-0">
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-3 px-4 py-3 text-left transition-colors",
          hasDetail ? "cursor-pointer hover:bg-accent/50" : "cursor-default",
        )}
        onClick={() => hasDetail && setOpen(!open)}
      >
        <MethodBadge method={ep.method} />
        <code className="flex-1 text-sm">{fullPath}</code>
        <span className="hidden text-sm text-muted-foreground sm:inline">
          {ep.summary}
        </span>
        {ep.auth !== false ? (
          <Lock className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <Globe className="h-3.5 w-3.5 text-emerald-400" />
        )}
        {hasDetail && (
          open ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )
        )}
      </button>

      {open && (
        <div className="border-t border-border bg-accent/30 px-4 py-4 space-y-3">
          {ep.description && (
            <p className="text-sm text-muted-foreground">{ep.description}</p>
          )}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <code className="rounded bg-muted px-2 py-0.5 text-xs">
              {ep.method} {fullPath}
            </code>
            <CopyButton text={`${ep.method} ${fullPath}`} />
          </div>
          {ep.requestBody && (
            <FieldsTable fields={ep.requestBody} label="Request body" />
          )}
          {ep.responseFields && (
            <FieldsTable fields={ep.responseFields} label="Response" />
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section                                                            */
/* ------------------------------------------------------------------ */

function ApiSection({ section }: { section: EndpointSection }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Card id={section.title.toLowerCase().replace(/\s+/g, "-")}>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{section.title}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {section.description}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {section.endpoints.length} endpoint{section.endpoints.length !== 1 && "s"}
            </Badge>
            {collapsed ? (
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
        </div>
      </CardHeader>
      {!collapsed && (
        <CardContent className="p-0">
          <div className="divide-y divide-border">
            {section.endpoints.map((ep, i) => (
              <EndpointRow key={`${ep.method}-${ep.path}-${i}`} ep={ep} />
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export function ApiDocsPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">API Documentation</h1>
        <p className="mt-1 text-muted-foreground">
          Complete reference for the Netaudit REST API. Base URL:{" "}
          <code className="rounded bg-muted px-2 py-0.5 text-sm">{BASE_URL}</code>
        </p>
      </div>

      {/* Auth info card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Most endpoints require a JWT Bearer token. Obtain one from the{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">POST /api/v1/auth/login/</code>{" "}
            endpoint, then include it in every request:
          </p>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs">
{`Authorization: Bearer <access_token>`}
          </pre>
          <p>
            Access tokens are short-lived. Use{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">POST /api/v1/auth/token/refresh/</code>{" "}
            to exchange your refresh token for a new access token.
          </p>
          <div className="flex items-center gap-4 pt-1">
            <span className="flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5" /> Requires authentication
            </span>
            <span className="flex items-center gap-1.5">
              <Globe className="h-3.5 w-3.5 text-emerald-400" /> Public endpoint
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Pagination info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pagination & Filtering</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            List endpoints return paginated results. Use{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">?page=2&page_size=25</code>{" "}
            to navigate pages.
          </p>
          <p>
            Paginated responses have this shape:
          </p>
          <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-xs">
{`{
  "count": 42,
  "next": "http://...?page=2",
  "previous": null,
  "results": [ ... ]
}`}
          </pre>
          <p>
            Many list endpoints also support{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">?search=term</code>{" "}
            for full-text search and{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">?ordering=field</code>{" "}
            (prefix with <code className="rounded bg-muted px-1.5 py-0.5 text-xs">-</code> for descending).
            Filter parameters are noted in each endpoint's description.
          </p>
        </CardContent>
      </Card>

      {/* Quick nav */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sections</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {sections.map((s) => (
              <a
                key={s.title}
                href={`#${s.title.toLowerCase().replace(/\s+/g, "-")}`}
                className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground no-underline"
              >
                {s.title}
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Endpoint sections */}
      {sections.map((section) => (
        <ApiSection key={section.title} section={section} />
      ))}
    </div>
  );
}
