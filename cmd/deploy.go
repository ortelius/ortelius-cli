// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/ortelius/ortelius-cli/internal/models"
	"github.com/ortelius/ortelius-cli/pkg/ortelius"
	"github.com/spf13/cobra"
)

var (
	appname       string
	appversion    string
	deployenv     string
	deploydata    string
	namespace     string
	logdeployment bool
)

var deployCmd = &cobra.Command{
	Use:   "deploy",
	Short: "Deploy application to environment",
	Long:  "Deploy the application to the specified environment",
	RunE:  runDeploy,
}

func init() {
	deployCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	deployCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")
	deployCmd.Flags().StringVar(&deployenv, "deployenv", "", "Deployment Environment")
	deployCmd.Flags().StringVar(&deploydata, "deploydata", "", "JSON file containing application, environment and log details")
	deployCmd.Flags().StringVar(&namespace, "namespace", "", "Kubernetes namespace to map image tag to application version")
	deployCmd.Flags().BoolVar(&logdeployment, "logdeployment", false, "Records a deployment by external program")

	RootCmd.AddCommand(deployCmd)
}

func runDeploy(_ *cobra.Command, _ []string) error {
	cfg, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	// Override with config values if not set
	if util.IsEmpty(appname) {
		appname = cfg.Application
	}
	if util.IsEmpty(appversion) {
		appversion = cfg.ApplicationVersion
	}

	if util.IsEmpty(deploydata) {
		return deployDirect(client)
	}

	return deployFromData(client)
}

func deployDirect(client *ortelius.Client) error {
	if util.IsEmpty(appname) {
		return fmt.Errorf("appname is required")
	}

	var appList []map[string]interface{}

	if util.IsNotEmpty(appname) {
		// Parse appname;appversion format
		if util.IsEmpty(appversion) && strings.Contains(appname, ";") {
			parts := strings.Split(appname, ";")
			if len(parts) == 3 {
				appname = parts[0] + ";" + parts[1]
				appversion = parts[2]
			}
		}

		appID, fullAppName, _ := client.GetApplication(appname, appversion, true)
		if util.IsEmpty(deployenv) {
			return fmt.Errorf("deployenv is required")
		}

		appList = append(appList, map[string]interface{}{
			"appid":     appID,
			"appname":   fullAppName,
			"deployenv": deployenv,
		})
	}

	retCode := 0
	for _, entry := range appList {
		appID := entry["appid"].(int)
		appName := entry["appname"].(string)
		deployEnv := entry["deployenv"].(string)

		fmt.Printf("Deploying %s to %s\n", appName, deployEnv)
		deployID, errMsg := client.DeployApplicationByID(appID, deployEnv)

		if deployID < 0 {
			fmt.Println(errMsg)
			return fmt.Errorf("deployment failed: %s", errMsg)
		}

		fmt.Printf("Fetching Logs for %d\n", deployID)
		success, logs := client.GetLogs(deployID)

		fmt.Println(logs)
		if success {
			fmt.Println("Successful")
		} else {
			fmt.Println("Failed")
			retCode++
		}
	}

	if retCode > 0 {
		return fmt.Errorf("deployment failed")
	}

	return nil
}

func deployFromData(client *ortelius.Client) error {
	content, err := os.ReadFile(deploydata)
	if err != nil {
		return err
	}

	var data models.DeployData
	if err := json.Unmarshal(content, &data); err != nil {
		return err
	}

	// Handle namespace if provided
	if util.IsNotEmpty(namespace) {
		// Get pods from cluster and extract image tags
		output := util.RunCmd("kubectl get pods -A -o json")
		if util.IsNotEmpty(output) {
			var clusterJSON map[string]interface{}
			if err := json.Unmarshal([]byte(output), &clusterJSON); err == nil {
				if items, ok := clusterJSON["items"].([]interface{}); ok {
					for _, item := range items {
						if itemMap, ok := item.(map[string]interface{}); ok {
							if metadata, ok := itemMap["metadata"].(map[string]interface{}); ok {
								if itemNamespace, ok := metadata["namespace"].(string); ok && itemNamespace == namespace {
									if spec, ok := itemMap["spec"].(map[string]interface{}); ok {
										if containers, ok := spec["containers"].([]interface{}); ok {
											for _, container := range containers {
												if containerMap, ok := container.(map[string]interface{}); ok {
													if image, ok := containerMap["image"].(string); ok {
														data.ImageTags = append(data.ImageTags, image)
													}
												}
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}

	// Update data from flags
	if util.IsEmpty(appname) {
		appname = data.Application
	} else {
		data.Application = appname
	}

	if util.IsEmpty(appversion) {
		appversion = data.AppVersion
	} else {
		data.AppVersion = appversion
	}

	// Clean and process app version
	appversion = util.CleanName(appversion)
	data.AppVersion = appversion

	fullAppName := appname
	if util.IsNotEmpty(appversion) {
		fullAppName = fullAppName + ";" + appversion
	}

	// Get application info
	_, _, _ = client.GetApplication(fullAppName, "", false)
	data.Application = fullAppName
	data.AppVersion = "" // Remove appversion from data

	// Set environment
	if util.IsEmpty(deployenv) {
		deployenv = data.Environment
	} else {
		data.Environment = deployenv
	}

	if !logdeployment {
		data.SkipDeploy = "Y"
	}

	// Save updated data
	updatedContent, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}

	if err := os.WriteFile(deploydata, updatedContent, 0644); err != nil {
		return err
	}

	// Log deployment
	deployResult := client.LogDeployApplication(map[string]interface{}{
		"application": data.Application,
		"environment": data.Environment,
		"rc":          data.RC,
		"skipdeploy":  data.SkipDeploy,
	})

	if logdeployment {
		if deployID, ok := deployResult["deployid"].(int); ok {
			fmt.Printf("Logged Deployment for %s to %s\n", data.Application, deployenv)
			_ = deployID
		}
	} else {
		if appID, ok := deployResult["appid"].(int); ok {
			fmt.Printf("Deploying %s to %s\n", data.Application, deployenv)
			deployID, errMsg := client.DeployApplicationByID(appID, deployenv)

			if deployID < 0 {
				fmt.Println(errMsg)
				return fmt.Errorf("deployment failed: %s", errMsg)
			}

			fmt.Printf("Fetching Logs for %d\n", deployID)
			success, logs := client.GetLogs(deployID)

			fmt.Println(logs)
			if success {
				fmt.Println("Successful")
			} else {
				fmt.Println("Failed")
				return fmt.Errorf("deployment failed")
			}
		}
	}

	return nil
}
