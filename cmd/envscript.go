package cmd

import (
	"fmt"

	"github.com/ortelius/dh-cli/internal/util"
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

func runEnvScript(cmd *cobra.Command, args []string) error {
	dhurl, dhuser, dhpass, rsp, cert := GetGlobalFlags()
	_ = dhurl
	_ = dhuser
	_ = dhpass
	_ = cert

	if util.IsEmpty(envvars) && util.IsEmpty(rsp) {
		return fmt.Errorf("envvars is required")
	}

	if util.IsEmpty(envvars) {
		envvars = rsp
	}

	fmt.Printf("Creating env shell script from %s\n", envvars)
	return util.CreateEnvScript(envvars, envvarssh)
}
