// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"encoding/json"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/models"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/spf13/cobra"
)

var (
	compname       string
	compvariant    string
	compversion    string
	compautoinc    string
	appautoinc     string
	deploydatasave string
	kvconfig       string
	crdatasource   string
	changerequest  []string
	kind           string
	compattrs      []string
	envs           []string
	deppkgs        []string
	consumes       string
	provides       string
)

var updatecompCmd = &cobra.Command{
	Use:   "updatecomp",
	Short: "Create/replace component version for application version",
	Long:  "Create or replace the component version for the application version",
	RunE:  runUpdateComp,
}

func init() {
	updatecompCmd.Flags().StringVar(&compname, "compname", "", "Component Name")
	updatecompCmd.Flags().StringVar(&compvariant, "compvariant", "", "Component Variant")
	updatecompCmd.Flags().StringVar(&compversion, "compversion", "", "Component Version")
	updatecompCmd.Flags().StringVar(&compautoinc, "compautoinc", "", "Component Auto Increment Version")
	updatecompCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	updatecompCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")
	updatecompCmd.Flags().StringVar(&appautoinc, "appautoinc", "", "Application Auto Increment Version")
	updatecompCmd.Flags().StringVar(&deploydatasave, "deploydatasave", "", "JSON file to save new component and application version names")
	updatecompCmd.Flags().StringVar(&deployenv, "deployenv", "", "Deployment Environment")
	updatecompCmd.Flags().StringVar(&kind, "kind", "docker", "Component Item Type (docker/file)")
	updatecompCmd.Flags().StringSliceVar(&compattrs, "compattr", []string{}, "Component Attributes (key:value)")
	updatecompCmd.Flags().StringSliceVar(&envs, "envs", []string{}, "Environments to Associate App to")
	updatecompCmd.Flags().StringSliceVar(&deppkgs, "deppkg", []string{}, "Dependency package files (type@filename)")
	updatecompCmd.Flags().StringVar(&consumes, "consumes", "", "JSON file listing endpoints being consumed")
	updatecompCmd.Flags().StringVar(&provides, "provides", "", "JSON file listing endpoints being provided")
	updatecompCmd.Flags().StringVar(&crdatasource, "crdatasource", "", "Change Request Data Source")
	updatecompCmd.Flags().StringSliceVar(&changerequest, "changerequest", []string{}, "Change Request IDs")
	updatecompCmd.Flags().StringVar(&kvconfig, "kvconfig", "", "Directory containing JSON and properties files")

	RootCmd.AddCommand(updatecompCmd)
}

