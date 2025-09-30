package util

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v2"
)

// IsEmpty checks if a string is empty or contains only whitespace
func IsEmpty(s string) bool {
	return len(strings.TrimSpace(s)) == 0
}

// IsNotEmpty checks if a string is not empty
func IsNotEmpty(s string) bool {
	return !IsEmpty(s)
}

// FileExists checks if a file exists
func FileExists(filename string) bool {
	_, err := os.Stat(filename)
	return err == nil
}

// CleanName removes periods and dashes from the name, replacing with underscores
func CleanName(name string) string {
	if name == "" {
		return name
	}
	name = strings.ReplaceAll(name, ".", "_")
	name = strings.ReplaceAll(name, "-", "_")
	return name
}

// GetEnvOrDefault returns environment variable value or default
func GetEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// Contains checks if a string slice contains an item
func Contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// FindChartPath finds a Helm chart file
func FindChartPath(shortname string) string {
	paths := []string{
		filepath.Join("helm", shortname, "Chart.yaml"),
		filepath.Join("helm", shortname, "Chart.yml"),
		filepath.Join("chart", shortname, "Chart.yaml"),
		filepath.Join("chart", shortname, "Chart.yml"),
		filepath.Join("charts", shortname, "Chart.yaml"),
		filepath.Join("charts", shortname, "Chart.yml"),
	}

	for _, path := range paths {
		if FileExists(path) {
			return path
		}
	}
	return ""
}

// ExtractChartVersion extracts version from a Helm chart file
func ExtractChartVersion(chartPath string) string {
	content, err := os.ReadFile(chartPath)
	if err != nil {
		return ""
	}

	var chart map[string]interface{}
	if err := yaml.Unmarshal(content, &chart); err != nil {
		return ""
	}

	if version, ok := chart["version"].(string); ok {
		return version
	}
	return ""
}

// FindFile finds the first existing file from a list of candidates
func FindFile(candidates []string) string {
	for _, candidate := range candidates {
		if FileExists(candidate) {
			return candidate
		}
	}
	return ""
}

// RunCmd executes a shell command and returns the trimmed output
func RunCmd(cmd string) string {
	if strings.Contains(cmd, "git") {
		if _, err := os.Stat(".git"); os.IsNotExist(err) {
			return ""
		}
	}

	parts := strings.Fields(cmd)
	if len(parts) == 0 {
		return ""
	}

	var cmdExec *exec.Cmd
	if len(parts) == 1 {
		cmdExec = exec.Command(parts[0])
	} else {
		// For complex shell commands, use sh -c
		if strings.Contains(cmd, "|") || strings.Contains(cmd, "&&") || strings.Contains(cmd, "||") || strings.Contains(cmd, ";") {
			cmdExec = exec.Command("sh", "-c", cmd)
		} else {
			cmdExec = exec.Command(parts[0], parts[1:]...)
		}
	}

	output, err := cmdExec.Output()
	if err != nil {
		return ""
	}

	return strings.TrimSpace(string(output))
}

// GetStringOrDefault returns value or default if empty
func GetStringOrDefault(value, defaultValue string) string {
	if value == "" {
		return defaultValue
	}
	return value
}
