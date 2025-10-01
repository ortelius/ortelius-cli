// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// Version is set at build time via -ldflags
var Version = "dev"

var (
	orteliusURL  string
	dhURL        string // Legacy flag for backward compatibility
	orteliusUser string
	dhUser       string // Legacy flag for backward compatibility
	orteliusPass string
	dhPass       string // Legacy flag for backward compatibility
	rsp          string
)

// RootCmd represents the base command when called without any subcommands
var RootCmd = &cobra.Command{
	Use:   "ortelius",
	Short: "Ortelius CLI using the Ortelius API Module",
	Long: `Ortelius CLI provides commands to interact with Ortelius for:
- Deploying applications
- Record deployment of the Application
- Managing component versions
- Create/replace the Component Version for the Application Version
- Assign a component version to an Application Version
- Assign the key/values pairs to the Component Version
- Persist SBOMs to the Component Version
- Persist SonarQube Project Status, Bugs, Code Smells, and Violations metrics to the Component Version
- Persist Veracode Score to the Component Version
- Persist License File to the Component Version
- Persist Readme File the Component Version
- Persist Swagger and OpenAPI files the Component Version
- Persist Git Branch, Branch Create Commit, Branch Create Timestamp, Branch Parent, Commit, Commit Authors, Committers Count, Commit Timestamp, Lines Added, Lines Deleted, Lines Total, Org, Repo, Repo Project, Signed Off By, Tag, Url, Verified Commit
- Approving applications
- Moving applications between domains
- Create a bash file from the Component .toml file
- Export a Domain including all objects to stdout
- Imports the export file into the new Domain`,
	Version: Version,
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	if err := RootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func init() {
	// Global flags
	RootCmd.PersistentFlags().StringVar(&orteliusURL, "ortelius-url", "", "Ortelius URL")
	RootCmd.PersistentFlags().StringVar(&dhURL, "dhurl", "", "Ortelius URL (deprecated, use --ortelius-url)")
	RootCmd.PersistentFlags().StringVar(&orteliusUser, "ortelius-user", "", "Ortelius User")
	RootCmd.PersistentFlags().StringVar(&dhUser, "dhuser", "", "Ortelius User (deprecated, use --ortelius-user)")
	RootCmd.PersistentFlags().StringVar(&orteliusPass, "ortelius-pass", "", "Ortelius Password")
	RootCmd.PersistentFlags().StringVar(&dhPass, "dhpass", "", "Ortelius Password (deprecated, use --ortelius-pass)")
	RootCmd.PersistentFlags().StringVar(&rsp, "rsp", "component.toml", "Response File for Parameters")

	// Bind environment variables
	viper.BindEnv("dhurl", "DHURL")
	viper.BindEnv("orteliusurl", "ORTELIUS_URL")
	viper.BindEnv("dhuser", "DHUSER")
	viper.BindEnv("orteliususer", "ORTELIUS_USER")
	viper.BindEnv("dhpass", "DHPASS")
	viper.BindEnv("orteliuspass", "ORTELIUS_PASS")
}

// GetGlobalFlags returns the global flag values for use by other packages
func GetGlobalFlags() (string, string, string, string) {
	// Implement fallback logic: use ortelius* flags if set, otherwise fall back to dh* flags
	url := orteliusURL
	if url == "" {
		url = dhURL
	}

	user := orteliusUser
	if user == "" {
		user = dhUser
	}

	pass := orteliusPass
	if pass == "" {
		pass = dhPass
	}

	return url, user, pass, rsp
}
