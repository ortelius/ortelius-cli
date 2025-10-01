// Package cmd provides command-line interface commands for the DeployHub CLI application.
package cmd

import (
	"fmt"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/dhutil"
	"github.com/spf13/cobra"
)

var approveCmd = &cobra.Command{
	Use:   "approve",
	Short: "Approve application version",
	Long:  "Approve the application version for deployment",
	RunE:  runApprove,
}

func init() {
	approveCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	approveCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")

	RootCmd.AddCommand(approveCmd)
}

func runApprove(_ *cobra.Command, _ []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if dhutil.IsEmpty(appname) {
		return fmt.Errorf("appname is required")
	}

	// Parse appname;appversion format
	if dhutil.IsEmpty(appversion) && strings.Contains(appname, ";") {
		parts := strings.Split(appname, ";")
		if len(parts) == 3 {
			appname = parts[0] + ";" + parts[1]
			appversion = parts[2]
		}
	}

	fmt.Printf("Approving %s %s\n", appname, appversion)
	appID, result := client.ApproveApplication(appname, appversion)

	if appID < 0 {
		return fmt.Errorf("approval failed: %s", result)
	}

	fmt.Println(result)
	return nil
}
