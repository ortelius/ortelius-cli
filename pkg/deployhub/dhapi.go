// Package deployhub provides a Go client for the DeployHub REST API
// This is a complete conversion from the Python dhapi.py module
package deployhub

import (
	"bytes"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/BurntSushi/toml"
	"github.com/go-ini/ini"
)

// Client represents a DeployHub API client
type Client struct {
	BaseURL    string
	HTTPClient *http.Client
	Cookies    map[string]string
}

// NewClient creates a new DeployHub API client
func NewClient(baseURL string) *Client {
	return &Client{
		BaseURL: strings.TrimSuffix(baseURL, "/"),
		HTTPClient: &http.Client{
			Timeout: 300 * time.Second,
		},
		Cookies: make(map[string]string),
	}
}

// URLValidator validates if a string is a valid URL
func URLValidator(urlStr string) bool {
	_, err := url.Parse(urlStr)
	return err == nil
}

// isEmpty checks if a string is empty or contains only whitespace
func isEmpty(s string) bool {
	return len(strings.TrimSpace(s)) == 0
}

// isNotEmpty checks if a string is not empty
func isNotEmpty(s interface{}) bool {
	switch v := s.(type) {
	case string:
		return len(strings.TrimSpace(v)) > 0
	case int:
		return true
	case map[string]interface{}:
		return true
	default:
		return false
	}
}

// cleanName removes periods and dashes from the name, replacing with underscores
func cleanName(name string) string {
	if name == "" {
		return name
	}
	name = strings.ReplaceAll(name, ".", "_")
	name = strings.ReplaceAll(name, "-", "_")
	return name
}

// SSLCerts handles custom SSL certificates
func (c *Client) SSLCerts() error {
	// Test SSL connection first
	resp, err := c.HTTPClient.Get(c.BaseURL)
	if err != nil {
		if strings.Contains(err.Error(), "certificate") {
			log.Println("Adding custom certs to client...")
			// Create custom transport with insecure TLS for custom certs
			tr := &http.Transport{
				TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
			}
			c.HTTPClient.Transport = tr
		}
		return err
	}
	if resp != nil {
		resp.Body.Close()
	}
	return nil
}

// Login authenticates with DeployHub
func (c *Client) Login(user, password string) error {
	data := url.Values{}
	data.Set("user", user)
	data.Set("pass", password)

	resp, err := c.HTTPClient.PostForm(c.BaseURL+"/dmadminweb/API/login", data)
	if err != nil {
		return fmt.Errorf("login failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("login failed with status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode login response: %w", err)
	}

	success, _ := result["success"].(bool)
	if !success {
		errorMsg, _ := result["error"].(string)
		return fmt.Errorf("login failed: %s", errorMsg)
	}

	token, _ := result["token"].(string)
	c.Cookies["token"] = token
	return nil
}

// getJSON performs a GET request and returns JSON response
func (c *Client) getJSON(endpoint string) (map[string]interface{}, error) {
	req, err := http.NewRequest("GET", c.BaseURL+endpoint, nil)
	if err != nil {
		return nil, err
	}

	// Add cookies
	for key, value := range c.Cookies {
		req.AddCookie(&http.Cookie{Name: key, Value: value})
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("request failed with status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result, nil
}

// postJSON performs a POST request with JSON payload
func (c *Client) postJSON(endpoint string, payload interface{}) (map[string]interface{}, error) {
	var body io.Reader

	switch v := payload.(type) {
	case string:
		body = strings.NewReader(v)
	case []byte:
		body = bytes.NewReader(v)
	default:
		jsonData, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal payload: %w", err)
		}
		body = bytes.NewReader(jsonData)
	}

	req, err := http.NewRequest("POST", c.BaseURL+endpoint, body)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")
	if !strings.Contains(endpoint, "/import") {
		req.Header.Set("host", "console.deployhub.com")
	}

	// Add cookies
	for key, value := range c.Cookies {
		req.AddCookie(&http.Cookie{Name: key, Value: value})
	}

	timeout := 300 * time.Second
	if strings.Contains(endpoint, "/import") {
		timeout = 1800 * time.Second
	}

	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return nil, fmt.Errorf("request failed with status: %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		// Return empty map if JSON decode fails (like Python version)
		return make(map[string]interface{}), nil
	}

	return result, nil
}

// DeployApplicationByID deploys an application by its ID
func (c *Client) DeployApplicationByID(appID int, env string) (int, string) {
	endpoint := fmt.Sprintf("/dmadminweb/API/deploy?app=%d&env=%s&wait=N",
		appID, url.QueryEscape(env))

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1, "Deployment Failed"
	}

	success, _ := data["success"].(bool)
	if success {
		deploymentID, _ := data["deploymentid"].(float64)
		return int(deploymentID), ""
	}

	errorMsg, _ := data["error"].(string)
	return -1, errorMsg
}

// DeployApplication deploys an application by name and version
func (c *Client) DeployApplication(appName, appVersion, env string) (int, string) {
	appID, _, _ := c.GetApplication(appName, appVersion, true)
	if appID == -1 {
		return -1, "Application not found"
	}

	return c.DeployApplicationByID(appID, env)
}

// Component represents component information
type Component struct {
	ID      int    `json:"id"`
	Name    string `json:"name"`
	Variant string `json:"variant,omitempty"`
	Version string `json:"version,omitempty"`
}

// GetComponent retrieves component information
func (c *Client) GetComponent(compName, compVariant, compVersion string, idOnly, latest bool) (int, string) {
	compVariant = cleanName(compVariant)
	compVersion = cleanName(compVersion)

	if compVariant == "" && compVersion != "" {
		compVariant = compVersion
		compVersion = ""
	}

	component := compName
	if compVariant != "" && compVersion != "" {
		component = fmt.Sprintf("%s;%s;%s", compName, compVariant, compVersion)
	} else if compVariant != "" {
		component = fmt.Sprintf("%s;%s", compName, compVariant)
	}

	checkCompName := ""
	shortCompName := ""
	if strings.Contains(compName, ".") {
		parts := strings.Split(compName, ".")
		if len(parts) > 0 {
			shortCompName = parts[len(parts)-1]
		}
	}

	switch {
	case compVariant != "" && compVersion != "":
		checkCompName = fmt.Sprintf("%s;%s;%s", shortCompName, compVariant, compVersion)
	case compVariant != "":
		checkCompName = fmt.Sprintf("%s;%s", shortCompName, compVariant)
	default:
		checkCompName = shortCompName
	}

	params := ""
	if idOnly {
		params += "&idonly=Y"
	}
	if latest {
		params += "&latest=Y"
	}

	endpoint := fmt.Sprintf("/dmadminweb/API/component/?name=%s%s",
		url.QueryEscape(component), params)

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1, ""
	}

	success, _ := data["success"].(bool)
	if !success {
		return -1, ""
	}

	result, _ := data["result"].(map[string]interface{})
	compID, _ := result["id"].(float64)
	name, _ := result["name"].(string)

	if name != checkCompName {
		if versions, ok := result["versions"].([]interface{}); ok {
			for _, ver := range versions {
				if version, ok := ver.(map[string]interface{}); ok {
					if verName, _ := version["name"].(string); verName == checkCompName {
						if verID, ok := version["id"].(float64); ok {
							return int(verID), verName
						}
					}
				}
			}
		}
	}

	return int(compID), name
}

// GetEnvironment retrieves environment information
func (c *Client) GetEnvironment(env string) (int, string) {
	endpoint := fmt.Sprintf("/dmadminweb/API/environment/?name=%s", url.QueryEscape(env))

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1, ""
	}

	success, _ := data["success"].(bool)
	if !success {
		return -1, ""
	}

	result, _ := data["result"].(map[string]interface{})
	envID, _ := result["id"].(float64)
	name, _ := result["name"].(string)

	return int(envID), name
}

