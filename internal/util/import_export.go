// Package util provides utility functions for import/export operations in the Ortelius CLI.
//
//revive:disable-next-line:var-naming
package util

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/ortelius/ortelius-cli/pkg/ortelius"
)

// FilterDict filters objects by domain for export
func FilterDict(client *ortelius.Client, objType, fromDom string, allObjs map[string]any) {
	endpoint := fmt.Sprintf("/dmadminweb/API/export/%s", objType)
	data, err := client.GetJSON(endpoint)
	if err != nil {
		return
	}

	var objList []interface{}
	if objects, ok := data[objType].([]interface{}); ok {
		for _, obj := range objects {
			if objMap, ok := obj.(map[string]any); ok {
				if objName, ok := objMap["objname"].(string); ok {
					if strings.Contains(strings.ToLower(objName), strings.ToLower(fromDom)) {
						objList = append(objList, obj)
					}
				}
			}
		}
	}

	allObjs[objType] = objList
}

// ImportDict imports objects from export data
func ImportDict(client *ortelius.Client, objType string, allObjs map[string]any) {
	fmt.Println(objType)

	if objects, ok := allObjs[objType].([]interface{}); ok {
		for _, obj := range objects {
			fmt.Printf("%+v\n", obj)

			jsonData, err := json.MarshalIndent(obj, "", "  ")
			if err != nil {
				continue
			}

			endpoint := "/dmadminweb/API/import/"
			result, err := client.PostJSON(endpoint, jsonData)
			if err != nil {
				fmt.Printf("Import error: %v\n", err)
				continue
			}

			fmt.Printf("%+v\n", result)
		}
	}
}
