package cmd

import (
	"fmt"
	"strings"

	"github.com/ortelius/dh-cli/internal/config"
	"github.com/ortelius/dh-cli/internal/util"
	"github.com/spf13/cobra"
)

var (
	fromDomain string
	task       string
)

var moveCmd = &cobra.Command{
	Use:   "move",
	Short: "Move application version using supplied task",
	Long:  "Move the application version from one domain to another using the supplied task",
	RunE:  runMove,
}

func init() {
	moveCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	moveCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")
	moveCmd.Flags().StringVar(&fromDomain, "from_domain", "", "Move from domain")
	moveCmd.Flags().StringVar(&task, "task", "", "Task to use for move")
	
	RootCmd.AddCommand(moveCmd)
}

func runMove(cmd *cobra.Command, args []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if util.IsEmpty(appname) {
		return fmt.Errorf("appname is required")
	}
	if util.IsEmpty(fromDomain) {
		return fmt.Errorf("from_domain is required")
	}
	if util.IsEmpty(task) {
		return fmt.Errorf("task is required")
	}

	// Parse appname;appversion format
	if util.IsEmpty(appversion) && strings.Contains(appname, ";") {
		parts := strings.Split(appname, ";")
		if len(parts) == 3 {
			appname = parts[0] + ";" + parts[1]
			appversion = parts[2]
		}
	}

	fmt.Printf("Moving %s %s from %s\n", appname, appversion, fromDomain)
	appID, result := client.MoveApplication(appname, appversion, fromDomain, task)

	if appID < 0 {
		return fmt.Errorf("move failed: %s", result)
	}

	fmt.Println(result)
	return nil
}
