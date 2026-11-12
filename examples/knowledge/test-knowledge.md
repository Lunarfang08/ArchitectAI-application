# Acme Inventory Platform — Test Requirements

## Business goal

Acme needs a small inventory system for two warehouses: Karachi and Lahore. Staff must be able to view products, receive stock, reserve stock for an order, and release expired reservations.

## Required stack

- Frontend: Next.js with TypeScript
- Backend: FastAPI with Python
- Database: PostgreSQL
- Background work: Redis-backed worker
- Local development: Docker Compose

## Business rules

1. A product is identified by a unique SKU.
2. Available stock equals on-hand stock minus active reservations.
3. A reservation must never make available stock negative.
4. Reservations expire after 15 minutes unless confirmed.
5. Every stock adjustment must create an immutable audit record containing the SKU, warehouse, quantity change, reason, actor, and timestamp.
6. Receiving the same supplier delivery event more than once must not increase stock twice. Use the delivery ID as an idempotency key.

## API and security constraints

- Expose REST endpoints under `/api/v1`.
- Use role-based access with `viewer`, `operator`, and `admin` roles.
- Only operators and admins may change or reserve stock.
- Only admins may make manual stock corrections.
- Validate all request bodies and return structured error responses.

## Reliability target

The design should remain correct when two users try to reserve the final units of the same SKU concurrently. Include health checks, structured logs, database migrations, and automated tests for reservation concurrency, authorization, expiry, and delivery idempotency.
