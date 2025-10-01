// Package cmd provides command-line interface commands for the DeployHub CLI application.
package cmd

import (
	"fmt"

	"github.com/ortelius/ortelius-cli/internal/dhutil"
	"github.com/spf13/cobra"
)

var (
	envvars   string
	envvarssh string
)

var envscriptCmd = &cobra.Command{
	Use:   "envscript",
	Short: "Create bash file from component toml file",
	Long:  "Creates a bash file from the component toml file",
	RunE:  runEnvScript,
}

func init() {
	envscriptCmd.Flags().StringVar(&envvars, "envvars", "", "Environment Variables TOML file")
	envscriptCmd.Flags().StringVar(&envvarssh, "envvars_sh", "", "Environment Variables Output shell file")

	RootCmd.AddCommand(envscriptCmd)
}

func runEnvScript(_ *cobra.Command, _ []string) error {
	dhurl, dhuser, dhpass, rsp, cert := GetGlobalFlags()
	_ = dhurl
	_ = dhuser
	_ = dhpass
	_ = cert

	if dhutil.IsEmpty(envvars) && dhutil.IsEmpty(rsp) {
		return fmt.Errorf("envvars is required")
	}

	if dhutil.IsEmpty(envvars) {
		envvars = rsp
	}

	fmt.Printf("Creating env shell script from %s\n", envvars)
	return dhutil.CreateEnvScript(envvars, envvarssh)
}
