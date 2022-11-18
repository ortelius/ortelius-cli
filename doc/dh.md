<a name="dh"></a>
# dh

Ortelius' CLI using the dhapi module.

**Arguments**:

  
  ACTION - one of the following
  
- `deploy` - deploy the application to the environment
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  --deployenv
  
- `approve` - approve the application version
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  
- `move` - move the application version using the supplied task
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  --from_domain
  --task
  
- `updatecomp` - create/replace the component version for the application verion
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --rsp <name of the component toml file>
  --autoappinc (optional)
  --compautoinc (optional)
  --consumes (optional)
  --provides (optional)
  --deppkg cyclonedx@<cyclonedx json sbom file> (optional)
  --deppkg spdx@<spdx json sbom file> (optional)
  
  ##### Component TOML Definition for --rsp parameter
  
  ```toml
  # Application Name and Version to create an associate the Component Version to
  # NOTE: Only needed if you need to assoicate the Component Version to the Application Verion
  
  Application = ""          # Name of the Applcation including the full Domain Name
  Application_Version = ""  # The semantic version for the Application Version
  
  # Component Name, Variant and Version
  Name = ""
  Variant = "${GIT_BRANCH}"
  Version = "v1.0.0.${BUILD_NUM}-g${GIT_COMMIT}"                  # 1.0.0 should be replace with your starting version string
  
  # Export the derived IMAGE_TAG, DOCKERREPO values to the CI/CD Tool via a shell script when using the `envscript` command line action
  [Export]
  IMAGE_TAG = "${Variant}-${Version}"
  DOCKERREPO = "${DockerRepo}"
  
  # Key/Values to associate to the Component Version.  Custom key/values can be added under this section.
  [Attributes]
  BuildId = "${BUILDID}"                                      # Identifier for the CI job (DERIVED IF NOT SPECIFIED)
  BuildNumber = "${BUILD_NUM}"                                # Build number for the CI job (DERIVED IF NOT SPECIFIED)
  BuildUrl = "${BUILD_URL}"                                   # Build url for the CI job (DERIVED IF NOT SPECIFIED)
  Chart = ""                                                  # Helm Chart for the component
  ChartNamespace = ""                                         # Name space for the component to be deployed to
  ChartRepo = ""                                              # Helm Chart Repo Name
  ChartRepoUrl = ""                                           # Helm Chart Repo Url
  ChartVersion = ""                                           # Helm Chart version
  CustomAction = ""                                           # Custom Action to assign to the Component
  DeployAlways = ""                                           # Set the Always Deploy option Y/N, default is N
  DockerBuildDate = ""                                        # Timestamp when the image was created (DERIVED IF NOT SPECIFIED)
  DockerRepo = "${DOCKERREPO}"                                # Registry which the image was pushed to
  DockerSha = "${DIGEST}"                                     # Digest for the image (DERIVED IF NOT SPECIFIED)
  DockerTag = "${DOCKERTAG}"                                  # Tag for the image
  GitBranch = "${GIT_BRANCH}"                                 # Git branch in the git repo (DERIVED IF NOT SPECIFIED)
  GitBranchCreateCommit = "${GIT_BRANCH_CREATE_COMMIT}"       # Git commit that the branch was created from (DERIVED IF NOT SPECIFIED)
  GitBranchCreateTimestamp = "${GIT_BRANCH_CREATE_TIMESTAMP}" # Timestamp of when the branch was created (DERIVED IF NOT SPECIFIED)
  GitBranchParent = "${GIT_BRANCH_PARENT}"                    # The parent branch for the current branch (DERIVED IF NOT SPECIFIED)
  GitCommit = "${GIT_COMMIT}"                                 # Git commit that triggered the CI job (DERIVED IF NOT SPECIFIED)
  GitCommitAuthors = "${GIT_COMMIT_AUTHORS}"                  # List of committers for the repo (DERIVED IF NOT SPECIFIED)
  GitCommittersCnt = "${GIT_COMMITTERS_CNT}"                  # Count of GitCommitAuthors (DERIVED IF NOT SPECIFIED)
  GitCommitTimestamp = "${GIT_COMMIT_TIMESTAMP}"              # Timestamp of the current commit (DERIVED IF NOT SPECIFIED)
  GitContribPercentage = "${GIT_CONTRIB_PERCENTAGE}"          # GitCommittersCnt / GitTotalCommittersCnt * 100 (DERIVED IF NOT SPECIFIED)
  GitLinesAdded = "${GIT_LINES_ADDED}"                        # Lines added since the previous commit (DERIVED IF NOT SPECIFIED)
  GitLinesDeleted = "${GIT_LINES_DELETED}"                    # Lines deleted since the previous commit (DERIVED IF NOT SPECIFIED)
  GitLinesTotal = "${GIT_LINES_TOTAL}"                        # Total line count for the branch (DERIVED IF NOT SPECIFIED)
  GitOrg = "${GIT_ORG}"                                       # Orgranization for the repo (DERIVED IF NOT SPECIFIED)
  GitPreviousComponentCommit = "${GIT_PREVIOUS_COMPONENT_COMMIT}" # Commit of the previous component (DERIVED IF NOT SPECIFIED)
  GitRepo = "${GIT_REPO}"                                     # Git repo that triggered the CI job (DERIVED IF NOT SPECIFIED)
  GitRepoProject = "${GIT_REPO_PROJECT}"                      # Project name part of the repository url (DERIVED IF NOT SPECIFIED)
  GitTag = "${GIT_TAG)"                                       # Git tag in the git repo (DERIVED IF NOT SPECIFIED)
  GitTotalCommittersCnt = "${GIT_TOTAL_COMMITTERS_CNT}"       # Total committers working on this repo
  GitUrl = "${GIT_URL}"                                       # Full url to the git repo (DERIVED IF NOT SPECIFIED)
  License = ""                                                # License file location in the Git Repo (DERIVED IF NOT SPECIFIED)
  operator = ""                                               # Operator name
  Readme = ""                                                 # Readme file location in the Git Repo (DERIVED IF NOT SPECIFIED)
  ServiceOwner = ""                                           # Owner of the Service
  ServiceOwnerEmail = ""                                      # Email for the Owner of the Service
  ServiceOwnerPhone = ""                                      # Phone number for the Owner of the Service
  Swagger = ""                                                # Swagger/OpenApi file location in the Git Repo (DERIVED IF NOT SPECIFIED)
  ```
  