// GetApplication retrieves application information
func (c *Client) GetApplication(appName, appVersion string, idOnly bool) (int, string, int) {
	appVersion = cleanName(appVersion)

	application := appName
	if appVersion != "" {
		if strings.ToLower(appVersion) == "latest" {
			application = appName
		} else {
			application = fmt.Sprintf("%s;%s", appName, appVersion)
		}
	}

	params := ""
	if idOnly {
		params += "&idonly=Y"
	}
	if strings.ToLower(appVersion) == "latest" {
		params += "&latest=Y"
	}

	endpoint := fmt.Sprintf("/dmadminweb/API/application/?name=%s%s",
		url.QueryEscape(application), params)

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1, "", -1
	}

	success, _ := data["success"].(bool)
	if !success {
		return -1, "", -1
	}

	result, _ := data["result"].(map[string]interface{})
	appID, _ := result["id"].(float64)
	name, _ := result["name"].(string)

	latest := int(appID)
	if versions, ok := result["versions"].([]interface{}); ok && len(versions) > 0 {
		if lastVer, ok := versions[len(versions)-1].(map[string]interface{}); ok {
			if latestID, ok := lastVer["id"].(float64); ok {
				latest = int(latestID)
			}
		}
	}

	return int(appID), name, latest
}

// IsDeploymentDone checks if deployment is complete
func (c *Client) IsDeploymentDone(deploymentID int) (bool, map[string]interface{}) {
	endpoint := fmt.Sprintf("/dmadminweb/API/log/%d?checkcomplete=Y", deploymentID)

	data, err := c.getJSON(endpoint)
	if err != nil {
		return false, map[string]interface{}{"msg": fmt.Sprintf("Could not get log #%d", deploymentID)}
	}

	if text, ok := data["text"]; ok && text != nil {
		return false, map[string]interface{}{"msg": fmt.Sprintf("Could not get log #%d", deploymentID)}
	}

	return true, data
}

// GetLogs retrieves deployment logs
func (c *Client) GetLogs(deployID int) (bool, string) {
	for {
		done, data := c.IsDeploymentDone(deployID)
		if done {
			if success, _ := data["success"].(bool); success {
				if isComplete, _ := data["iscomplete"].(bool); isComplete {
					break
				}
			} else {
				break
			}
		}
		time.Sleep(10 * time.Second)
	}

	endpoint := fmt.Sprintf("/dmadminweb/API/log/%d", deployID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return false, fmt.Sprintf("Could not get log #%d", deployID)
	}

	if len(data) == 0 {
		return false, fmt.Sprintf("Could not get log #%d", deployID)
	}

	logOutput, _ := data["logoutput"].([]interface{})
	exitCode, _ := data["exitcode"].(float64)

	var output strings.Builder
	for _, line := range logOutput {
		if lineStr, ok := line.(string); ok {
			output.WriteString(lineStr + "\n")
		}
	}

	return int(exitCode) == 0, output.String()
}

// NewComponentVersion creates a new component version
func (c *Client) NewComponentVersion(compName, compVariant, compVersion, kind string, compAutoInc bool) int {
	compVariant = cleanName(compVariant)
	compVersion = cleanName(compVersion)
	var componentItems []map[string]interface{}

	if compVariant == "" && compVersion != "" {
		compVariant = compVersion
		compVersion = ""
	}

	compName = strings.TrimSuffix(compName, ";")
	compVariant = strings.TrimSuffix(compVariant, ";")
	if compVersion != "" {
		compVersion = strings.TrimSuffix(compVersion, ";")
	}

	// Get latest version of component variant
	latestCompID, foundCompName := c.GetComponent(compName, compVariant, compVersion, false, true)
	if latestCompID == -1 {
		latestCompID, foundCompName = c.GetComponent(compName, compVariant, "", false, true)
		if latestCompID == -1 {
			latestCompID, foundCompName = c.GetComponent(compName, "", "", false, true)
		}
	}

	compID := latestCompID
	checkCompName := ""
	shortCompName := ""

	if strings.Contains(compName, ".") {
		parts := strings.Split(compName, ".")
		if len(parts) > 0 {
			shortCompName = parts[len(parts)-1]
		}
	}

	switch {
	case compVariant != "" && compVersion != "":
		checkCompName = fmt.Sprintf("%s;%s;%s", shortCompName, compVariant, compVersion)
	case compVariant != "":
		checkCompName = fmt.Sprintf("%s;%s", shortCompName, compVariant)
	default:
		checkCompName = shortCompName
	}

	// Create base component variant if one is not found
	if latestCompID < 0 {
		if strings.ToLower(kind) == "docker" {
			return c.NewDockerComponent(compName, compVariant, compVersion, -1)
		}
		return c.NewFileComponent(compName, compVariant, compVersion, -1, componentItems)
	}

	// Handle component creation logic based on auto-increment and existing versions
	if !compAutoInc {
		if foundCompName == "" || foundCompName != checkCompName {
			if strings.ToLower(kind) == "docker" {
				return c.NewDockerComponent(compName, compVariant, compVersion, compID)
			}
			return c.NewFileComponent(compName, compVariant, compVersion, compID, componentItems)
		} else if compID > 0 {
			if strings.ToLower(kind) == "docker" {
				c.NewComponentItem(compID, "docker", nil)
			} else {
				c.NewComponentItem(compID, "file", componentItems)
			}
		}
	} else {
		// Handle auto-increment logic
		parts := strings.Split(foundCompName, ";")
		latestCompVersion := ""
		if len(parts) >= 3 {
			latestCompVersion = parts[2]
		} else if len(parts) == 2 {
			latestCompVersion = parts[1]
		}

		verSchema := ""
		gitCommit := ""

		switch {
		case strings.Contains(latestCompVersion, "-g"):
			schemaParts := strings.Split(latestCompVersion, "-g")
			verSchema = schemaParts[0]
			gitCommit = schemaParts[1]
		case strings.Contains(latestCompVersion, "_g"):
			schemaParts := strings.Split(latestCompVersion, "_g")
			verSchema = schemaParts[0]
			gitCommit = schemaParts[1]
		default:
			verSchema = latestCompVersion
		}

		compID = latestCompID
		if compVariant == verSchema {
			verSchema = ""
		}

		// Increment semantic version until we don't have an existing version
		for compID >= 0 {
			if strings.Contains(verSchema, "_") {
				schemaParts := strings.Split(verSchema, "_")
				if len(schemaParts) > 0 {
					if incNum, err := strconv.Atoi(schemaParts[len(schemaParts)-1]); err == nil {
						schemaParts[len(schemaParts)-1] = strconv.Itoa(incNum + 1)
						verSchema = strings.Join(schemaParts, "_") + gitCommit
					}
				}
			} else if num, err := strconv.Atoi(verSchema); err == nil {
				verSchema = strconv.Itoa(num+1) + gitCommit
			} else {
				verSchema = "1" + gitCommit
			}

			compVersion = verSchema
			compID, _ = c.GetComponent(compName, compVariant, compVersion, true, false)
		}

		if strings.ToLower(kind) == "docker" {
			return c.NewDockerComponent(compName, compVariant, compVersion, latestCompID)
		}
		return c.NewFileComponent(compName, compVariant, compVersion, latestCompID, componentItems)
	}

	return compID
}

