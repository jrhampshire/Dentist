# Clinic Configuration UI Specification

## Purpose

Frontend Configuration Hub at `/settings` providing tabbed access to clinic profile, fiscal data, integrations, subscription, and appointment types.

## Requirements

### Requirement: Tabbed Configuration Hub

`/settings` MUST render five tabs via shadcn/ui `Tabs` with persistent URL hash routing.

| Tab | Hash | Source |
|-----|------|--------|
| Información General | `#general` | `GET /clinics/{id}/` |
| Datos Fiscales | `#fiscal` | `GET /fiscal-config/` |
| Integraciones | `#integrations` | Static + WhatsApp |
| Plan y Suscripción | `#plan` | `GET /clinics/{id}/` |
| Tipos de Cita | `#appointment-types` | `useAppointmentTypes` |

The page MUST be wrapped in `ProtectedRoute`. Each tab MUST load data independently and render loading (skeleton), error (retry button), empty, and success states.

#### Scenario: Open from sidebar

- GIVEN an authenticated admin
- WHEN they click "Configuración"
- THEN the browser navigates to `/settings` with General active

#### Scenario: Deep link to a tab

- GIVEN `/settings#fiscal`
- WHEN the page loads
- THEN the Fiscal tab is active and its query runs

#### Scenario: Query error

- GIVEN a tab's query fails
- WHEN the tab renders
- THEN a retry button appears; clicking it refetches

### Requirement: General Info Tab

Edit `name` (required), `phone` (required, format-validated), `address` (optional). `rfc` and `email` are read-only. On save MUST call `PATCH /clinics/{id}/`, show a success/error toast, and invalidate the clinic query. "Guardar" MUST be disabled while pending.

#### Scenario: Save edits

- GIVEN edits to phone and address
- WHEN "Guardar" is clicked
- THEN PATCH is sent, a success toast appears, and the form reflects saved values

#### Scenario: Empty required field

- GIVEN name is cleared
- WHEN submit is attempted
- THEN submit is blocked with an inline validation message

#### Scenario: RFC and email are read-only

- GIVEN the tab renders
- WHEN the form is displayed
- THEN rfc and email inputs are disabled

### Requirement: Fiscal Config Tab

Show `razon_social`, `regimen_fiscal`, `fiscal_address`, `email`, `is_validated` from `GET /fiscal-config/`. If absent, create via `POST`; if present, edit via `PATCH /{id}/`. `regimen_fiscal` MUST be a select with SAT codes 601, 603, 605, 606, 607, 608, 610, 611, 612, 614, 615, 616, 620, 621, 622, 623, 624, 625, 626. CSD `.cer`/`.key` are text inputs (string paths); existing paths render as text. CSD password MUST be `type="password"` and write-only. `is_validated` MUST render as green "Validado" or red "No validado" badge. "Validar CSD" MUST call `POST /fiscal-config/{id}/validate-csd/` with current password; show spinner during the call.

#### Scenario: Validate CSD

- GIVEN a saved fiscal config with password entered
- WHEN "Validar CSD" is clicked
- THEN POST is sent, a spinner appears, and the badge updates

#### Scenario: Password is not repopulated

- GIVEN a previously saved fiscal config
- WHEN the tab reopens
- THEN the password input is empty and the GET response has no password field

### Requirement: Integrations Tab

Render Google Calendar, Gmail, and WhatsApp cards. See `clinic-integrations` spec for details.

### Requirement: Plan & Subscription Tab

Read-only display of plan name (Starter/Pro/Premium), `stamps_remaining` (green >20, yellow 10–20, red <10), `subscription_start`/`subscription_end` in Spanish locale, and status badge (Activo/Suspendido/Cancelado). If `plan === "free"`, show a placeholder "Actualiza tu plan" CTA.

#### Scenario: Stamps color thresholds

- GIVEN 25 stamps remaining
- WHEN the Plan tab renders
- THEN the count is shown in green

#### Scenario: Free plan CTA

- GIVEN the plan is "free"
- WHEN the Plan tab renders
- THEN the "Actualiza tu plan" CTA is displayed

### Requirement: Appointment Types Tab

MUST preserve current behavior: list types in a table (name, duration, kit count), open `AppointmentTypeDialog` for create/edit, and provide delete actions. Data flow and dialog MUST NOT change.

#### Scenario: Create appointment type

- GIVEN the admin clicks "Nuevo tipo de cita"
- WHEN the dialog is submitted
- THEN a new type is created and the table refreshes
