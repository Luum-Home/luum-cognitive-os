// Command cos-dispatch is the vendor-agnostic hook dispatcher for Cognitive OS.
// It reads JSON from stdin, dispatches validators, and writes JSON to stdout.
// Exit code is always 0 (fail-open); exit code 2 is used to block tool execution.
//
// Subcommand routing (ADR-008):
//   - "cos-dispatch review ..."   → runReview (artifact feedback loop)
//   - "cos-dispatch" (no args)    → stdin-dispatch (backwards-compatible default)
//   - "cos-dispatch -flag ..."    → stdin-dispatch (flag-only, not a subcommand)
package main

import (
	"flag"
	"os"
)

var version = "dev"

func main() {
	os.Exit(run())
}

// run is the real entry point. It returns an exit code so deferred cleanup
// (tracker.Close) runs before os.Exit is called.  Using os.Exit directly in
// main would skip defers and leave the tracker buffer unflushed.
func run() int {
	args := os.Args[1:]

	// If the first non-flag argument is a recognised subcommand, dispatch to it.
	// "Recognised subcommand" means the first arg does not start with '-'.
	if len(args) > 0 && args[0] == "review" {
		return runReview(args[1:])
	}

	// Default path: stdin-dispatch.  Preserves 100% backwards compatibility with
	// vendor integrations that invoke cos-dispatch with no args or only flags.
	fs := flag.NewFlagSet("cos-dispatch", flag.ContinueOnError)
	f := registerDispatchFlags(fs)
	if err := fs.Parse(args); err != nil {
		return 1
	}
	return runDispatch(fs, f)
}
