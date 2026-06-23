# inventory — Inventory Management Specification

## Purpose

Dental supply and material tracking with stock levels, expiration alerts, movement audit trail, and automatic consumption via procedure kits.

## Requirements

### Requirement: Inventory CRUD MUST enforce tenant isolation

The system SHALL scope all inventory operations to the requesting user's clinic.

#### Scenario: List items filtered by clinic

- GIVEN clinic A has 5 inventory items and clinic B has 3
- WHEN an authenticated user from clinic A calls `GET /api/v1/inventory/`
- THEN the system SHALL return exactly 5 items
- AND clinic B's items SHALL NOT appear

#### Scenario: Stock cannot be negative

- GIVEN an inventory item with `stock_current=0` and check constraint `chk_stock_current_non_negative`
- WHEN an attempt is made to set `stock_current` to a negative value
- THEN the database SHALL reject the operation with a check constraint violation

### Requirement: Stock deduction MUST enforce availability and status

The system SHALL prevent stock deduction when the item is blocked, expired, or has insufficient stock.

#### Scenario: Insufficient stock is rejected

- GIVEN an item with `stock_current=5`
- WHEN `item.deduct_stock(quantity=10)` is called
- THEN the system SHALL raise `ValueError` with message "Stock insuficiente"
- AND `stock_current` SHALL remain `5`

#### Scenario: Blocked items cannot be consumed

- GIVEN an item with `is_blocked=True` and `stock_current=10`
- WHEN `item.deduct_stock(quantity=1)` is called
- THEN the system SHALL raise `ValueError` with message indicating the item is blocked
- AND `stock_current` SHALL remain `10`

#### Scenario: Expired items cannot be consumed

- GIVEN an item with `is_expired=True` and `stock_current=10`
- WHEN `item.deduct_stock(quantity=1)` is called
- THEN the system SHALL raise `ValueError` with message indicating the item is expired
- AND `stock_current` SHALL remain `10`

### Requirement: Inventory movements MUST create an audit trail

Every stock change (add, deduct, adjust, consume) SHALL create an `InventoryMovement` record with `previous_stock`, `new_stock`, quantity, and reason.

#### Scenario: Deduction creates movement record

- GIVEN an item with `stock_current=10`
- WHEN `item.deduct_stock(quantity=3, reason="Consumo por cita")` is called
- THEN an `InventoryMovement` SHALL be created with `movement_type=out`
- AND `previous_stock=10`, `new_stock=7`, `quantity=-3`
- AND `stock_current` SHALL be `7`

#### Scenario: Addition creates movement record

- GIVEN an item with `stock_current=7`
- WHEN `item.add_stock(quantity=5, reason="Reabastecimiento")` is called
- THEN an `InventoryMovement` SHALL be created with `movement_type=in`
- AND `previous_stock=7`, `new_stock=12`, `quantity=5`

### Requirement: Low stock and expiration alerts MUST be queryable

The system SHALL expose endpoints for items below `stock_minimum` and items expiring soon.

#### Scenario: Low stock alert returns items below minimum

- GIVEN an item with `stock_current=10` and `stock_minimum=20`
- WHEN `GET /api/v1/inventory/alerts/` is called
- THEN the item SHALL appear in the low_stock results
- AND `item.is_low_stock` SHALL be `True`

#### Scenario: Expiring soon alert returns items near expiration

- GIVEN an item expiring in 25 days
- WHEN `GET /api/v1/inventory/alerts/?expiring_within_days=30` is called
- THEN the item SHALL appear in the expiring_soon results

#### Scenario: Well-stocked items do not trigger alerts

- GIVEN an item with `stock_current=100` and `stock_minimum=20`
- WHEN `GET /api/v1/inventory/alerts/` is called
- THEN the item SHALL NOT appear in low stock results

### Requirement: Expired items MUST auto-block on save

When an item with an `expiration_date` in the past is saved, the system SHALL automatically set `is_expired=True` and `is_blocked=True`.

#### Scenario: Expired item is auto-blocked

- GIVEN an item with `expiration_date=2024-01-01`
- WHEN the item is saved
- THEN `is_expired` SHALL be `True`
- AND `is_blocked` SHALL be `True`
- AND the item SHALL NOT be usable for consumption

### Requirement: Inventory kits MUST support automatic consumption

The system SHALL allow `AppointmentType` to define an `inventory_kit` that is automatically consumed when the appointment is completed.

#### Scenario: Kit consumption on appointment completion

- GIVEN an appointment type "Extracción" with `inventory_kit=[{item_id: "x", quantity: 2}, {item_id: "y", quantity: 1}]`
- WHEN the appointment is marked `completed`
- THEN item X's stock SHALL be reduced by 2
- AND item Y's stock SHALL be reduced by 1
- AND two `InventoryMovement` records SHALL be created with `movement_type=consumption`
