# Crescent Digital Banking Platform

## Business scope

Crescent Bank needs a digital banking platform for retail customers in Pakistan. Customers can view accounts, transfer funds, manage beneficiaries, pay utility bills, and receive transaction notifications. The first release does not include lending, investments, foreign-currency trading, or business banking.

## Users and permissions

- Customers can access only their own accounts, beneficiaries, payments, and transaction history.
- Customer-support agents can view masked customer and transaction data but cannot initiate or approve transactions.
- Compliance officers can review flagged transactions and place or remove compliance holds.
- Operations administrators can manage transaction limits and service availability but cannot view authentication secrets.
- Security auditors have read-only access to security events, administrative changes, and access logs.

## Account and beneficiary rules

- Each account has a unique IBAN and can be `active`, `restricted`, `dormant`, or `closed`.
- Closed accounts cannot send or receive transfers.
- Restricted accounts cannot initiate transfers, but authorized incoming credits are allowed.
- A customer must complete step-up authentication before adding a beneficiary.
- New beneficiaries have a 30-minute cooling-off period before the first transfer.
- Beneficiary changes must create an immutable audit event.

## Funds-transfer rules

- A transfer must never make the source account's available balance negative.
- Available balance equals the ledger balance minus active holds.
- Every transfer has a client-supplied idempotency key that is unique per customer for 24 hours.
- Transfers above PKR 100,000 require a one-time password or equivalent step-up authentication.
- A customer's combined outgoing transfers cannot exceed PKR 500,000 per day unless a lower configured limit applies.
- Debit and credit ledger entries must be written atomically using double-entry accounting.
- A transfer can be `pending`, `completed`, `failed`, `reversed`, or `under_review`.

## Bill payments and notifications

- A bill inquiry must return the consumer name, billing period, amount due, and due date before payment confirmation.
- Repeated bill-payment requests with the same idempotency key must not create duplicate debits.
- Successful transfers and bill payments generate in-app and SMS notifications.
- Notification delivery failure must not roll back a completed financial transaction.
- Notification retries must be idempotent and use exponential backoff.

## Security and compliance

- Use multi-factor authentication for customers and privileged staff.
- Encrypt all network traffic with TLS and encrypt sensitive customer data at rest.
- Never store plaintext passwords, one-time passwords, PINs, or full card credentials in logs.
- Mask IBANs and customer identifiers in support views and application logs.
- Sessions expire after 15 minutes of inactivity; privileged sessions expire after 10 minutes.
- Record immutable audit events for logins, failed authentication, beneficiary changes, limit changes, compliance holds, and privileged data access.
- Flag suspicious transfer patterns for manual compliance review without automatically declaring fraud.

## Architecture constraints

- Use a Next.js web application and a FastAPI API.
- Store accounts, transfers, and ledger entries in PostgreSQL.
- Use Redis for short-lived sessions, rate limiting, and distributed coordination, but not as the financial system of record.
- Use an asynchronous event bus for notifications and compliance screening.
- Use the transactional outbox pattern for events produced by committed financial transactions.
- Run local development through Docker Compose.
- Expose versioned REST endpoints under `/api/v1`.

## Reliability and observability

- Concurrent transfers must lock or otherwise protect the source balance from overspending.
- Consumers must handle duplicate and out-of-order events safely.
- Reconciliation must detect unbalanced ledger transactions and missing external settlement results.
- Include structured logs, correlation IDs, metrics, health checks, database migrations, and alerting for transfer failure-rate spikes.
- Backups must be encrypted, restoration must be tested, and recovery procedures must define recovery-time and recovery-point targets.

## Required automated tests

- Authorization boundaries between customers and staff roles.
- Concurrent transfers attempting to spend the final available balance.
- Duplicate transfer and bill-payment requests.
- Beneficiary cooling-off enforcement.
- Daily and per-transaction transfer limits.
- Atomic double-entry ledger writes and reversal behavior.
- Redaction of authentication secrets and sensitive identifiers from logs.
- Duplicate, delayed, and out-of-order event delivery.

## Explicit exclusions

- No cryptocurrency support.
- No loan origination or credit scoring.
- No investment or brokerage products.
- No international or foreign-currency transfers in the first release.
- No storage or processing of full payment-card details.
