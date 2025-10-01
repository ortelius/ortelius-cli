// Package cmd provides command-line interface commands for the Ortelius CLI application.
package cmd

import (
	"fmt"
	"strings"

	"github.com/ortelius/ortelius-cli/internal/config"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/spf13/cobra"
)

var (
	clusterjson string
	msname      string
	msbranch    string
)

var clusterCmd = &cobra.Command{
	Use:   "cluster",
	Short: "Sync cluster configuration",
	Long:  "Sync cluster from Kubernetes JSON configuration",
	RunE:  runCluster,
}

func init() {
	clusterCmd.Flags().StringVar(&appname, "appname", "", "Application Name")
	clusterCmd.Flags().StringVar(&appversion, "appversion", "", "Application Version")
	clusterCmd.Flags().StringVar(&appautoinc, "appautoinc", "", "Application Auto Increment Version")
	clusterCmd.Flags().StringVar(&clusterjson, "cluster_json", "", "JSON from kubectl get deploy -n default -o json")
	clusterCmd.Flags().StringVar(&todom, "todom", "", "To Domain")
	clusterCmd.Flags().StringVar(&msname, "msname", "", "New microservice being added to cluster")
	clusterCmd.Flags().StringVar(&msbranch, "msbranch", "", "New microservice branch being added to cluster")
	clusterCmd.Flags().StringVar(&deployenv, "deployenv", "", "Deployment Environment")
	clusterCmd.Flags().StringVar(&crdatasource, "crdatasource", "", "Change Request Data Source")
	clusterCmd.Flags().StringSliceVar(&changerequest, "changerequest", []string{}, "Change Request IDs")

	RootCmd.AddCommand(clusterCmd)
}

func runCluster(_ *cobra.Command, _ []string) error {
	_, client, err := config.GetConfigAndInit()
	if err != nil {
		return err
	}

	if util.IsEmpty(appname) {
		return fmt.Errorf("appname is required")
	}
	if util.IsEmpty(clusterjson) {
		return fmt.Errorf("cluster_json is required")
	}
	if util.IsEmpty(todom) {
		return fmt.Errorf("todom is required")
	}

	// Parse appname;appversion format
	if util.IsEmpty(appversion) && strings.Contains(appname, ";") {
		parts := strings.Split(appname, ";")
		if len(parts) == 3 {
			appname = parts[0] + ";" + parts[1]
			appversion = parts[2]
		}
	}

	fmt.Printf("Syncing cluster from %s\n", clusterjson)

	appAutoIncBool := strings.ToLower(appautoinc) == "y"
	client.ImportCluster(todom, appname, appversion, appAutoIncBool, deployenv, crdatasource, changerequest, clusterjson, msname, msbranch)

	return nil
}