- `assign` - assigns a component version to an application verion
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --compname
  --compvariant (optional)
  --compversion (optional)
  --appname
  --appversion (optional)
  
- `kv` - assigns the key/values pairs to the component verion
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --compname
  --compvariant (optional)
  --compversion (optional)
  --kvconfig
  
- `envscript` - creates a bash file from the component toml file
  Usage:
  --envvars
  --envvars_sh
  
- `export` - exports a domain including all objects to stdout
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --from_dom
  
- `import` - imports the export file into the new domain
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --from_dom
  --to_dom
  
  #### Parameter Descriptions
  
  | Parameter| Descriptions |
  | appautoinc | Application Auto Increment Version |
  | appname | Application Name |
  `--appversion` Application Version
  `--cert` Customer SSL Certificate File
  `--changerequest` Change Request for Component, use multiple time for each Change Request Id
  `--cluster_json` json from kubectl get deploy -n default -o json
  `--compattr` Component Attributes, use multiple time for each attr
  `--compautoinc` Component Auto Increment Version
  `--compname` Component Name
  `--compvariant` Component Variant
  `--compversion` Component Version
  `--consumes`  json file that lists the endpoints the component consumes.  [ {"verb", "get", "path": "/weather"}]
  `--crdatasource` Change Request Data Source for the Component
  `--deploydata` The json file that contains the application, environment and log details
  `--deploydatasave` Name of the json file to save the new component and application versions names to
  `--deployenv` Deployment Environment
  `--deppkg` File name for the Safety, CycloneDx, SPDX json scan data, use multiple time for each file.  Parameter format is: <type>@<filename> where type=safety, cyclonedx, spdx
  `--dhpass` Ortelius Password
  `--dhurl` Ortelius Url
  `--dhuser` Ortleius User
  `--docker` docker Kind of the component item
  `--envs` Environments to Associate App to, use multiple time for each env
  `--envvars_sh` Environment Variables Output shell file
  `--envvars` Component TOML file
  `--file` file Kind of the component item
  `--from_domain` Move from domain
  `--fromdom` From Domain
  `--importfile` File to Import
  `--kvconfig` Directory containing the json and properties file
  `--logdeployment` Records a deployment by a external program
  `--msbranch` New microservice branch being added to the cluster
  `--msname` New microservice being added to the cluster
  `--provides`  json file that lists the endpoints the component provides.  [ {"verb", "get", "path": "/checkout"}]
  `--rsp` Response File for Parameters, ie component.toml
  `--task` Task to use for move
  `--todom` To Domain

