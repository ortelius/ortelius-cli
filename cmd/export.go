package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/ortelius/dh-cli/internal/config"
	"github.com/ortelius/dh-cli/internal/util"
	"github.com/spf13/cobra"
)

var fromdom string

var exportCmd = &cobra.Command{
	Use:   "export",
	Short: "Export domain including all objects to stdout",
	Long:  "Exports a domain including all objects to stdout",
	RunE:  runExport,
}

func init() {
	exportCmd.Flags().StringVar(&fromdom, "fromdom", "", "From Domain")
	
	RootCmd.AddCommand(exportCmd)
}

func runExport(cmd *cobra.Command, args []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if util.IsEmpty(fromdom) {
		return fmt.Errorf("fromdom is required")
	}

	allObjs := make(map[string]interface{})

	objectTypes := []string{"users", "groups", "comptypes", "credentials", "endpoints",
		"datasources", "tasks", "engines", "repositories", "environments", "components", "applications", "releases"}

	for _, objType := range objectTypes {
		util.FilterDict(client, objType, fromdom, allObjs)
	}

	jsonStr, err := json.MarshalIndent(allObjs, "", "  ")
	if err != nil {
		return err
	}

	fmt.Println(string(jsonStr))
	return nil
}
