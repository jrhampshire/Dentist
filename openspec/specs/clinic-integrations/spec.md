# Clinic Integrations Specification

## Purpose

Integration settings UI on the `/settings#integrations` tab — placeholder cards for Google Calendar, Gmail, and WhatsApp. Backend wiring for Google/Gmail is deferred; WhatsApp reflects the existing `OnboardingStep.whatsapp_config` status.

## Requirements

### Requirement: Integration Cards

The Integrations tab MUST render three cards in a responsive grid: Google Calendar, Gmail, and WhatsApp. Each card MUST display an icon, the integration name, a status badge (Conectado / Desconectado), and an action button.

| Card | Source | Action |
|------|--------|--------|
| Google Calendar | Placeholder (static "Desconectado") | "Conectar" / "Desconectar" (placeholder, no-op) |
| Gmail | Placeholder (static "Desconectado") | "Conectar" / "Desconectar" (placeholder, no-op) |
| WhatsApp | `OnboardingStep.whatsapp_config` | "Reconectar" when disconnected, status reflects backend |

When disconnected, the card MUST render a disabled/placeholder state with the integration's icon and a brief "Próximamente" hint for Google/Gmail.

#### Scenario: Google card is disconnected placeholder

- GIVEN the user opens the Integrations tab
- WHEN the Google Calendar card renders
- THEN a "Desconectado" badge and a disabled "Conectar" button are shown

#### Scenario: WhatsApp reflects backend status

- GIVEN the clinic's `whatsapp_config` is connected
- WHEN the WhatsApp card renders
- THEN a "Conectado" badge is shown

#### Scenario: Google connect click is a no-op

- GIVEN the user clicks "Conectar" on Google Calendar
- WHEN the click handler runs
- THEN no network call is made and a toast "Próximamente" is shown

### Requirement: Card Status and Sync Info

Each card MUST show its connection status badge. Where applicable (WhatsApp), the card MUST display the last-sync timestamp from the backend payload. Google/Gmail cards omit last-sync info until wired.

#### Scenario: WhatsApp last sync shown

- GIVEN the WhatsApp payload includes a `last_sync_at` field
- WHEN the card renders
- THEN the timestamp is shown formatted in Spanish locale

#### Scenario: Google card omits last sync

- GIVEN the Google card is rendered
- WHEN the card layout is computed
- THEN no last-sync row is displayed
