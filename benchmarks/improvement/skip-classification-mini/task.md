# Skip Classification Mini Benchmark

Classify test-lane skip reasons into stable categories without hiding unknown failures.
The target reads public execution logs and should map known optional-service skips to
`environmental_optional`, bootstrap precondition skips to `bootstrap_precondition`,
and unknown failures to `unknown_blocking`.

This benchmark is intentionally tiny: it validates the improvement-loop artifact
contract before larger SO primitives use the loop.
