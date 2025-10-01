// Package config provides configuration management for the Ortelius CLI application.
package config

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"text/template"
	"time"

	"github.com/BurntSushi/toml"
	"github.com/mitchellh/mapstructure"
	"github.com/ortelius/ortelius-cli/internal/models"
	"github.com/ortelius/ortelius-cli/internal/util"
	"github.com/ortelius/ortelius-cli/pkg/ortelius"
	"github.com/spf13/viper"
)

// GetConfigAndInit initializes the client and loads configuration
func GetConfigAndInit() (*models.ComponentConfig, *ortelius.Client, error) {
	// Get values from viper (environment variables) and command flags
	// Try ortelius* environment variables first, fall back to dh* for backward compatibility
	orteliusURL := viper.GetString("ortelius-url")
	if orteliusURL == "" {
		orteliusURL = viper.GetString("dhurl")
	}

	orteliusUser := viper.GetString("ortelius-user")
	if orteliusUser == "" {
		orteliusUser = viper.GetString("dhuser")
	}

	orteliusPass := viper.GetString("ortelius-pass")
	if orteliusPass == "" {
		orteliusPass = viper.GetString("dhpass")
	}

	// Get global flags from root command
	globalOrteliusURL, globalOrteliusUser, globalOrteliusPass, rsp := getGlobalFlags()

	if orteliusURL == "" {
		orteliusURL = globalOrteliusURL
	}
	if orteliusUser == "" {
		orteliusUser = globalOrteliusUser
	}
	if orteliusPass == "" {
		orteliusPass = globalOrteliusPass
	}

	// Initialize client
	client := ortelius.NewClient(orteliusURL)

	// Login
	if util.IsEmpty(orteliusURL) || util.IsEmpty(orteliusUser) || util.IsEmpty(orteliusPass) {
		return nil, nil, fmt.Errorf("dhurl, dhuser, and dhpass are required")
	}

	if err := client.Login(orteliusUser, orteliusPass); err != nil {
		return nil, nil, fmt.Errorf("login failed: %w", err)
	}

	// Handle RSP file
	if !util.FileExists(rsp) {
		var err error
		if rsp, err = generateDefaultRSP(); err != nil {
			return nil, nil, err
		}
		defer os.Remove(rsp) // Clean up generated file
	}

	// Load and process configuration
	config, err := loadAndProcessConfig(rsp)
	if err != nil {
		return nil, nil, err
	}

	return config, client, nil
}

func generateDefaultRSP() (string, error) {
	org := strings.TrimSpace(util.RunCmd("git config --get remote.origin.url | awk -F'[@:/]' '{print $(NF-1)}'"))
	repo := strings.TrimSpace(util.RunCmd("git config --get remote.origin.url | awk -F/ '{print $NF}'| sed 's/.git$//'"))
	branch := strings.TrimSpace(util.RunCmd("git rev-parse --abbrev-ref HEAD"))
	bldnum := strings.TrimSpace(util.RunCmd("git log --oneline | wc -l | tr -d ' '"))

	content := fmt.Sprintf(`Name = "GLOBAL.%s.%s"
Variant = "%s"
Version = "v%s"
`, org, repo, branch, bldnum)

	var err error
	if repo != "" {
		err = os.WriteFile("generated-component.toml", []byte(content), 0644)
	}

	return "generated-component.toml", err
}

// PreprocessTemplate converts ${Var} to {{.Var}} for Go templates
func PreprocessTemplate(s string) string {
	return strings.ReplaceAll(strings.ReplaceAll(s, "${", "{{."), "}", "}}")
}

// BuildVarsMap initializes the variable map from top-level fields + environment
func BuildVarsMap(cfg map[string]any) map[string]string {
	vars := make(map[string]string)
	for k, v := range cfg {
		if s, ok := v.(string); ok {
			vars[k] = s
		}
	}
	for _, e := range os.Environ() {
		parts := strings.SplitN(e, "=", 2)
		if len(parts) == 2 {
			vars[parts[0]] = parts[1]
		}
	}

	// Set BLDDATE if not present
	if vars["BLDDATE"] == "" {
		vars["BLDDATE"] = time.Now().Format(time.RFC3339)
	} else {
		vars["BLDDATE"] = strings.Trim(vars["BLDDATE"], `"`)
	}
	return vars
}

// ResolveMap recursively substitutes {{.Var}} placeholders in map[string]any
func ResolveMap(m map[string]any, vars map[string]string) error {
	inProgress := make(map[string]bool)
	return resolveMapRec(m, vars, inProgress)
}

// Helper to recursively resolve with cycle detection
func resolveMapRec(m map[string]any, vars map[string]string, inProgress map[string]bool) error {
	for k, v := range m {
		switch val := v.(type) {
		case string:
			if inProgress[k] {
				return fmt.Errorf("cycle detected while resolving key %s", k)
			}
			inProgress[k] = true
			newVal, err := ResolveString(val, vars)
			if err != nil {
				return fmt.Errorf("key %s: %w", k, err)
			}
			m[k] = newVal
			vars[k] = newVal
			inProgress[k] = false
		case map[string]any:
			if err := resolveMapRec(val, vars, inProgress); err != nil {
				return err
			}
		case []any:
			for i, item := range val {
				switch s := item.(type) {
				case string:
					newVal, err := ResolveString(s, vars)
					if err != nil {
						return err
					}
					val[i] = newVal
				case map[string]any:
					if err := resolveMapRec(s, vars, inProgress); err != nil {
						return err
					}
				}
			}
		}
	}
	return nil
}

// ResolveString substitutes a string using vars and Go templates
func ResolveString(s string, vars map[string]string) (string, error) {
	tmpl, err := template.New("tpl").Parse(PreprocessTemplate(s))
	if err != nil {
		return "", err
	}
	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, vars); err != nil {
		return "", err
	}
	return buf.String(), nil
}

func loadAndProcessConfig(filename string) (*models.ComponentConfig, error) {
	// First substitution with environment variables
	var config models.ComponentConfig

	if !util.FileExists(filename) {
		return &config, nil
	}

	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}

	var input map[string]any
	if strings.HasSuffix(strings.ToLower(filename), ".toml") {
		if err := toml.Unmarshal(data, &input); err != nil {
			return nil, err
		}

		vars := BuildVarsMap(input)

		if err := ResolveMap(input, vars); err != nil {
			return nil, err
		}
	} else {
		if err := json.Unmarshal(data, &input); err != nil {
			return nil, err
		}
	}

	if err := mapstructure.Decode(input, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

// getGlobalFlags is a placeholder - needs to be imported from cmd package
// This is a workaround for the circular dependency
var getGlobalFlags = func() (string, string, string, string) {
	return "", "", "", "component.toml"
}

// SetGlobalFlagsGetter allows the cmd package to set this function
func SetGlobalFlagsGetter(fn func() (string, string, string, string)) {
	getGlobalFlags = fn
}
