# Safety review

VoltAI is a decision-support demonstration, not a charger-control system.

- The scheduling engine uses only versioned fixtures or validated cached data.
- The coordinator receives schedule and checker values only through
  `agent.tools.EngineTools`; it does not perform its own arithmetic.
- `engine.checker` is independent of `engine.scheduler`. A dashboard plan is
  labelled verified only after the checker passes.
- Missing battery data raises an explicit error. Invalid tariff/route refreshes
  retain the prior cache.
- The dashboard's approval button appends a local audit record and explicitly
  states that it does not send a charger, vehicle, dispatch, or V2G command.
- `saved_outputs/approvals.jsonl` is ignored by Git because it is an
  environment-specific operator record.

Before any future physical integration, add authenticated operator identities,
access control, encryption, a hardware-specific command adapter, emergency
stop behaviour, audit retention, and security review. Keep the independent
checker as a blocking gate in that integration.