// NewDockerComponent creates a new Docker component
func (c *Client) NewDockerComponent(compName, compVariant, compVersion string, parentCompID int) int {
	compVariant = cleanName(compVariant)
	compVersion = cleanName(compVersion)

	if compVariant == "" && compVersion != "" {
		compVariant = compVersion
		compVersion = ""
	}

	var compID int
	var endpoint string

	// Create base version
	if parentCompID < 0 {
		if isEmpty(compVariant) {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/?name=%s", url.QueryEscape(compName))
		} else {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/?name=%s", url.QueryEscape(compName+";"+compVariant))
		}
	} else {
		endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/%d", parentCompID)
	}

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1
	}

	if result, ok := data["result"].(map[string]interface{}); ok {
		if id, ok := result["id"].(float64); ok {
			compID = int(id)
		}
	}

	if parentCompID >= 0 {
		c.UpdateName(compName, compVariant, compVersion, compID)
	}

	c.NewComponentItem(compID, "docker", nil)
	return compID
}

// NewFileComponent creates a new file component
func (c *Client) NewFileComponent(compName, compVariant, compVersion string, parentCompID int, componentItems []map[string]interface{}) int {
	compVariant = cleanName(compVariant)
	compVersion = cleanName(compVersion)

	if compVariant == "" && compVersion != "" {
		compVariant = compVersion
		compVersion = ""
	}

	var compID int
	var endpoint string

	// Create base version
	if parentCompID < 0 {
		if isEmpty(compVariant) {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/?name=%s", url.QueryEscape(compName))
		} else {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/?name=%s", url.QueryEscape(compName+";"+compVariant))
		}
	} else {
		endpoint = fmt.Sprintf("/dmadminweb/API/new/compver/%d", parentCompID)
	}

	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1
	}

	if result, ok := data["result"].(map[string]interface{}); ok {
		if id, ok := result["id"].(float64); ok {
			compID = int(id)
		}
	}

	if parentCompID >= 0 {
		c.UpdateName(compName, compVariant, compVersion, compID)
	}

	c.NewComponentItem(compID, "file", componentItems)
	return compID
}

// NewComponentItem creates a new component item
func (c *Client) NewComponentItem(compID int, kind string, componentItems []map[string]interface{}) map[string]interface{} {
	var data map[string]interface{}
	var err error

	if strings.ToLower(kind) == "docker" || componentItems == nil {
		endpoint := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=inv&c=%d&xpos=100&ypos=100&kind=%s&removeall=Y",
			compID, kind)
		data, err = c.getJSON(endpoint)
	} else {
		ypos := 100
		parentItem := -1

		for i, item := range componentItems {
			tmpStr := ""
			ciName := ""

			for _, entry := range item {
				if entryMap, ok := entry.(map[string]interface{}); ok {
					if key, ok := entryMap["key"].(string); ok {
						if value, ok := entryMap["value"].(string); ok {
							if strings.ToLower(key) == "name" {
								ciName = value
							} else {
								tmpStr += "&" + url.QueryEscape(key) + "=" + url.QueryEscape(value)
							}
						}
					}
				}
			}

			if i == 0 {
				tmpStr += "&removeall=Y"
			}

			endpoint := fmt.Sprintf("/dmadminweb/API/new/compitem/%s?component=%d&xpos=100&ypos=%d&kind=%s%s",
				url.QueryEscape(ciName), compID, ypos, kind, tmpStr)

			data, err = c.getJSON(endpoint)
			if err == nil {
				if result, ok := data["result"].(map[string]interface{}); ok {
					if workID, ok := result["id"].(float64); ok {
						workIDInt := int(workID)
						if parentItem > 0 {
							linkEndpoint := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=iad&c=%d&fn=%d&tn=%d",
								compID, parentItem, workIDInt)
							c.getJSON(linkEndpoint)
						}
						parentItem = workIDInt
					}
				}
			}

			ypos += 100
		}
	}

	if err != nil {
		return map[string]interface{}{"error": err.Error()}
	}
	return data
}

// UpdateName updates the component name
func (c *Client) UpdateName(compName, compVariant, compVersion string, compID int) map[string]interface{} {
	compVariant = cleanName(compVariant)
	compVersion = cleanName(compVersion)

	if compVariant == "" && compVersion != "" {
		compVariant = compVersion
		compVersion = ""
	}

	if strings.Contains(compName, ".") {
		parts := strings.Split(compName, ".")
		if len(parts) > 0 {
			compName = parts[len(parts)-1]
		}
	}

	var newName string
	switch {
	case compVariant != "" && compVersion != "":
		newName = fmt.Sprintf("%s;%s;%s", compName, compVariant, compVersion)
	case compVariant != "":
		newName = fmt.Sprintf("%s;%s", compName, compVariant)
	default:
		newName = compName
	}

	endpoint := fmt.Sprintf("/dmadminweb/UpdateSummaryData?objtype=23&id=%d&change_1=%s",
		compID, url.QueryEscape(newName))

	data, err := c.getJSON(endpoint)
	if err != nil {
		return map[string]interface{}{"error": err.Error()}
	}
	return data
}

// UpdateComponentAttrs updates component attributes
func (c *Client) UpdateComponentAttrs(compName, compVariant, compVersion string, attrs map[string]string, crDataSource string, crList []string) (bool, interface{}, string) {
	compID, _ := c.GetComponent(compName, compVariant, compVersion, true, false)
	if compID < 0 {
		return false, "Component not found", ""
	}

	return c.UpdateCompIDAttrs(compID, attrs, crDataSource, crList)
}

// UpdateCompIDAttrs updates component attributes by ID
func (c *Client) UpdateCompIDAttrs(compID int, attrs map[string]string, crDataSource string, crList []string) (bool, interface{}, string) {
	endpoint := fmt.Sprintf("/dmadminweb/API/setvar/component/%d?delattrs=y", compID)
	fullURL := c.BaseURL + endpoint

	data, err := c.postJSON(endpoint, attrs)
	if err != nil {
		return false, fmt.Sprintf("Could not update attributes on '%d': %s", compID, err.Error()), fullURL
	}

	if errorMsg, ok := data["error"].(string); ok && errorMsg != "" {
		return false, fmt.Sprintf("Could not update attributes on '%d': %s", compID, errorMsg), fullURL
	}

	if isNotEmpty(crDataSource) {
		for _, bugID := range crList {
			crEndpoint := fmt.Sprintf("/dmadminweb/API2/assign/defect/%d?ds=%s&bugid=%s",
				compID, url.QueryEscape(crDataSource), bugID)
			c.getJSON(crEndpoint)
		}
	}

	return true, data, fullURL
}

// RunCmd executes a command and returns the output
func RunCmd(cmd string) string {
	if strings.Contains(cmd, "git") {
		if _, err := os.Stat(".git"); os.IsNotExist(err) {
			return ""
		}
	}

	out, err := exec.Command("sh", "-c", cmd).Output()
	if err != nil {
		return ""
	}

	return strings.TrimSpace(string(out))
}

// ClusterContainer represents a container from Kubernetes cluster
type ClusterContainer struct {
	CompID      int    `json:"compid"`
	CompName    string `json:"compname"`
	CompVariant string `json:"compvariant"`
	CompVersion string `json:"compversion"`
	FullMSName  string `json:"full_msname"`
	MSName      string `json:"msname"`
	Branch      string `json:"branch"`
	Repo        string `json:"repo"`
	Tag         string `json:"tag"`
	DeployTime  string `json:"deploy_time"`
}

