# Default API Endpoint Configuration

## Problem

Each device currently requires a full `api_endpoint` URL. When many devices share the same base URL (differing only by device name), this is repetitive and error-prone.

## Solution

A global "default API endpoint" setting, configurable via the web UI. When set, devices without a custom `api_endpoint` automatically use `<default_endpoint>/<device.name>`.

## Data Model

New `settings` Django app with a singleton `SiteSettings` model:

- `default_api_endpoint`: URLField, blank=True
- Auto-created on first access (only one row ever exists)

## Endpoint Resolution Logic

In `_fetch_config()` (audits/services.py):

1. If `device.api_endpoint` is set, use it as-is
2. Else if `SiteSettings.default_api_endpoint` is set, use `<default>/<device.name>`
3. Else fail with error (no endpoint configured)

## Device Model Changes

- `api_endpoint` becomes optional (blank=True)
- Helper text on form: "Leave blank to use default endpoint"

## Web UI

- New "Settings" page added to sidebar navigation
- Simple form with default endpoint URL field and save button
- Uses existing HTMX/Django template patterns

## Device Display

- Device detail and list pages show the effective endpoint
- Makes it clear whether a device uses its own URL or the default
