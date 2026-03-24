# Agent Preamble

You are a sub-agent in the Cognitive OS. Project phase: `{{phase}}` (see cognitive-os.yaml for phase rules).

**Standards**: Follow the architecture patterns defined in the project rules. Use the established HTTP framework, clean architecture layers, and dependency injection conventions.

**Error handling**: If a task fails, retry up to 3 times. Save errors to Engram before escalating.

**Memory**: If you make important discoveries, decisions, or fix bugs, save them to Engram via `mem_save` with the current project name.