// ImportCluster imports a Kubernetes cluster configuration
func (c *Client) ImportCluster(domain, appName, appVersion string, appAutoInc bool, deployEnv, crDataSource string, crList []string, clusterJSON, msName, msBranch string) {
	if appVersion == "" {
		appVersion = ""
	}

	if _, err := os.Stat(clusterJSON); os.IsNotExist(err) {
		return
	}

	file, err := os.Open(clusterJSON)
	if err != nil {
		return
	}
	defer file.Close()

	var values map[string]interface{}
	if err := json.NewDecoder(file).Decode(&values); err != nil {
		return
	}

	items, ok := values["items"].([]interface{})
	if !ok {
		return
	}

	masterContainers := make(map[string]ClusterContainer)
	var deployedMS ClusterContainer

	for _, item := range items {
		itemMap, ok := item.(map[string]interface{})
		if !ok {
			continue
		}

		metadata, ok := itemMap["metadata"].(map[string]interface{})
		if !ok {
			continue
		}

		deployTime, _ := metadata["creationTimestamp"].(string)
		labels, ok := metadata["labels"].(map[string]interface{})
		if !ok {
			continue
		}

		branch, _ := labels["git/branch"].(string)
		if branch == "" {
			branch = "main"
		}
		msVersion, _ := labels["app.kubernetes.io/version"].(string)

		spec, ok := itemMap["spec"].(map[string]interface{})
		if !ok {
			continue
		}

		template, ok := spec["template"].(map[string]interface{})
		if !ok {
			continue
		}

		templateSpec, ok := template["spec"].(map[string]interface{})
		if !ok {
			continue
		}

		containers, ok := templateSpec["containers"].([]interface{})
		if !ok {
			continue
		}

		for _, container := range containers {
			containerMap, ok := container.(map[string]interface{})
			if !ok {
				continue
			}

			fullMSName, _ := containerMap["name"].(string)
			image, _ := containerMap["image"].(string)

			imageParts := strings.Split(image, ":")
			if len(imageParts) != 2 {
				continue
			}

			repo := imageParts[0]
			tag := imageParts[1]
			repoParts := strings.Split(repo, "/")
			shortMSName := repoParts[len(repoParts)-1]

			compName := domain + "." + shortMSName
			compVariant := branch
			compVersion := tag

			containerInfo := ClusterContainer{
				CompID:      -1,
				CompName:    compName,
				CompVariant: compVariant,
				CompVersion: compVersion,
				FullMSName:  fullMSName,
				MSName:      shortMSName,
				Branch:      branch,
				Repo:        repo,
				Tag:         tag,
				DeployTime:  deployTime,
			}

			if fullMSName == msName {
				deployedMS = containerInfo
			}

			if branch == "master" || branch == "main" {
				if !strings.HasPrefix(msVersion, "1.") && msVersion != "1" {
					continue
				}

				if existing, exists := masterContainers[shortMSName]; !exists || existing.DeployTime <= deployTime {
					masterContainers[shortMSName] = containerInfo
				}
			}
		}
	}

	var compList []ClusterContainer
	if msBranch != "" {
		if deployedMS.MSName == "" {
			deployedMS = ClusterContainer{CompID: -1, MSName: "", Tag: "", Branch: ""}
		} else {
			compList = append(compList, deployedMS)
		}

		for _, container := range masterContainers {
			if deployedMS.MSName != container.MSName {
				compList = append(compList, container)
			} else if deployedMS.Branch == container.Branch && msBranch != "master" && msBranch != "main" {
				compList = append(compList, container)
			}
		}
	}

	var compIDList []map[string]interface{}
	for _, item := range compList {
		compID, _ := c.GetComponent(item.CompName, item.CompVariant, item.CompVersion, true, false)
		if compID == -1 {
			fmt.Printf("Adding missing component: %s;%s;%s\n", item.CompName, item.CompVariant, item.CompVersion)
			compID = c.NewDockerComponent(item.CompName, item.CompVariant, item.CompVersion, -1)
			if compID > 0 {
				attrs := map[string]string{
					"DockerTag":  item.Tag,
					"DockerRepo": item.Repo,
				}
				c.UpdateCompIDAttrs(compID, attrs, crDataSource, crList)
			}
		} else {
			fmt.Printf("%s;%s;%s\n", item.CompName, item.CompVariant, item.CompVersion)
		}

		compIDList = append(compIDList, map[string]interface{}{
			"compid": compID,
			"name":   fmt.Sprintf("%s;%s;%s", item.CompName, item.CompVariant, item.CompVersion),
		})
	}

	if len(compIDList) > 0 {
		app := appName
		if appVersion != "" && isNotEmpty(appVersion) {
			app = appName + ";" + appVersion
		}

		endpoint := fmt.Sprintf("/dmadminweb/API/application/?name=%s&latest=Y", url.QueryEscape(app))
		data, err := c.getJSON(endpoint)

		appID := -1
		if err == nil && data != nil {
			if success, _ := data["success"].(bool); success {
				if result, ok := data["result"].(map[string]interface{}); ok {
					if id, ok := result["id"].(float64); ok {
						appID = int(id)
					}
				}
			}
		}

		var existingIDs []int
		if appID > 0 {
			appEndpoint := fmt.Sprintf("/dmadminweb/API/application/%d", appID)
			appData, err := c.getJSON(appEndpoint)
			if err == nil && appData != nil {
				if result, ok := appData["result"].(map[string]interface{}); ok {
					if comps, ok := result["components"].([]interface{}); ok {
						for _, comp := range comps {
							if compMap, ok := comp.(map[string]interface{}); ok {
								if id, ok := compMap["id"].(float64); ok {
									existingIDs = append(existingIDs, int(id))
								}
							}
						}
					}
				}
			}
		}

		var newIDs []int
		for _, item := range compIDList {
			if compID, ok := item["compid"].(int); ok {
				newIDs = append(newIDs, compID)
			}
		}

		if areEqual(existingIDs, newIDs) {
			fmt.Printf("Application Version %s;%s already exists\n", appName, appVersion)
		} else {
			newAppID, _ := c.NewApplication(appName, appVersion, appAutoInc, nil, -1)
			if newAppID != -1 {
				appID = newAppID

				// Remove existing components
				for _, compID := range existingIDs {
					endpoint := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=acd&a=%d&c=%d", appID, compID)
					c.getJSON(endpoint)
				}

				// Add new components
				for _, item := range compIDList {
					if compID, ok := item["compid"].(int); ok {
						if name, ok := item["name"].(string); ok {
							fmt.Printf("Assigning Component Version %s to Application Version %s;%s\n",
								name, appName, appVersion)
							c.AddCompVerToAppVer(appID, compID)
						}
					}
				}
			}
		}

		// Create deployment record
		deployData := map[string]interface{}{
			"application": appID,
			"environment": deployEnv,
			"rc":          0,
		}

		c.LogDeployApplication(deployData)
	}
}

// areEqual compares two integer slices
func areEqual(arr1, arr2 []int) bool {
	if len(arr1) != len(arr2) {
		return false
	}

	sort.Ints(arr1)
	sort.Ints(arr2)

	for i := range arr1 {
		if arr1[i] != arr2[i] {
			return false
		}
	}

	return true
}

