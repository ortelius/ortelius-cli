package util

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"text/template"

	"github.com/BurntSushi/toml"
	"github.com/ortelius/dh-cli/internal/types"
)

// CreateEnvScript creates a bash script from environment variables
func CreateEnvScript(envvarsFile, outputFile string) error {
	var fpScript *os.File
	var err error

	mapping := make(map[string]string)

	if IsNotEmpty(outputFile) {
		fpScript, err = os.OpenFile(outputFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0755)
		if err != nil {
			return err
		}
		defer fpScript.Close()
	}

	// Get environment mapping with derived git values
	mapping = GetDerivedEnvMapping(mapping)

	var vardict types.ComponentConfig
	if FileExists(envvarsFile) {
		content, err := os.ReadFile(envvarsFile)
		if err != nil {
			return err
		}

		// Process template
		tmpl, err := template.New("envscript").Parse(string(content))
		if err != nil {
			return err
		}

		var buf strings.Builder
		if err := tmpl.Execute(&buf, mapping); err != nil {
			return err
		}

		if err := toml.Unmarshal([]byte(buf.String()), &vardict); err != nil {
			return err
		}
	}

	// Merge attributes into main map
	for k, v := range vardict.Attributes {
		mapping[k] = v
	}

	// Handle git metrics calculations
	if mapping["GIT_TOTAL_COMMITTERS_CNT"] == "" && vardict.Attributes["GitTotalCommittersCnt"] != "" {
		mapping["GIT_TOTAL_COMMITTERS_CNT"] = vardict.Attributes["GitTotalCommittersCnt"]
	}

	if mapping["GIT_COMMITTERS_CNT"] == "" && mapping["GIT_COMMIT_AUTHORS"] != "" {
		authors := strings.Split(mapping["GIT_COMMIT_AUTHORS"], ",")
		mapping["GIT_COMMITTERS_CNT"] = strconv.Itoa(len(authors))
	}

	// Calculate contribution percentage
	if mapping["GIT_COMMITTERS_CNT"] != "" && mapping["GIT_TOTAL_COMMITTERS_CNT"] != "" {
		committersCnt, _ := strconv.Atoi(mapping["GIT_COMMITTERS_CNT"])
		totalCnt, _ := strconv.Atoi(mapping["GIT_TOTAL_COMMITTERS_CNT"])
		if totalCnt > 0 {
			percentage := float64(committersCnt) / float64(totalCnt) * 100
			mapping["GIT_CONTRIB_PERCENTAGE"] = strconv.Itoa(int(percentage))
		}
	}

	// Get export variables
	exportVars := make(map[string]string)
	for k, v := range vardict.Export {
		exportVars[k] = v
	}

	// Add all mapping values to export
	for k, v := range mapping {
		if _, exists := exportVars[k]; !exists {
			exportVars[k] = v
		}
	}

	// Handle git previous commit if component name available
	if vardict.Name != "" {
		// This would require dhapi client to get previous commit
		// For now, set defaults
		exportVars["GIT_PREVIOUS_COMPONENT_COMMIT"] = ""
		exportVars["GIT_LINES_ADDED"] = "0"
		exportVars["GIT_LINES_DELETED"] = "0"
	}

	// Add basename
	if cwd, err := os.Getwd(); err == nil {
		exportVars["BASENAME"] = filepath.Base(cwd)
	}

	// Sort and write export variables
	var keys []string
	for k := range exportVars {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	for _, key := range keys {
		value := exportVars[key]

		// Process template substitution
		tmpl, err := template.New("value").Parse(value)
		if err == nil {
			var buf strings.Builder
			tmpl.Execute(&buf, mapping)
			value = buf.String()
		}

		if fpScript != nil {
			fmt.Fprintf(fpScript, "export %s=\"%s\"\n", key, value)
		}

		os.Setenv(key, value)
	}

	return nil
}
