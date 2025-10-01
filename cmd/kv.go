// Package cmd provides command-line interface commands for the DeployHub CLI application.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/dhutil"
	"github.com/ortelius/ortelius-cli/internal/models"
	"github.com/spf13/cobra"
)

var kvCmd = &cobra.Command{
	Use:   "kv",
	Short: "Assign key/value pairs to component version",
	Long:  "Assigns the key/value pairs to the component version",
	RunE:  runKV,
}

func init() {
	kvCmd.Flags().StringVar(&kvconfig, "kvconfig", "", "Directory containing JSON and properties files")
	kvCmd.Flags().StringVar(&deploydata, "deploydata", "", "JSON file containing deployment data")
	kvCmd.Flags().StringVar(&compname, "compname", "", "Component Name")
	kvCmd.Flags().StringVar(&compvariant, "compvariant", "", "Component Variant")
	kvCmd.Flags().StringVar(&compversion, "compversion", "", "Component Version")
	kvCmd.Flags().StringVar(&compautoinc, "compautoinc", "Y", "Component Auto Increment Version")
	kvCmd.Flags().StringVar(&kind, "kind", "docker", "Component Item Type")
	kvCmd.Flags().StringVar(&crdatasource, "crdatasource", "", "Change Request Data Source")
	kvCmd.Flags().StringSliceVar(&changerequest, "changerequest", []string{}, "Change Request IDs")

	RootCmd.AddCommand(kvCmd)
}

func runKV(_ *cobra.Command, _ []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if dhutil.IsEmpty(kvconfig) && dhutil.IsEmpty(deploydata) {
		return fmt.Errorf("kvconfig or deploydata is required")
	}

	if dhutil.IsNotEmpty(deploydata) {
		content, err := os.ReadFile(deploydata)
		if err != nil {
			return err
		}

		var data models.DeployData
		if err := json.Unmarshal(content, &data); err != nil {
			return err
		}

		appname = data.Application
		appversion = data.AppVersion
		compname = data.ConfigComponent
		compvariant = data.Environment
		compversion = ""

		if dhutil.IsEmpty(kvconfig) {
			kvconfig = data.KvConfig
		}

		fmt.Printf("Config for %s to %s\n", appname, compvariant)
	}

	if dhutil.IsEmpty(compname) {
		return fmt.Errorf("compname is required")
	}

	// Clean variant
	if strings.Contains(compvariant, ".") {
		parts := strings.Split(compvariant, ".")
		compvariant = parts[len(parts)-1]
	}

	if dhutil.IsEmpty(compautoinc) {
		compautoinc = "Y"
	}

	client.SetKVConfig(kvconfig, compname, compvariant, compversion, crdatasource, changerequest)

	return nil
}
