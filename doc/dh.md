<a name="dh"></a>
# The Ortelius Command Line Interface
The Ortelius Command Line Interface supports integration with DevOps tools and CI/CD pipelines.

The CLI Python script interacts with the Ortelius REST APIs to perform:

- Approve the _Application Version_
- Move the _Application Version- using the supplied task
- Create/replace the _Component Version_ for the _Application Version_
- Assign a _Component Version_ to an _Application version_
- Assign the key/values pairs to the _Component version_
- Create a bash file from the _Component_ .toml file
- Export a _Domain_ including all objects to stdout
- Imports the export file into the new _Domain_
- Deploy the _Application Version_
- Upload Swagger and SBOM files to _Component Version_


## CLI Prerequisites 

- The Ortelius CLI uses Python. Install Python 3.6 or higher.
  - [Python download.](https://www.python.org/downloads/)

- Install the Ortelius CLI where your CI/CD server is running. . The CLI module is available at https://pypi.org/project/ortelius-cli/. To install run:
  - `pip install ortelius-cli`

## Get Started with a POC
Refer to the [Ortelius sample POC](https://docs.ortelius.io/Ortelius-General-Poc.pdf) to get started. This POC provides you the steps to incorporate Ortelius into your Pipeline, with SBOM generation. 


## Ortelius' CLI using the dhapi module.

**Arguments**:

  
  ACTION - one of the following
  
- `deploy` - deploy the _Application_ to the _Environment_
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  --deployenv
  
- `approve` - approve the _Application Version_
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  
- `move` - move the _Application Version_ using the supplied task
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --appname
  --appversion (optional)
  --from_domain
  --task
  
- `updatecomp` - create/replace the _Component Version_ for the _Application Verion_ with SBOM (CycloneDX or SPDX formats).
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
  Chart = ""                                                  # Helm Chart for the Component
  ChartNamespace = ""                                         # Name space for the Component to be deployed to
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
  GitPreviousComponentCommit = "${GIT_PREVIOUS_COMPONENT_COMMIT}" # Commit of the previous Component (DERIVED IF NOT SPECIFIED)
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
  
- `assign` - assigns a _Component Version_ to an _Application Verion_
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --compname
  --compvariant (optional)
  --compversion (optional)
  --appname
  --appversion (optional)
  
- `kv` - assigns the key/values pairs to the _Component Verion_
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --compname
  --compvariant (optional)
  --compversion (optional)
  --kvconfig
  
- `envscript` - creates a bash file from the _Component_ toml file
  Usage:
  --envvars
  --envvars_sh
  
- `export` - exports a _Domain_ including all objects to stdout
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --from_dom
  
- `import` - imports the export file into the new _Domain_
  Usage:
  --dhurl
  --dhuser
  --dhpass
  --from_dom
  --to_dom
  
#### Parameter Usage
  
  | Parameter| Descriptions |
  | --- | --- | 
  | appautoinc | _Application_ Auto Increment Version |
  | appname | _Application_ Name |
  | appversion | _Application Version_ |
  | cert | Customer SSL Certificate File |
  | changerequest | Change Request for _Component_, use multiple time for each Change Request Id |
  | cluster_json | json from kubectl get deploy -n default -o json |
  | compattr | _Component_ attributes, use multiple time for each attr |
  | compautoinc | _Component_ auto increment version |
  | compname | _Component_ Name |
  | compvariant | _Component_ Variant |
  | compversion | _Component Version_ |
  | consumes | json file that lists the endpoints the _Component_ consumes.  [ {"verb", "get", "path": "/weather"}] |
  | crdatasource | Change Request Data Source for the _Component_ |
  | deploydata | The json file that contains the _Application_, _Environment_ and log details |
  | deploydatasave | Name of the json file to save the new _Component_ and _Application Versions_ names to |
  | deployenv | Deployment _Environment_ |
  | deppkg | File name for the Safety, CycloneDx, SPDX json scan data, use multiple time for each file.  Parameter format is: <type>@<filename> where type=safety, cyclonedx, spdx
  | dhpass | Ortelius Password |
  | dhurl | Ortelius Url |
  | dhuser | Ortleius User |
  | docker | docker Kind of the _Component_ item |
  | envs | _Environments_ to Associate _Application Version_ to, use multiple time for each env |
  | envvars_sh | Environment Variables Output shell file |
  | envvars | _Component_ TOML file |
  | file | file Kind of the _Component_ item |
  | from_domain | Move from _Domain_ |
  | fromdom | From _Domain_ |
  | importfile | File to Import |
  | kvconfig | Directory containing the json and properties file |
  | logdeployment | Records a deployment by a external program |
  | msbranch | New microservice branch being added to the cluster |
  | msname | New microservice being added to the cluster |
  | provides | json file that lists the _Endpoints_ the _Component_ provides.  [ {"verb", "get", "path": "/checkout"}] |
  | rsp | Response File for Parameters, ie component.toml |
  | task | Task to use for move |
  | todom | To _Domain_ |