// NewApplication creates a new application version
func (c *Client) NewApplication(appName, appVersion string, appAutoInc bool, envs []string, compID int) (int, string) {
	appVersion = cleanName(appVersion)

	var parts []string
	if isEmpty(appVersion) && strings.Contains(appName, ";") {
		parts = strings.Split(appName, ";")
		if len(parts) > 1 {
			appVersion = parts[len(parts)-1]
			parts = parts[:len(parts)-1]
			appName = strings.Join(parts, ";")
		}
	}

	fullAppName := appName
	domain := ""

	if strings.Contains(appName, ".") {
		parts = strings.Split(appName, ".")
		if len(parts) > 0 {
			parts = parts[:len(parts)-1]
			domain = strings.Join(parts, ".")
			appName = strings.Split(fullAppName, ".")[len(strings.Split(fullAppName, "."))-1]
		}
	}

	// Get Base Version
	parentAppID, _, _ := c.GetApplication(fullAppName, "", true)

	// Create base version
	if parentAppID < 0 {
		var endpoint string
		if domain != "" {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/application/?name=%s&domain=%s",
				url.QueryEscape(appName), url.QueryEscape(domain))
		} else {
			endpoint = fmt.Sprintf("/dmadminweb/API/new/application/?name=%s", url.QueryEscape(appName))
		}

		data, err := c.getJSON(endpoint)
		if err == nil {
			if success, _ := data["success"].(bool); success {
				parentAppID, _, _ = c.GetApplication(appName, "", true)
			}
		}

		for _, env := range envs {
			assignEndpoint := fmt.Sprintf("/dmadminweb/API/assign/application/?name=%s&env=%s",
				url.QueryEscape(fullAppName), url.QueryEscape(env))
			c.getJSON(assignEndpoint)
		}
	}

	// Get latest version
	latestAppID, latestName, _ := c.GetApplication(fullAppName, "latest", false)

	if latestAppID == -1 {
		latestAppID = parentAppID
	}

	// Check if current version exists
	appID, _, _ := c.GetApplication(fullAppName, appVersion, true)

	// Handle auto-increment
	if appAutoInc && appID >= 0 {
		ver := appVersion
		for appID >= 0 {
			if strings.Contains(ver, "_") {
				schemaParts := strings.Split(ver, "_")
				if len(schemaParts) > 0 {
					if incNum, err := strconv.Atoi(schemaParts[len(schemaParts)-1]); err == nil {
						schemaParts[len(schemaParts)-1] = strconv.Itoa(incNum + 1)
						ver = strings.Join(schemaParts, "_")
					}
				}
			} else if num, err := strconv.Atoi(ver); err == nil {
				ver = strconv.Itoa(num + 1)
			} else {
				ver = "1"
			}
			appVersion = ver
			appID, _, _ = c.GetApplication(fullAppName, appVersion, true)
		}
	}

	// Check if component is already assigned
	if compID > 0 {
		isAssigned := c.IsCompAssigned2App(latestAppID, compID)
		if isAssigned {
			return latestAppID, latestName
		}
	}

	// Create new application version
	if appID < 0 {
		var endpoint string
		if domain != "" {
			endpoint = fmt.Sprintf("/dmadminweb/API/newappver/%d/?name=%s&domain=%s",
				latestAppID, url.QueryEscape(appName+";"+appVersion), url.QueryEscape(domain))
		} else {
			endpoint = fmt.Sprintf("/dmadminweb/API/newappver/%d/?name=%s",
				latestAppID, url.QueryEscape(appName+";"+appVersion))
		}

		data, err := c.getJSON(endpoint)
		if err != nil {
			return -1, err.Error()
		}

		if success, _ := data["success"].(bool); !success {
			if errorMsg, ok := data["error"].(string); ok {
				return -1, errorMsg
			}
		}

		if result, ok := data["result"].(map[string]interface{}); ok {
			if id, ok := result["id"].(float64); ok {
				appID = int(id)
			}
		}
	}

	return appID, fullAppName + ";" + appVersion
}

// IsCompAssigned2App checks if component is assigned to application
func (c *Client) IsCompAssigned2App(appID, compID int) bool {
	endpoint := fmt.Sprintf("/dmadminweb/API/compassigned2app/%d/%d", appID, compID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return false
	}

	result, _ := data["result"].(bool)
	return result
}

// MoveApplication moves an application from one domain using a task
func (c *Client) MoveApplication(appName, appVersion, fromDomain, task string) (int, string) {
	appID, _, _ := c.GetApplication(appName, appVersion, true)
	if appID == -1 {
		return -1, "Application not found"
	}

	// Get from domain ID
	fromID := ""
	domainEndpoint := fmt.Sprintf("/dmadminweb/API/domain/%s", url.QueryEscape(fromDomain))
	data, err := c.getJSON(domainEndpoint)
	if err == nil && data != nil {
		if result, ok := data["result"].(map[string]interface{}); ok {
			if id, ok := result["id"].(float64); ok {
				fromID = strconv.Itoa(int(id))
			}
		}
	}

	// Get tasks
	taskID := "0"
	taskEndpoint := fmt.Sprintf("/dmadminweb/GetTasks?domainid=%s", fromID)
	taskData, err := c.getJSON(taskEndpoint)
	if err == nil && taskData != nil {
		if tasks, ok := taskData["tasks"].([]interface{}); ok {
			for _, t := range tasks {
				if taskMap, ok := t.(map[string]interface{}); ok {
					if name, ok := taskMap["name"].(string); ok && name == task {
						if id, ok := taskMap["id"].(float64); ok {
							taskID = strconv.Itoa(int(id))
							break
						}
					}
				}
			}
		}
	}

	// Move application
	moveEndpoint := fmt.Sprintf("/dmadminweb/RunTask?f=run&tid=%s&notes=&id=%d&pid=%s",
		taskID, appID, fromID)
	moveData, err := c.getJSON(moveEndpoint)
	if err != nil {
		return -1, "Move Failed"
	}

	if success, _ := moveData["success"].(bool); success {
		return appID, "Move Successful"
	}

	if errorMsg, ok := moveData["error"].(string); ok {
		return -1, errorMsg
	}
	return -1, "Move Failed"
}

// ApproveApplication approves an application for deployment
func (c *Client) ApproveApplication(appName, appVersion string) (int, string) {
	appID, _, _ := c.GetApplication(appName, appVersion, true)
	if appID == -1 {
		return -1, "Application not found"
	}

	endpoint := fmt.Sprintf("/dmadminweb/API/approve/%d", appID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1, "Approval Failed"
	}

	if success, _ := data["success"].(bool); success {
		return appID, "Approval Successful"
	}

	if errorMsg, ok := data["error"].(string); ok {
		return -1, errorMsg
	}
	return -1, "Approval Failed"
}

