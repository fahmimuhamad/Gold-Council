---
name: strategy-formalization
description: Use when converting source-backed concepts into strategy YAML and detectors.
---
Each rule needs source_refs with page/timestamp, exact maths, availability time (bar close or later), entry/expiry/SL/TP, eligible regimes. Anything ambiguous goes in `unresolved` and keeps status draft. Add synthetic boundary tests and a no-lookahead test. Only a human sets approved statuses (approved_by).
