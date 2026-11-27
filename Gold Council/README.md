# Gold Council Assistant Starter

This is a configuration starter, not a working trading application. It contains the full previous master guide, a primary assistant, 18 specialist definitions, one workflow skill, and initial project state and knowledge registers. No books are bundled. No API key required for the intended interactive Claude Code subscription workflow.

## Install on macOS
1. Install Claude Code if needed using the official setup at https://code.claude.com/docs/en/setup. Run `claude --version`.
2. Unzip this archive into `~/Projects/` (the archive contains the `gold-council-assistant-starter/` directory). Use a new folder to avoid overwriting an existing project.
3. In Terminal run `cd ~/Projects/gold-council-assistant-starter`.
4. For subscription authentication, run `env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN claude --agent gold-council-assistant`. Sign in using your eligible Claude account if prompted. Check `/status` and `/agents` in the session. If an API gateway is configured, review your environment and settings rather than assuming subscription billing.
5. Ask: `Verify the project setup and registered agents. Read GOLD_COUNCIL_SPEC.md and CLAUDE.md. Inventory existing knowledge and test the missing-source workflow with the Probability of Backtest Overfitting paper. Do not start API billing or real trading.`
6. Approve only expected tool actions. Restart Claude Code if newly created agent files are not discovered.
7. For later use launch the same command again. Use `claude --continue` from the same folder to resume the previous conversation if desired, or open a fresh assistant session and ask it to read STATE.md. Use `/model` or edit agent model aliases if your subscription lacks access to Opus or usage is limited.

## On demand examples
- Find lawful sources for Mind Over Markets; don't purchase anything.
- Find and download an authorized open copy of The Probability of Backtest Overfitting; record source and rights, and ingest if the pipeline exists.
- Study the available ICT materials and report missing definitions; delegate to the librarian if necessary.
- Continue the earliest incomplete milestone; run tests and have the auditor review it.
- Backtest London ORB against the rule-based baseline with available historical data.
- Analyze the latest verified XAUUSD snapshot, or tell me what data is missing.

## Notes
Current mode overrides future API steps in GOLD_COUNCIL_SPEC.md. The local registers persist across sessions; the assistant itself does not run after you exit. Claude subagents share the same provider and subscription limits; they are not statistically independent. Prompt-level boundaries are not OS-level security controls; use normal tool permissions and keep trading credentials out of the project. This starter has been checked for file structure, not executed in Claude Code or MT5.
