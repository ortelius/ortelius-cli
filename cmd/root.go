package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

const version = "9.3.281"

var (
	dhurl string
	dhuser string
	dhpass string
	rsp string
	cert string
)

var RootCmd = &cobra.Command{
	Use:   "dh",
	Short: "Ortelius CLI using the dhapi module",
	Long: `Ortelius CLI provides commands to interact with DeployHub for:
- Deploying applications
- Managing component versions  
- Approving applications
- Moving applications between domains
- Exporting/importing configurations
- And more...`,
	Version: version,
}

func Execute() {
	if err := RootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func init() {
	// Global flags
	RootCmd.PersistentFlags().StringVar(&dhurl, "dhurl", "", "DeployHub URL")
	RootCmd.PersistentFlags().StringVar(&dhuser, "dhuser", "", "DeployHub User")
	RootCmd.PersistentFlags().StringVar(&dhpass, "dhpass", "", "DeployHub Password")
	RootCmd.PersistentFlags().StringVar(&cert, "cert", "", "Customer SSL Certificate File")
	RootCmd.PersistentFlags().StringVar(&rsp, "rsp", "component.toml", "Response File for Parameters")

	// Bind environment variables
	viper.BindEnv("dhurl", "DHURL")
	viper.BindEnv("dhuser", "DHUSER")
	viper.BindEnv("dhpass", "DHPASS")
}

func GetGlobalFlags() (string, string, string, string, string) {
	return dhurl, dhuser, dhpass, rsp, cert
}
