# Delta for Fiscal Config

## ADDED Requirements

### Requirement: Fiscal Config Frontend Form

A frontend form MUST allow admins to create or edit their clinic's `FiscalConfig`. Fields, types, and validation:

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `razon_social` | text | Yes | max 255 chars |
| `regimen_fiscal` | select | Yes | SAT codes 601, 603, 605, 606, 607, 608, 610, 611, 612, 614, 615, 616, 620, 621, 622, 623, 624, 625, 626 |
| `fiscal_address` | nested fields | Yes | calle, no_exterior, no_interior, colonia, localidad, municipio, estado, pais, codigo_postal |
| `email` | email | No | Optional |
| `csd_cert_path` | text | No | File path string |
| `csd_key_path` | text | No | File path string |
| `csd_password` | password | No | `type="password"`, write-only |

The form MUST POST to `/api/v1/fiscal-config/` when no config exists and PATCH `/api/v1/fiscal-config/{id}/` when one exists. Existing paths MUST be shown as text in their inputs.

#### Scenario: Create fiscal config

- GIVEN no fiscal config exists
- WHEN the admin submits a valid form
- THEN a POST is sent and a success toast appears

#### Scenario: Edit existing fiscal config

- GIVEN a saved fiscal config
- WHEN the admin changes `regimen_fiscal` and submits
- THEN a PATCH is sent and the badge/state updates

#### Scenario: Fiscal address fields

- GIVEN the form is rendered
- WHEN the address section displays
- THEN all nine address sub-fields (calle, no_exterior, no_interior, colonia, localidad, municipio, estado, pais, codigo_postal) are present

### Requirement: CSD Validation Action

A "Validar CSD" button MUST call `POST /api/v1/fiscal-config/{id}/validate-csd/` with `{ csd_password: string }`. During the call, a loading spinner MUST be shown. On success, the `is_validated` badge MUST update to green "Validado"; on failure, an error toast MUST appear and the badge MUST remain red "No validado".

#### Scenario: Successful CSD validation

- GIVEN a password is entered
- WHEN the admin clicks "Validar CSD"
- THEN POST is sent, a spinner appears, and the badge turns green "Validado"

#### Scenario: Failed CSD validation

- GIVEN an incorrect password is entered
- WHEN the admin clicks "Validar CSD"
- THEN an error toast appears and the badge stays red

### Requirement: Validated Status Badge

The fiscal config form MUST render an `is_validated` badge: green "Validado" when true, red "No validado" when false. The badge MUST update reactively after a successful validation.

#### Scenario: Badge reflects current state

- GIVEN `is_validated === false` from the API
- WHEN the form renders
- THEN a red "No validado" badge is shown