// GetAttrs gets attributes for deployment based on app, component, environment, and server
func (c *Client) GetAttrs(app, comp, env, srv string) map[string]interface{} {
	envID := "-1"
	appID := "-1"
	compID := "-1"
	var servers []interface{}
	var envAttrs, srvAttrs, appAttrs, compAttrs []interface{}

	// Get environment data
	envEndpoint := fmt.Sprintf("/dmadminweb/API/environment/%s", url.QueryEscape(env))
	data, err := c.getJSON(envEndpoint)
	if err == nil && data != nil {
		if result, ok := data["result"].(map[string]interface{}); ok {
			if id, ok := result["id"].(float64); ok {
				envID = strconv.Itoa(int(id))
			}
			if srvs, ok := result["servers"].([]interface{}); ok {
				servers = srvs
			}
		}
	}

	// Get environment attributes
	envAttrEndpoint := fmt.Sprintf("/dmadminweb/API/getvar/environment/%s", envID)
	envAttrData, err := c.getJSON(envAttrEndpoint)
	if err == nil && envAttrData != nil {
		if attrs, ok := envAttrData["attributes"].([]interface{}); ok {
			envAttrs = attrs
		}
	}

	// Find server and get attributes
	for _, server := range servers {
		if srvMap, ok := server.(map[string]interface{}); ok {
			if name, ok := srvMap["name"].(string); ok && name == srv {
				if id, ok := srvMap["id"].(float64); ok {
					srvID := strconv.Itoa(int(id))
					srvAttrEndpoint := fmt.Sprintf("/dmadminweb/API/getvar/server/%s", srvID)
					srvAttrData, err := c.getJSON(srvAttrEndpoint)
					if err == nil && srvAttrData != nil {
						if attrs, ok := srvAttrData["attributes"].([]interface{}); ok {
							srvAttrs = attrs
						}
					}
					break
				}
			}
		}
	}

	// Get application data
	appEndpoint := fmt.Sprintf("/dmadminweb/API/application/?name=%s", url.QueryEscape(app))
	appData, err := c.getJSON(appEndpoint)
	if err == nil && appData != nil {
		if result, ok := appData["result"].(map[string]interface{}); ok {
			if name, ok := result["name"].(string); ok && name == app {
				if id, ok := result["id"].(float64); ok {
					appID = strconv.Itoa(int(id))
				}
			} else {
				if versions, ok := result["versions"].([]interface{}); ok {
					for _, ver := range versions {
						if verMap, ok := ver.(map[string]interface{}); ok {
							if name, ok := verMap["name"].(string); ok && name == app {
								if id, ok := verMap["id"].(float64); ok {
									appID = strconv.Itoa(int(id))
									break
								}
							}
						}
					}
				}
			}
		}
	}

	// Get application attributes
	appAttrEndpoint := fmt.Sprintf("/dmadminweb/API/getvar/application/%s", appID)
	appAttrData, err := c.getJSON(appAttrEndpoint)
	if err == nil && appAttrData != nil {
		if attrs, ok := appAttrData["attributes"].([]interface{}); ok {
			appAttrs = attrs
		}
	}

	// Get component data
	compEndpoint := fmt.Sprintf("/dmadminweb/API/component/%s", comp)
	compData, err := c.getJSON(compEndpoint)
	if err == nil && compData != nil {
		if result, ok := compData["result"].(map[string]interface{}); ok {
			if id, ok := result["id"].(float64); ok {
				compID = strconv.Itoa(int(id))
			}
		}
	}

	// Get component attributes
	compAttrEndpoint := fmt.Sprintf("/dmadminweb/API/getvar/component/%s", compID)
	compAttrData, err := c.getJSON(compAttrEndpoint)
	if err == nil && compAttrData != nil {
		if attrs, ok := compAttrData["attributes"].([]interface{}); ok {
			compAttrs = attrs
		}
	}

	// Merge all attributes
	result := make(map[string]interface{})

	for _, attrList := range [][]interface{}{envAttrs, srvAttrs, appAttrs, compAttrs} {
		for _, entry := range attrList {
			if entryMap, ok := entry.(map[string]interface{}); ok {
				for k, v := range entryMap {
					result[k] = v
				}
			}
		}
	}

	return result
}

// GetApplicationAttrs gets attributes for an application
func (c *Client) GetApplicationAttrs(appID int) map[string]interface{} {
	endpoint := fmt.Sprintf("/dmadminweb/API/getvar/application/%d", appID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return map[string]interface{}{}
	}

	if attributes, ok := data["attributes"].(map[string]interface{}); ok {
		return attributes
	}

	return map[string]interface{}{}
}

// FindDomain finds a domain by name
func (c *Client) FindDomain(findName string) map[string]interface{} {
	data, err := c.getJSON("/dmadminweb/GetAllDomains")
	if err != nil {
		return nil
	}

	if domains, ok := data["domains"].([]interface{}); ok {
		for _, dom := range domains {
			if domMap, ok := dom.(map[string]interface{}); ok {
				if name, ok := domMap["name"].(string); ok {
					parts := strings.Split(name, ".")
					if len(parts) > 0 {
						child := parts[len(parts)-1]
						if child == findName {
							return domMap
						}
						childLower := strings.ToLower(strings.ReplaceAll(child, " ", ""))
						if childLower == findName {
							domMap["name"] = "GLOBAL.Chasing Horses LLC." + name
							return domMap
						}
					}
				}
			}
		}
	}

	return nil
}

// GetComponentName gets the full component name by ID
func (c *Client) GetComponentName(compID int) string {
	endpoint := fmt.Sprintf("/dmadminweb/API/component/%d?idonly=Y", compID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return ""
	}

	if success, _ := data["success"].(bool); success {
		if result, ok := data["result"].(map[string]interface{}); ok {
			domain, _ := result["domain"].(string)
			name, _ := result["name"].(string)
			return domain + "." + name
		}
	}

	return ""
}

// GetComponentFromID gets component data by ID
func (c *Client) GetComponentFromID(compID int) map[string]interface{} {
	endpoint := fmt.Sprintf("/dmadminweb/API/component/%d", compID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return map[string]interface{}{}
	}
	return data
}

// GetPreviousCommit gets the git commit from the previous component version
func (c *Client) GetPreviousCommit(compName, compVariant string) string {
	parentCompID, _ := c.GetComponent(compName, compVariant, "", true, true)
	if parentCompID > 0 {
		data := c.GetComponentFromID(parentCompID)
		if result, ok := data["result"].(map[string]interface{}); ok {
			if gitCommit, ok := result["gitcommit"].(string); ok {
				return gitCommit
			}
		}
	}
	return ""
}

// GetApplicationName gets the full application name by ID
func (c *Client) GetApplicationName(appID int) string {
	endpoint := fmt.Sprintf("/dmadminweb/API/application/%d", appID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return ""
	}

	if success, _ := data["success"].(bool); success {
		if result, ok := data["result"].(map[string]interface{}); ok {
			domain, _ := result["domain"].(string)
			name, _ := result["name"].(string)
			return domain + "." + name
		}
	}

	return ""
}

// GetComponentFromTag gets component by Docker tag
func (c *Client) GetComponentFromTag(imageTag string) int {
	endpoint := fmt.Sprintf("/dmadminweb/API/comp4tag?image=%s", imageTag)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1
	}

	if id, ok := data["id"].(float64); ok {
		return int(id)
	}

	return -1
}

// AssignAppToEnv assigns an application to environments
func (c *Client) AssignAppToEnv(appName string, envs []string) {
	domain := ""
	if strings.Contains(appName, ".") {
		parts := strings.Split(appName, ".")
		if len(parts) > 0 {
			parts = parts[:len(parts)-1]
			domain = strings.Join(parts, ".")
			appName = strings.Split(appName, ".")[len(strings.Split(appName, "."))-1]
		}
	}

	for _, env := range envs {
		var endpoint string
		if domain != "" {
			endpoint = fmt.Sprintf("/dmadminweb/API/assign/application/?name=%s&env=%s&domain=%s",
				url.QueryEscape(appName), url.QueryEscape(env), url.QueryEscape(domain))
		} else {
			endpoint = fmt.Sprintf("/dmadminweb/API/assign/application/?name=%s&env=%s",
				url.QueryEscape(appName), url.QueryEscape(env))
		}
		c.getJSON(endpoint)
	}
}

// CloneRepo clones a repository and reads features.toml
func CloneRepo(project string) (map[string]interface{}, error) {
	fmt.Println("### Grabbing features.toml ###")

	tempDir := os.TempDir() + "/deployhub_clone_" + strconv.FormatInt(time.Now().Unix(), 10)
	err := os.MkdirAll(tempDir, 0755)
	if err != nil {
		return nil, err
	}

	oldDir, _ := os.Getwd()
	defer os.Chdir(oldDir)
	defer os.RemoveAll(tempDir)

	os.Chdir(tempDir)
	fmt.Println(tempDir)

	output := RunCmd("git clone -q git@github.com:" + project + ".git .")
	fmt.Println(output)

	featuresFile := "features.toml"
	if _, err := os.Stat(featuresFile); os.IsNotExist(err) {
		fmt.Println("features.toml not found")
		return nil, nil
	}

	var data map[string]interface{}
	if _, err := toml.DecodeFile(featuresFile, &data); err != nil {
		return nil, err
	}

	return data, nil
}

