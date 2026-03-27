package main

import (
	"fmt"
	"os"

	"luum-agent-os/cmd/cos-test/internal/cli"
)

func main() {
	if err := cli.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
