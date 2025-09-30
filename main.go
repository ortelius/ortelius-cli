package main

import (
	"github.com/ortelius/dh-cli/cmd"
	"github.com/ortelius/dh-cli/internal/config"
)

func main() {
	// Set up the config package to access global flags
	config.SetGlobalFlagsGetter(cmd.GetGlobalFlags)
	
	// Execute the root command
	cmd.Execute()
}