// RunCircleCIPipeline triggers a CircleCI pipeline
func RunCircleCIPipeline(pipeline string) []string {
	url := "https://circleci.com/api/v2/project/" + pipeline + "/pipeline"
	token := os.Getenv("CI_TOKEN")
	if token == "" {
		return []string{"Error: CI_TOKEN environment variable not set"}
	}

	cmd := fmt.Sprintf(`curl -X POST %s -H "Accept: application/json" -H "Circle-Token:%s" -q`, url, token)
	output := RunCmd(cmd)
	return strings.Split(output, "\n")
}

// GetScriptPath returns the directory of the current executable
func GetScriptPath() (string, error) {
	ex, err := os.Executable()
	if err != nil {
		return "", err
	}
	return filepath.Dir(ex), nil
}

// UpdateEnvIDAttrs updates environment attributes
func (c *Client) UpdateEnvIDAttrs(envID int, attrs map[string]interface{}) (bool, interface{}, string) {
	endpoint := fmt.Sprintf("/dmadminweb/API/setvar/environment/%d", envID)
	url := c.BaseURL + endpoint

	data, err := c.postJSON(endpoint, attrs)
	if err != nil {
		return false, fmt.Sprintf("Could not update attributes on '%d'", envID), url
	}

	if len(data) == 0 {
		return false, fmt.Sprintf("Could not update attributes on '%d'", envID), url
	}

	return true, data, url
}

// PostJSONWithHeader posts JSON with custom headers (for CircleCI integration)
func PostJSONWithHeader(url, token string) []string {
	fmt.Printf("URL: %s\n", url)

	cmd := fmt.Sprintf(`curl -X POST %s -H "Accept: application/json" -H "Circle-Token:%s" -q`, url, token)
	output := RunCmd(cmd)
	return strings.Split(output, "\n")
}

// Helper functions and types for better Go idiomatic usage

// DeploymentResult represents the result of a deployment operation
type DeploymentResult struct {
	ID      int    `json:"id"`
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// ApplicationInfo represents application information
type ApplicationInfo struct {
	ID      int    `json:"id"`
	Name    string `json:"name"`
	Latest  int    `json:"latest"`
	Success bool   `json:"success"`
}

// ComponentInfo represents component information
type ComponentInfo struct {
	ID      int    `json:"id"`
	Name    string `json:"name"`
	Success bool   `json:"success"`
}

// EnvironmentInfo represents environment information
type EnvironmentInfo struct {
	ID      int    `json:"id"`
	Name    string `json:"name"`
	Success bool   `json:"success"`
}

// DeploymentLog represents deployment log information
type DeploymentLog struct {
	Success bool   `json:"success"`
	Output  string `json:"output"`
}

// AddCompVerToAppVer adds component version to application version
func (c *Client) AddCompVerToAppVer(appID, compID int) {
	replaceCompID := -1
	baseCompID := c.GetBaseComponent(compID)
	lastCompID := 0
	xpos := 100
	ypos := 100

	endpoint := fmt.Sprintf("/dmadminweb/API/application/%d", appID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return
	}

	if success, _ := data["success"].(bool); success {
		if result, ok := data["result"].(map[string]interface{}); ok {
			if components, ok := result["components"].([]interface{}); ok {
				if lastComp, ok := result["lastcompver"].(float64); ok {
					lastCompID = int(lastComp)
				}

				for _, comp := range components {
					if compMap, ok := comp.(map[string]interface{}); ok {
						if id, ok := compMap["id"].(float64); ok {
							appBaseCompID := c.GetBaseComponent(int(id))
							if appBaseCompID == baseCompID {
								replaceCompID = int(id)
							}

							if int(id) == lastCompID {
								if x, ok := compMap["xpos"].(float64); ok {
									xpos = int(x)
								}
								if y, ok := compMap["ypos"].(float64); ok {
									ypos = int(y) + 100
								}
							}
						}
					}
				}
			}
		}
	}

	if replaceCompID >= 0 {
		replaceEndpoint := fmt.Sprintf("/dmadminweb/API/replace/%d/%d/%d", appID, replaceCompID, compID)
		c.getJSON(replaceEndpoint)
	} else {
		c.AssignCompToApp(appID, compID, lastCompID, xpos, ypos)
	}
}

// GetBaseComponent gets the base component ID
func (c *Client) GetBaseComponent(compID int) int {
	endpoint := fmt.Sprintf("/dmadminweb/API/basecomponent/%d", compID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return -1
	}

	if result, ok := data["result"].(map[string]interface{}); ok {
		if id, ok := result["id"].(float64); ok {
			return int(id)
		}
	}

	return -1
}

// AssignCompToApp assigns component to application
func (c *Client) AssignCompToApp(appID, compID, parentCompID, xpos, ypos int) {
	// Add component to application
	endpoint1 := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=acd&a=%d&c=%d", appID, compID)
	c.getJSON(endpoint1)

	// Position component
	endpoint2 := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=acvm&a=%d&c=%d&xpos=%d&ypos=%d",
		appID, compID, xpos, ypos)
	c.getJSON(endpoint2)

	// Link to parent
	endpoint3 := fmt.Sprintf("/dmadminweb/UpdateAttrs?f=cal&a=%d&fn=%d&tn=%d",
		appID, parentCompID, compID)
	c.getJSON(endpoint3)
}

// LogDeployApplication logs a deployment
func (c *Client) LogDeployApplication(deployData map[string]interface{}) map[string]interface{} {
	endpoint := "/dmadminweb/API/deploy"

	compVersion, _ := deployData["compversion"].([]string)
	environment, _ := deployData["environment"].(string)
	application, _ := deployData["application"].(string)

	if _, exists := deployData["skipdeploy"]; !exists {
		deployData["skipdeploy"] = "N"
	}

	if application != "" && environment != "" {
		result, err := c.postJSON(endpoint, deployData)
		if err == nil && result != nil {
			if deployID, ok := result["deployid"].(float64); ok {
				deployData["deployid"] = int(deployID)
			}
			if app, ok := result["application"].(string); ok {
				deployData["application"] = app
				application = app
			}
			if appID, ok := result["appid"].(float64); ok {
				deployData["appid"] = int(appID)
			}

			if errorMsg, ok := result["errormsg"].(string); ok && errorMsg != "" {
				fmt.Println(errorMsg)
			}
		}

		fmt.Printf("Recorded deployment of %v for %s\n", application, environment)

		if len(compVersion) > 0 {
			fmt.Printf("Assigned components to %v:\n", application)
			for _, comp := range compVersion {
				fmt.Printf("  %s\n", comp)
			}
		}
	}

	return deployData
}