func runUpdateComp(_ *cobra.Command, _ []string) error {
	cfg, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	// Override with config values
	if util.IsEmpty(compname) {
		compname = cfg.Name
	}
	if util.IsEmpty(compvariant) {
		compvariant = cfg.Variant
	}
	if util.IsEmpty(compversion) {
		compversion = cfg.Version
	}
	if util.IsEmpty(appname) {
		appname = cfg.Application
	}
	if util.IsEmpty(appversion) {
		appversion = cfg.ApplicationVersion
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

	// Clean variant name
	if util.IsNotEmpty(compvariant) {
		compvariant = strings.ReplaceAll(compvariant, "/", "_")
	}

	// Set default auto increment
	if util.IsEmpty(compautoinc) {
		compautoinc = "Y"
	}
	compAutoIncBool := strings.ToLower(compautoinc) == "y" || compautoinc == "true"

	deployDataDict := models.DeployData{
		Application: "",
		CompVersion: []string{},
		RC:          0,
	}

	// Load existing deploy data if specified
	if util.IsNotEmpty(deploydatasave) && util.FileExists(deploydatasave) {
		content, err := os.ReadFile(deploydatasave)
		if err == nil {
			var existingData models.DeployData
			if json.Unmarshal(content, &existingData) == nil {
				deployDataDict = existingData
			}
		}
	}

	cnt := 1
	saveAppVer := appversion

	for {
		parentCompid, _ := client.GetComponent(compname, "", "", true, true)
		if parentCompid < 0 {
			parentCompid, _ = client.GetComponent(compname, compvariant, "", true, true)
		}

		if parentCompid < 0 {
			fmt.Println("Creating Parent Component")
			parentCompid = client.NewComponentVersion(compname, compvariant, "", kind, compAutoIncBool)
			parentCompName := client.GetComponentName(parentCompid)
			fmt.Printf("Creation Done: %s\n", parentCompName)
		}

		// Create component version
		fmt.Println("Creating Component")
		compID := client.NewComponentVersion(compname, compvariant, compversion, kind, compAutoIncBool)

		if compID < 0 {
			return fmt.Errorf("failed to create component")
		}

		fullCompName := client.GetComponentName(compID)
		deployDataDict.CompVersion = append(deployDataDict.CompVersion, fullCompName)

		fmt.Printf("Creation Done: %s\n", fullCompName)

		// Update attributes
		attrs := make(map[string]string)

		// Process config attributes
		maps.Copy(attrs, cfg.Attributes)

		// Process command line attributes
		for _, attr := range compattrs {
			if strings.Contains(attr, ":") {
				parts := strings.SplitN(attr, ":", 2)
				key := parts[0]
				value := parts[1]

				if strings.Contains(value, "@sha256:") {
					value = strings.Split(value, "@sha256:")[1]
				}

				if strings.HasPrefix(value, "@") {
					value = value[1:]
					if util.FileExists(value) {
						content, err := os.ReadFile(value)
						if err == nil {
							attrs[key] = strings.ReplaceAll(string(content), "\n", "")
						} else {
							attrs[key] = ""
						}
					} else {
						attrs[key] = ""
					}
				} else {
					attrs[key] = value
				}
			}
		}

		attrs = util.GetDerivedEnvMapping(attrs)

		// Auto-detect chart information
		shortname := compname
		if strings.Contains(shortname, ".") {
			parts := strings.Split(shortname, ".")
			shortname = parts[len(parts)-1]
		}

		chartPath := util.FindChartPath(shortname)
		if chartPath != "" {
			attrs["Chart"] = filepath.Dir(chartPath)
			if chartVersion := util.ExtractChartVersion(chartPath); chartVersion != "" {
				attrs["ChartVersion"] = chartVersion
			}
		}

		fmt.Printf("Updating Component Attributes\n")

		keys := make([]string, 0, len(attrs))
		for k := range attrs {
			keys = append(keys, k)
		}
		sort.Strings(keys)

		// Print sorted
		for _, key := range keys {
			fmt.Printf("%s: %s\n", key, attrs[key])
		}

		// Update component attributes
		success, _, _ := client.UpdateCompIDAttrs(compID, attrs, crdatasource, changerequest)
		if !success {
			return fmt.Errorf("failed to update component attributes")
		}

		// Handle file uploads
		readmeFile := util.FindFile([]string{"README", "README.md", "readme", "readme.md"})
		if readmeFile != "" {
			client.PostTextFile(compID, readmeFile, "readme")
		}

		licenseFile := util.FindFile([]string{"LICENSE", "LICENSE.md", "license", "license.md"})
		if licenseFile != "" {
			client.PostTextFile(compID, licenseFile, "license")
		}

		swaggerFile := util.FindFile([]string{"swagger.yaml", "swagger.yml", "swagger.json", "openapi.json", "openapi.yaml", "openapi.yml"})
		if swaggerFile != "" {
			client.PostTextFile(compID, swaggerFile, "swagger")
		}

		// Handle dependency packages
		var glic map[string]interface{}
		for _, filename := range deppkgs {
			if strings.HasPrefix(filename, "gradlelicense@") {
				actualFile := strings.TrimPrefix(filename, "gradlelicense@")
				if util.FileExists(actualFile) {
					content, err := os.ReadFile(actualFile)
					if err == nil {
						json.Unmarshal(content, &glic)
					}
				}
			} else {
				result := client.UpdateDepPkgs(compID, filename, glic)
				fmt.Printf("Dependency package result: %+v\n", result)
			}
		}

		// Handle consumes/provides endpoints
		if util.IsNotEmpty(consumes) && util.FileExists(consumes) {
			fmt.Println("Adding Consuming End Points")
		}

		if util.IsNotEmpty(provides) && util.FileExists(provides) {
			fmt.Println("Adding Providing End Points")
		}

		// Handle KV config
		if util.IsNotEmpty(kvconfig) {
			fmt.Printf("Load config from %s\n", kvconfig)
			client.SetKVConfig(kvconfig, compname, compvariant, compversion, crdatasource, changerequest)
		}

		// Handle application assignment
		var appList []string

		if util.IsEmpty(appname) && strings.ToLower(appautoinc) == "y" {
			// Derive appname from component
			parentCompID, _ := client.GetComponent(compname, "", "", true, true)
			if parentCompID > 0 {
				compData := client.GetComponentFromID(parentCompID)
				if result, ok := compData["result"].(map[string]interface{}); ok {
					if apps, ok := result["applications"].([]interface{}); ok {
						for _, app := range apps {
							if appMap, ok := app.(map[string]interface{}); ok {
								domain := appMap["domain"].(string)
								name := appMap["name"].(string)
								appID := int(appMap["id"].(float64))

								fullAppName := domain + "." + name
								latestAppID, _, _ := client.GetApplication(fullAppName, "latest", true)

								if appID == latestAppID {
									appList = append(appList, fullAppName)
								}
							}
						}
					}
				}
			}
		} else if util.IsNotEmpty(appname) {
			appList = append(appList, appname)
		}

		// Process applications
		for _, appName := range appList {
			currentAppVersion := saveAppVer
			if util.IsEmpty(currentAppVersion) {
				// Parse app;version format
				if strings.Contains(appName, ";") {
					parts := strings.Split(appName, ";")
					if len(parts) == 3 {
						appName = parts[0] + ";" + parts[1]
						currentAppVersion = parts[2]
					}
				}
			}

			fmt.Printf("Application Version Definition: '%s' '%s' AppAutoInc: %s\n",
				appName, currentAppVersion, appautoinc)

			appAutoIncBool := strings.ToLower(appautoinc) == "y"
			newAppID, fullAppName := client.NewApplication(appName, currentAppVersion, appAutoIncBool, envs, compID)

			if newAppID < 0 {
				return fmt.Errorf("failed to create application: %s", fullAppName)
			}

			realAppName := client.GetApplicationName(newAppID)
			fmt.Printf("Using Application Version: %s\n", realAppName)

			deployDataDict.Application = realAppName

			fmt.Printf("Assigning Component Version to Application Version %s\n", realAppName)
			client.AddCompVerToAppVer(newAppID, compID)
			fmt.Println("Assignment Done")

			// Deploy if environment specified
			if util.IsNotEmpty(deployenv) {
				fmt.Printf("Deploying %s to %s\n", realAppName, deployenv)
				deployID, errMsg := client.DeployApplicationByID(newAppID, deployenv)

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
