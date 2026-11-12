# Architecture generation prompt

Use `../knowledge/digital-banking-knowledge.md` as the authoritative knowledge base for this request.

Design a production-ready architecture for the Crescent Digital Banking Platform. Explain how the design prevents overspending during concurrent transfers, guarantees atomic double-entry ledger updates, handles idempotent requests, and publishes reliable events without coupling notification delivery to financial transactions.

Your response must include:

1. A concise summary of the business scope and explicit exclusions.
2. A system-context view and a component-level architecture.
3. Clear service and module responsibilities.
4. A PostgreSQL data model covering customers, accounts, balances or holds, beneficiaries, transfers, ledger transactions, ledger entries, idempotency records, audit events, and transactional outbox records.
5. REST API endpoints under `/api/v1`, including authentication and authorization rules.
6. Step-by-step flows for beneficiary creation, an internal funds transfer, bill payment, reversal, compliance review, and notification retry.
7. The transaction boundaries, concurrency-control strategy, and failure handling for each financial flow.
8. Security controls for multi-factor authentication, session expiry, encryption, masking, secrets, rate limiting, and immutable auditing.
9. Event schemas and idempotent consumer behavior for duplicate and out-of-order delivery.
10. Deployment topology for local Docker Compose and a production environment.
11. Observability, backup, reconciliation, recovery, and operational alerting.
12. A prioritized automated-test plan tied to the knowledge-base requirements.
13. Assumptions, unresolved decisions, and risks. Do not invent requirements silently.

For every important design decision, cite the relevant heading from the knowledge base. Clearly distinguish stated requirements from your recommendations. Do not add lending, investments, cryptocurrency, international transfers, or card-data processing to the proposed scope.