// SetKVConfig updates component attributes from configuration files
func (c *Client) SetKVConfig(kvConfig, compName, compVariant, compVersion, crDataSource string, crList []string) {
	if isEmpty(compVariant) {
		compVariant = ""
	}

	if isEmpty(compVariant) && strings.Contains(compVersion, "-v") {
		parts := strings.Split(compVersion, "-v")
		compVariant = parts[0]
		compVersion = "v" + parts[1]
	}

	if isEmpty(compVariant) && strings.Contains(compVersion, "-V") {
		parts := strings.Split(compVersion, "-V")
		compVariant = parts[0]
		compVersion = "v" + parts[1]
	}

	var configPath string
	var tempDir string

	if strings.Contains(kvConfig, "git@") {
		fmt.Println("### Grabbing Config from Git ###")

		gitBranch := "master"
		if strings.Contains(kvConfig, "#") {
			parts := strings.Split(kvConfig, "#")
			kvConfig = parts[0]
			gitBranch = parts[1]
		}

		repoParts := strings.Split(kvConfig, "/")
		repo := strings.Join(repoParts[:2], "/")
		kvConfig = strings.Join(repoParts[1:], "/")
		gitDir := strings.Split(kvConfig, "/")[0]
		kvConfig = strings.Join(strings.Split(kvConfig, "/")[1:], "/")

		// Create temp directory and clone
		tempDir = os.TempDir() + "/deployhub_" + strconv.FormatInt(time.Now().Unix(), 10)
		os.MkdirAll(tempDir, 0755)

		oldDir, _ := os.Getwd()
		os.Chdir(tempDir)

		RunCmd("git clone -q " + repo)
		os.Chdir(gitDir)
		RunCmd("git checkout " + gitBranch)

		configPath = kvConfig
		defer func() {
			os.Chdir(oldDir)
			os.RemoveAll(tempDir)
		}()
	} else {
		configPath = kvConfig
	}

	normalDict := make(map[string]string)

	// Process .properties files
	err := filepath.Walk(configPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if strings.HasSuffix(info.Name(), ".properties") {
			fmt.Println(path)
			cfg, err := ini.Load(path)
			if err != nil {
				fmt.Printf("Error loading %s: %v\n", path, err)
				return nil
			}

			for _, section := range cfg.Sections() {
				for _, key := range section.Keys() {
					normalDict[key.Name()] = key.String()
				}
			}
		}

		if strings.HasSuffix(info.Name(), ".json") {
			fmt.Println(path)
			file, err := os.Open(path)
			if err != nil {
				return nil
			}
			defer file.Close()

			var data map[string]string
			json.NewDecoder(file).Decode(&data)

			for k, v := range data {
				normalDict[k] = v
			}
		}

		return nil
	})

	if err != nil {
		fmt.Printf("Error walking config path: %v\n", err)
		return
	}

	// Flatten nested dictionaries (simplified version)
	attrs := make(map[string]string)
	for key, value := range normalDict {
		attrs[key] = value
	}

	fmt.Println()

	// Get latest component
	fmt.Println("Getting Latest Component")
	latestCompID, _ := c.GetComponent(compName, compVariant, compVersion, false, true)

	if latestCompID < 0 {
		latestCompID, _ = c.GetComponent(compName, "", "", false, true)
	}

	if latestCompID > 0 {
		compAttrs := c.GetComponentAttrs(latestCompID)

		allAttrs := make(map[string]string)
		for k, v := range compAttrs {
			allAttrs[k] = v
		}

		for k, v := range attrs {
			allAttrs[k] = v
		}

		fmt.Println("Updating Component Attributes")
		c.UpdateCompIDAttrs(latestCompID, allAttrs, crDataSource, crList)
	}

	fmt.Println("Attribute Update Done")
}

// GetComponentAttrs gets component attributes
func (c *Client) GetComponentAttrs(compID int) map[string]string {
	endpoint := fmt.Sprintf("/dmadminweb/API/getvar/component/%d", compID)
	data, err := c.getJSON(endpoint)
	if err != nil {
		return make(map[string]string)
	}

	if attributes, ok := data["attributes"].([]map[string]string); ok {
		result := make(map[string]string) // Initialize the map
		for _, attr := range attributes {
			// Extract key-value pairs from each attribute map
			for key, value := range attr {
				result[key] = value
			}
		}
		return result
	}

	return make(map[string]string)
}

// PostTextFile uploads a text file to a component
func (c *Client) PostTextFile(compID int, filename, fileType string) map[string]interface{} {
	var fileData []byte
	var err error

	if _, statErr := os.Stat(filename); statErr == nil {
		fileData, err = os.ReadFile(filename)
	} else {
		// Try to fetch from URL
		resp, httpErr := http.Get(filename)
		if httpErr == nil && resp.StatusCode == http.StatusOK {
			defer resp.Body.Close()
			fileData, err = io.ReadAll(resp.Body)
		} else {
			fmt.Printf("WARNING: %s not found\n", filename)
			return map[string]interface{}{}
		}
	}

	if err != nil || len(fileData) == 0 {
		return map[string]interface{}{}
	}

	encodedData := base64.StdEncoding.EncodeToString(fileData)
	lines := strings.Split(encodedData, "\n")

	payload := map[string]interface{}{
		"compid":   compID,
		"filetype": fileType,
		"file":     lines,
	}

	result, err := c.postJSON("/msapi/textfile", payload)
	if err != nil {
		return map[string]interface{}{
			"message": fmt.Sprintf("Could not persist '%s' with compid: '%d'", filename, compID),
		}
	}

	return result
}

// UpdateDepPkgs updates dependency packages
func (c *Client) UpdateDepPkgs(compID int, filename string, glic map[string]interface{}) map[string]interface{} {
	// Get SBOM type
	sbomData, err := c.getJSON("/msapi/sbomtype")
	var sbomType string
	if err == nil && sbomData != nil {
		if st, ok := sbomData["SBOMType"].(string); ok {
			sbomType = st
		}
	}

	parts := strings.Split(filename, "@")
	if len(parts) != 2 {
		return map[string]interface{}{"error": "Invalid filename format"}
	}

	fileType := strings.ToLower(parts[0])
	actualFilename := parts[1]

	file, err := os.Open(actualFilename)
	if err != nil {
		return map[string]interface{}{
			"message": fmt.Sprintf("Could not open '%s' with compid: '%d'", actualFilename, compID),
		}
	}
	defer file.Close()

	var data map[string]interface{}
	if err := json.NewDecoder(file).Decode(&data); err != nil {
		return map[string]interface{}{
			"message": fmt.Sprintf("Could not parse JSON in '%s'", actualFilename),
		}
	}

	var result map[string]interface{}

	if sbomType == "fullfile" {
		postData := map[string]interface{}{
			"_key":    strconv.Itoa(compID),
			"content": data,
		}

		result, err = c.postJSON("/msapi/package", postData)
	} else {
		// Handle license mapping if glic is provided
		if glic != nil {
			glicHash := make(map[string]string)

			if dependencies, ok := glic["dependencies"].([]interface{}); ok {
				for _, dep := range dependencies {
					if depMap, ok := dep.(map[string]interface{}); ok {
						if moduleName, ok := depMap["moduleName"].(string); ok {
							if moduleVersion, ok := depMap["moduleVersion"].(string); ok {
								if moduleLicense, ok := depMap["moduleLicense"].(string); ok {
									purl := fmt.Sprintf("pkg:maven/%s@%s",
										strings.ReplaceAll(moduleName, ":", "/"), moduleVersion)
									glicHash[purl] = moduleLicense
								}
							}
						}
					}
				}
			}

			// Update components with license information
			if components, ok := data["components"].([]interface{}); ok {
				var newData []interface{}
				for _, comp := range components {
					if compMap, ok := comp.(map[string]interface{}); ok {
						if purl, ok := compMap["purl"].(string); ok {
							if license, exists := glicHash[purl]; exists {
								compMap["licenses"] = []map[string]interface{}{
									{"license": map[string]interface{}{"name": license}},
								}
							}
						}
						newData = append(newData, compMap)
					}
				}
				data["components"] = newData
			}
		}

		endpoint := fmt.Sprintf("/msapi/deppkg/%s?compid=%d", fileType, compID)
		result, err = c.postJSON(endpoint, data)
	}

	if err != nil {
		return map[string]interface{}{
			"message": fmt.Sprintf("Could not persist '%s' with compid: '%d'", actualFilename, compID),
		}
	}

	return result
}

// GetJSON provides public access to getJSON method
func (c *Client) GetJSON(endpoint string) (map[string]interface{}, error) {
	return c.getJSON(endpoint)
}

// PostJSON provides public access to postJSON method
func (c *Client) PostJSON(endpoint string, payload interface{}) (map[string]interface{}, error) {
	return c.postJSON(endpoint, payload)
}
