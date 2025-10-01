// Package main provides the entry point for the Ortelius CLI application.
package main

import (
	"github.com/ortelius/ortelius-cli/cmd"
	"github.com/ortelius/ortelius-cli/internal/config"
)

func main() {
	// Set up the config package to access global flags
	config.SetGlobalFlagsGetter(cmd.GetGlobalFlags)

	// Execute the root command
	cmd.Execute()
}
