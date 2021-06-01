<a name="dh"></a>
# dh

DeployHub's CLI using the dhapi module.

**Arguments**:

  
  ACTION - one of the following
  
- `deploy` - deploy the application to the evironment
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --appname
    > --appversion (optional)
    > --deployenv
  
- `approve` - approve the application version
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --appname
    > --appversion (optional)
  
- `move` - move the application version using the supplied task
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --appname
    > --appversion (optional)
    > --from_domain
    > --task
  
- `updatecomp` - create/replace the component version for the application verion
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --compname
    > --compvariant (optional)
    > --compversion (optional)
    > --autocompinc (optional)
    > --appname (optional)
    > --appversion (optional)
    > --autoappinc (optional)
    > --compattr
  
  - Predefined Key/Values:
    * BuildId - Identifier for the CI job
    * BuildNumber - Build number for the CI job
    * BuildUrl - url for the CI job
    * Chart - Helm Chart for the component
    * ChartNamespace - Name space for the component to be deployed to
    * ChartRepo - Helm Chart Repo Name
    * ChartRepoUrl - Helm Chart Repo Url
    * ChartVersion - Helm Chart version
    * CustomAction - Custom Action to assign to the Component
    * DockerBuildDate - Timestamp when the image was created
    * DockerRepo - Registry which the image was pushed to
    * DockerSha - Digest for the image
    * DockerTag - Tag for the image
    * GitBranch - Git branch in the git repo
    * GitCommit - Git commit that triggered the CI job
    * GitRepo - Git repo that triggered the CI job
    * GitTag - Git tag in the git repo
    * GitUrl - Full url to the git repo
    * operator - Operator name
    * Readme - Readme location in the Git Repo
    * ServiceOwner - Owner of the Service
    * ServiceOwnerEmail - Email for the Owner of the Service
    * ServiceOwnerPhone - Phone number for the Owner of the Service
  
- `assign` - assigns a component version to an application verion
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --compname
    > --compvariant (optional)
    > --compversion (optional)
    > --appname
    > --appversion (optional)
  
- `kv` - assigns the key/values pairs to the component verion
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --compname
    > --compvariant (optional)
    > --compversion (optional)
    > --kvconfig
  
- `envscript` - creates a bash file from the component toml file
  - Usage:
    > --envvars
    > --envvars_sh
  
- `export` - exports a domain including all objects to stdout
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --from_dom
  
- `import` - imports the export file into the new domain
  - Usage:
    > --dhurl
    > --dhuser
    > --dhpass
    > --from_dom
    > --to_dom
  
  Parameter Descriptions:
  - `--dhurl` - DeployHub Url
  - `--dhuser` - DeployHub User
  - `--dhpass` - DeployHub Password
  - `--appname` - Application Name
  - `--appversion` - Application Version
  - `--appautoinc` - Application Auto Increment Version
  - `--deployenv` - Deployment Environment
  - `--compname` - Component Name
  - `--compvariant` - Component Variant
  - `--compversion` - Component Version
  - `--compautoinc` - Component Auto Increment Version
  - `--kvconfig` - Directory containing the json and properties file
  - `--crdatasource` - Change Request Data Source for the Component
  - `--changerequest` - Change Request for Component, use multiple time for each Change Request Id
  - `--deploydata` - The json file that contains the application, environment and log details
  - `--from_domain` - Move from domain
  - `--task` - Task to use for move
  - `--envvars` - Env Variables TOML file
  - `--envvars_sh` - Env Variables Output sh file
  - `--docker` - docker Kind of the component item
  - `--file` - file Kind of the component item
  - `--compattr` - Component Attributes, use multiple time for each attr
  - `--envs` - Environments to Associate App to, use multiple time for each env
  - `--importfile` - File to Import
  - `--fromdom` - From Domain
  - `--todom` - To Domain
  - `--msname` - New microservice being added to the cluster
  - `--msbranch` - New microservice branch being added to the cluster
  
  
  Example Jenkinsfile Snippet:
  https://github.com/ortelius/compupdate/blob/main/Jenkinsfile

