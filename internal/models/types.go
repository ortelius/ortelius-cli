// Package models provides common data structures used throughout the Ortelius CLI application.
package models

// ComponentConfig represents the component configuration structure
type ComponentConfig struct {
	Application        string            `mapstructure:"application"`
	ApplicationVersion string            `mapstructure:"application_version"`
	Name               string            `mapstructure:"name"`
	Variant            string            `mapstructure:"variant"`
	Version            string            `mapstructure:"version"`
	Kind               string            `mapstructure:"kind"`
	Export             map[string]string `mapstructure:"export"`
	Attributes         map[string]string `mapstructure:"attributes"`

	Extras map[string]any `mapstructure:",remain"` // capture extra fields from the map
}

// DeployData represents the deployment data structure
type DeployData struct {
	Application     string         `json:"application" mapstructure:"application"`
	AppVersion      string         `json:"appversion,omitempty" mapstructure:"appversion,omitempty"`
	CompVersion     []string       `json:"compversion" mapstructure:"compversion"`
	RC              int            `json:"rc" mapstructure:"rc"`
	Environment     string         `json:"environment,omitempty" mapstructure:"environment,omitempty"`
	KvConfig        string         `json:"kvconfig,omitempty" mapstructure:"kvconfig,omitempty"`
	CircleCIPipe    string         `json:"circleci_pipeline,omitempty" mapstructure:"circleci_pipeline,omitempty"`
	ConfigComponent string         `json:"config_component,omitempty" mapstructure:"config_component,omitempty"`
	ImageTags       []string       `json:"imagetags,omitempty" mapstructure:"imagetags,omitempty"`
	SkipDeploy      string         `json:"skipdeploy,omitempty" mapstructure:"skipdeploy,omitempty"`
	Extras          map[string]any `json:"-" mapstructure:",remain"`
}
