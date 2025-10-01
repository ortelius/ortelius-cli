// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/models"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/spf13/cobra"
)

var assignCmd = &cobra.Command{
	Use:   "assign",
	Short: "Assign component version to application version",
	Long:  "Assigns a component version to an application version",
	RunE:  runAssign,
}

func init() {
	assignCmd.Flags().StringVar(&compname, "compname", "", "Component Name")
	assignCmd.Flags().StringVar(&compvariant, "compvariant", "", "Component Variant")
	assignCmd.Flags().StringVar(&compversion, "compversion", "", "Component Version")
	assignCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	assignCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")
	assignCmd.Flags().StringVar(&appautoinc, "appautoinc", "", "Application Auto Increment Version")
	assignCmd.Flags().StringVar(&deploydatasave, "deploydatasave", "", "JSON file to save deployment data")
	assignCmd.Flags().StringSliceVar(&envs, "envs", []string{}, "Environments to Associate App to")

	RootCmd.AddCommand(assignCmd)
}

func runAssign(_ *cobra.Command, _ []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if util.IsEmpty(appname) {
		return fmt.Errorf("appname is required")
	}
	if util.IsEmpty(compname) {
		return fmt.Errorf("compname is required")
	}

	// Handle variant/version parsing
	if util.IsEmpty(compvariant) && strings.Contains(compversion, "-v") {
		parts := strings.Split(compversion, "-v")
		compvariant = parts[0]
		compversion = "v" + parts[1]
	}
	if util.IsEmpty(compvariant) && strings.Contains(compversion, "-V") {
		parts := strings.Split(compversion, "-V")
		compvariant = parts[0]
		compversion = "v" + parts[1]
	}

	assignCompleted := []string{}
	deployDataDict := models.DeployData{}

	// Load existing deploy data if specified
	if util.IsNotEmpty(deploydatasave) && util.FileExists(deploydatasave) {
		content, err := os.ReadFile(deploydatasave)
		if err == nil {
			json.Unmarshal(content, &deployDataDict)
		}
	}

	saveAppVer := appversion
	cnt := 1

	for {
		// Get component
		compID, name := client.GetComponent(compname, compvariant, compversion, true, false)
		if compID <= 0 {
			return fmt.Errorf("component not found: %s", compname)
		}

		fmt.Printf("Found %s\n", name)

		currentAppVersion := saveAppVer
		currentAppName := appname

		// Parse appname;appversion format
		if util.IsEmpty(currentAppVersion) && strings.Contains(currentAppName, ";") {
			parts := strings.Split(currentAppName, ";")
			if len(parts) == 3 {
				currentAppName = parts[0] + ";" + parts[1]
				currentAppVersion = parts[2]
			}
		}

		// Get or create application
		appID, _, _ := client.GetApplication(currentAppName, currentAppVersion, true)

		if appID < 0 {
			fmt.Printf("Creating Application Version '%s' '%s'\n", currentAppName, currentAppVersion)
			appAutoIncBool := strings.ToLower(appautoinc) == "y"
			newAppID, _ := client.NewApplication(currentAppName, currentAppVersion, appAutoIncBool, envs, compID)
			appID = newAppID
			currentAppName = client.GetApplicationName(appID)
			fmt.Printf("Creation Done: %s\n", currentAppName)
		}

		// Assign to environments
		if !util.Contains(assignCompleted, currentAppName) {
			client.AssignAppToEnv(currentAppName, envs)
			assignCompleted = append(assignCompleted, currentAppName)
		}

		fullAppName := client.GetApplicationName(appID)
		fullCompName := client.GetComponentName(compID)

		fmt.Printf("Assigning Component Version %s to Application Version %s\n", name, fullAppName)

		deployDataDict.Application = fullAppName
		deployDataDict.CompVersion = append(deployDataDict.CompVersion, fullCompName)

		client.AddCompVerToAppVer(appID, compID)
		fmt.Println("Assignment Done")

		// Check for next component in environment variables
		compname = os.Getenv(fmt.Sprintf("COMPONENT_NAME_%d", cnt))
		compversion = os.Getenv(fmt.Sprintf("COMPONENT_VERSION_%d", cnt))
		appname = os.Getenv(fmt.Sprintf("COMPONENT_APPLICATION_%d", cnt))
		appversion = os.Getenv(fmt.Sprintf("COMPONENT_APPLICATION_VERSION_%d", cnt))

		cnt++

		if util.IsEmpty(compname) {
			break
		}
	}

	// Save deploy data
	if util.IsNotEmpty(deploydatasave) {
		content, err := json.MarshalIndent(deployDataDict, "", "  ")
		if err == nil {
			os.WriteFile(deploydatasave, content, 0644)
		}
	}

	return nil
}
