# Northstar Fleet Maintenance Platform

## Business scope

Northstar operates delivery vans across Karachi, Lahore, and Islamabad. The platform must track vehicles, maintenance work, inspections, and workshop inventory. It does not manage delivery routes, driver payroll, or customer orders.

## Users and permissions

- Fleet administrators can register vehicles, assign workshop locations, and view all records.
- Workshop managers can create work orders, approve parts usage, and close completed work.
- Technicians can update tasks assigned to them and record inspection results.
- Drivers can submit defect reports for vehicles assigned to them but cannot edit work orders.
- Auditors have read-only access to work orders, inspections, and inventory adjustments.

## Vehicle and maintenance rules

- Every vehicle is identified by a unique registration number and VIN.
- A vehicle can be marked `active`, `in_maintenance`, or `retired`.
- Open work orders place the vehicle in `in_maintenance` status.
- A work order cannot be closed until every required task is completed and a workshop manager approves it.
- Odometer readings must never be lower than the vehicle's previous recorded reading.
- Preventive maintenance is due every 10,000 km or six months, whichever occurs first.

## Defect and inspection workflow

- Driver defect reports include the vehicle, description, severity, timestamp, and optional photos.
- Critical defects immediately prevent the vehicle from being assigned for use.
- A technician must record pass/fail results for brakes, tyres, lights, steering, and fluid levels.
- Failed safety checks create a required work-order task automatically.

## Parts inventory

- Inventory is tracked independently per workshop.
- Parts cannot be issued if doing so would make available stock negative.
- Every receipt, issue, return, or adjustment creates an immutable inventory ledger entry.
- Issuing a part requires an open work order and workshop-manager approval.
- Reorder alerts are raised when available quantity reaches or falls below the part's configured threshold.

## Architecture constraints

- Use a Next.js web application and a FastAPI API.
- Store transactional data in PostgreSQL.
- Use an asynchronous event bus for maintenance-due notifications and reorder alerts.
- Run local development through Docker Compose.
- Record an audit event for permission changes, work-order approval, work-order closure, and inventory adjustment.
- Personally identifiable driver data must be encrypted in transit and at rest.

## Reliability and testing

- Inventory ledger writes and stock updates must commit in one database transaction.
- Event publication must use the transactional outbox pattern.
- Duplicate events must be handled idempotently by consumers.
- Automated tests must cover authorization boundaries, invalid odometer readings, work-order closure rules, negative-stock prevention, and duplicate-event delivery.

## Explicit exclusions

- No GPS or live vehicle tracking.
- No payment processing.
- No predictive maintenance or machine-learning requirement.
- No integration with government registration systems in the first release.
