# Industry-Specific Gates (Example Template)

This is an EXAMPLE template. Projects should create their own industry-specific gates.

For a fintech project, you might include:
- Idempotency for financial operations
- Audit trails for money movement
- Mock-first for external provider integrations

For an ecommerce project:
- Inventory consistency checks
- Payment gateway mock-first
- Order state machine validation

For a healthcare project:
- HIPAA compliance checks
- Data encryption at rest
- Audit logging for PHI access

Create your project-specific gates template in `.cognitive-os/templates/` or `{project}/.claude/templates/`.
