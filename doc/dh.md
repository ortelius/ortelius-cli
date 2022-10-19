<a name="dh"></a>
# dh

DeployHub's CLI using the dhapi module.

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
  --compname
  --compvariant (optional)
  --compversion (optional)
  --autocompinc (optional)
  --appname (optional)
  --appversion (optional)
  --autoappinc (optional)
  --compattr
  --consumes (optional)
  --provides (optional)
  
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
- `--consumes` - json file that lists the endpoints the component consumes.  [ {"verb", "get", "path": "/weather"}]
- `--provides` - json file that lists the endpoints the component provides.  [ {"verb", "get", "path": "/checkout"}]
  
  Example Jenkinsfile Snippet:
  https://github.com/ortelius/compupdate/blob/main/Jenkinsfile

<a name="dh.main"></a>
#### main

```python
@click.command()
@click.argument('action', required=True)
@click.option('--dhurl', help='DeployHub Url', envvar='DHURL', required=True)
@click.option('--dhuser', help='DeployHub User', envvar='DHUSER', required=True)
@click.option('--dhpass', help='DeployHub Password', envvar='DHPASS', required=True)
@click.option('--appname', help='Application Name', envvar='COMPONENT_APPLICATION')
@click.option('--appversion', help='Application Version', envvar='COMPONENT_APPLICATION_VERSION')
@click.option('--appautoinc', help='Application Auto Increment Version', envvar='COMPONENT_APPLICATION_AUTOINC')
@click.option('--deployenv', help='Deployment Environment')
@click.option('--compname', help='Component Name', envvar='COMPONENT_NAME')
@click.option('--compvariant', help='Component Variant', envvar='COMPONENT_VARIANT')
@click.option('--compversion', help='Component Version', envvar='COMPONENT_VERSION')
@click.option('--compautoinc', help='Component Auto Increment Version', envvar='COMPONENT_AUTOINC')
@click.option('--deploydatasave', help='Name of the json file to save the new component and application versions names to')
@click.option('--kvconfig', help='Directory containing the json and properties file', envvar='KVCONFIG')
@click.option('--crdatasource', help='Change Request Data Source for the Component', envvar='CR_DATASOURCE')
@click.option('--changerequest', help='Change Request for Component, use multiple time for each Change Request Id', multiple=True)
@click.option('--deploydata', help='The json file that contains the application, environment and log details', envvar='DEPLOY_DATA')
@click.option('--from_domain', help='Move from domain')
@click.option('--task', help='Task to use for move')
@click.option('--envvars', help='Env Variables TOML file')
@click.option('--envvars_sh', help='Env Variables Output sh file')
@click.option('--docker', 'kind', flag_value='docker', default=True, help='Component Item Type')
@click.option('--file', 'kind', flag_value='file')
@click.option('--compattr', help='Component Attributes, use multiple time for each attr', multiple=True)
@click.option('--envs', help='Environments to Associate App to, use multiple time for each env', multiple=True)
@click.option('--importfile', help='File to Import')
@click.option('--fromdom', help='From Domain')
@click.option('--todom', help='To Domain')
@click.option('--cluster_json', help='json from kubectl get deploy -n default -o json')
@click.option('--msname', help='New microservice being added to the cluster')
@click.option('--msbranch', help='New microservice branch being added to the cluster')
@click.option('--deppkg', help='File name for the Safety, CycloneDx json scan data, use multiple time for each file.  Parameter format is: <type>@<filename> where type=safety, cyclonedx', multiple=True)
@click.option('--logdeployment', is_flag=True, help='Records a deployment by a external program')
@click.option('--consumes', help='json file listing end points being consumed')
@click.option('--provides', help='json file listing end points being provided')
@click.option('--rsp', help='Response File for Parameters')
@click.option('--cert', help='Customer SSL Certificate File')
main(dhurl, dhuser, dhpass, action, appname, appversion, appautoinc, compname, compvariant, compversion, compautoinc, kind, deployenv, envs, compattr, kvconfig, deploydata, deploydatasave, from_domain, task, envvars, envvars_sh, importfile, fromdom, todom, crdatasource, changerequest, cluster_json, msname, msbranch, deppkg, logdeployment, consumes, provides, rsp, cert)
```

ACTION: deploy, updatecomp, approve, move, envscript, kv, cluster, export or import for the type of action to perform.

    deploy: deploy the application to the evironment\n
    approve: approve the application version\n
    move: move the application version using the supplied task\n
    updatecomp: create/replace the component version for the application verion\n
        Predefined Key/Values:\n
            BuildId - Identifier for the CI job\n
            BuildNumber - Build number for the CI job\n
            BuildUrl - url for the CI job\n
            Chart - Helm Chart for the component\n
            ChartNamespace - Name space for the component to be deployed to\n
            ChartRepo - Helm Chart Repo Name\n
            ChartRepoUrl - Helm Chart Repo Url\n
            ChartVersion - Helm Chart version\n
            CustomAction - Custom Action to assign to the Component\n
            DockerBuildDate - Timestamp when the image was created\n
            DockerRepo - Registry which the image was pushed to\n
            DockerSha - Digest for the image\n
            DockerTag - Tag for the image\n
            GitBranch - Git branch in the git repo\n
            GitCommit - Git commit that triggered the CI job\n
            GitRepo - Git repo that triggered the CI job\n
            GitTag - Git tag in the git repo\n
            GitUrl - Full url to the git repo\n
            operator - Operator name\n
            Readme - Readme location in the Git Repo\n
            ServiceOwner - Owner of the Service\n
            ServiceOwnerEmail - Email for the Owner of the Service\n
            ServiceOwnerPhone - Phone number for the Owner of the Service\n

    assign: assigns a component version to an application verion\n
    kv: assigns the key/values pairs to the component verion\n
    envscript: creates a bash file from the component toml file\n
    export: exports a domain including all objects to stdout\n
    import: imports the export file into the new domain\n

<a name="dh.envscript"></a>
#### envscript

```python
envscript(dhurl, cookies, envvars, envvars_sh)
```

Add the variabes from the envvars toml file to the shell script.

**Arguments**:

- `dhurl` _string_ - url for the server
- `cookies` _string_ - cookies from the login
- `envvars` _string_ - file name for the environment toml file
- `envvars_sh` _string_ - the shell script to update with var from toml file
  

**Returns**:

  no data returned.  Output is in the shell script file.

<a name="dh.filterdict"></a>
#### filterdict

```python
filterdict(dhurl, cookies, objtype, fromdom, allobjs)
```

Export all the objects from the server for the from domain and filter the dictionary for the object name.

**Arguments**:

- `dhurl` _string_ - url for the server
- `cookies` _string_ - cookies from the login
- `objtype` _sting_ - object type to look for in the dictionary
- `fromdom` _string_ - name of the domain in the dictionary
- `allobjs` _dict_ - return of the objects found
  

**Returns**:

  data returned in allobjs

<a name="dh.importdict"></a>
#### importdict

```python
importdict(dhurl, cookies, objtype, allobjs)
```

Import the objects based on objtype and add them to the server.

**Arguments**:

- `dhurl` _string_ - url for the server
- `cookies` _string_ - cookies from the login
- `objtype` _sting_ - object type to look for in the dictionary
- `allobjs` _dict_ - return of the objects found
  

**Returns**:

  no data returned

