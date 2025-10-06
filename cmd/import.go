// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/spf13/cobra"
)

var (
	todom      string
	importfile string
)

var importCmd = &cobra.Command{
	Use:   "import",
	Short: "Import export file into new domain",
	Long:  "Imports the export file into the new domain",
	RunE:  runImport,
}

func init() {
	importCmd.Flags().StringVar(&fromdom, "fromdom", "", "From Domain")
	importCmd.Flags().StringVar(&todom, "todom", "", "To Domain")
	importCmd.Flags().StringVar(&importfile, "importfile", "", "File to Import")

	RootCmd.AddCommand(importCmd)
}

func runImport(_ *cobra.Command, _ []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if util.IsEmpty(fromdom) {
		return fmt.Errorf("fromdom is required")
	}
	if util.IsEmpty(todom) {
		return fmt.Errorf("todom is required")
	}
	if util.IsEmpty(importfile) {
		return fmt.Errorf("importfile is required")
	}

	content, err := os.ReadFile(importfile)
	if err != nil {
		return err
	}

	// Replace fromdom with todom in content
	updatedContent := strings.ReplaceAll(string(content), fromdom, todom)

	var allObjs map[string]any
	if err := json.Unmarshal([]byte(updatedContent), &allObjs); err != nil {
		return err
	}

	objectTypes := []string{"users", "groups", "comptypes", "credentials", "endpoints",
		"datasources", "tasks", "engines", "repositories", "environments", "components", "applications", "releases"}

	for _, objType := range objectTypes {
		util.ImportDict(client, objType, allObjs)
	}

	return nil
}
