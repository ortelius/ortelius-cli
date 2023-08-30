<a name="__init__"></a>
# \_\_init\_\_

DeployHub REST API Client module.

<a name="dhapi"></a>
# dhapi

DeployHub RESTapi interface for Python.

<a name="dhapi.fspath"></a>
#### fspath

```python
fspath(path)
```

See <https://www.python.org/dev/peps/pep-0519/>`os` for details.

<a name="dhapi.get_json"></a>
#### get\_json

```python
get_json(url, cookies)
```

Get URL as json string.

**Arguments**:

- `url` _string_ - url to server
  cookies (string) - login cookies


**Returns**:

- `string` - The json string.

<a name="dhapi.post_json"></a>
#### post\_json

```python
post_json(url, payload, cookies)
```

Post URL as json string.

**Arguments**:

- `url` _string_ - url to server
- `payload` _string_ - json payload to post
- `cookies` _string_ - login cookies


**Returns**:

- `string` - The json string.

<a name="dhapi.post_json_with_header"></a>
#### post\_json\_with\_header

```python
post_json_with_header(url, token)
```

Post URL as json string.

**Arguments**:

- `url` _string_ - url to server
- `token` _string_ - CircleCI token for header


**Returns**:

- `string` - The json string

<a name="dhapi.is_empty"></a>
#### is\_empty

```python
is_empty(my_string)
```

Is the string empty.

**Arguments**:

- `my_string` _string_ - string to check emptyness on


**Returns**:

- `boolean` - True if the string is None or blank, otherwise False.

<a name="dhapi.is_not_empty"></a>
#### is\_not\_empty

```python
is_not_empty(my_string)
```

Is the string NOT empty.

**Arguments**:

- `my_string` _string_ - string to check emptyness on


**Returns**:

- `boolean` - False if the string is None or blank, otherwise True.

<a name="dhapi.login"></a>
#### login

```python
login(dhurl, user, password, errors)
```

Login to DeployHub using the DH Url, userid and password.

**Arguments**:

- `dhurl` _string_ - url to server
- `user` _string_ - username to login with
- `password` _string_ - password for login
- `errors` _list_ - list to return any errors back to the caller


**Returns**:

- `string` - the cookies to be used in subsequent API calls.

<a name="dhapi.deploy_application_by_appid"></a>
#### deploy\_application\_by\_appid

```python
deploy_application_by_appid(dhurl, cookies, appid, env)
```

Deploy the application to the environment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id to the application
- `env` _string_ - full name of the environemt


**Returns**:

- `list` - [deployment_id (int) -1 for error, message (string)].

<a name="dhapi.deploy_application"></a>
#### deploy\_application

```python
deploy_application(dhurl, cookies, appname, appversion, env)
```

Deploy the application to the environment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of the application including domain name
- `appversion` _string_ - version of application. Should include vairiant if used.
- `env` _string_ - full name of the environment


**Returns**:

- `list` - [deployment_id (int) -1 for error, message (string)].

<a name="dhapi.move_application"></a>
#### move\_application

```python
move_application(dhurl, cookies, appname, appversion, from_domain, task)
```

Move an application from the from_domain using the task.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of the application including domain name
- `appversion` _string_ - version of application. Should include vairiant if used.
- `from_domain` _string_ - full name of the domain to move from
- `task` _string_ - task to use to do the move


**Returns**:

- `list` - [appid (int) -1 for error, message (string)].

<a name="dhapi.approve_application"></a>
#### approve\_application

```python
approve_application(dhurl, cookies, appname, appversion)
```

Approve the application for the current domain that it is in.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of the application including domain name
- `appversion` _string_ - version of application. Should include vairiant if used.


**Returns**:

- `list` - [appid (int) -1 for error, message (string)].

<a name="dhapi.is_deployment_done"></a>
#### is\_deployment\_done

```python
is_deployment_done(dhurl, cookies, deployment_id)
```

Check to see if the deployment has completed.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `deployment_id` _int_ - id of the deployment to check


**Returns**:

- `list` - [True if done, otherwise False (boolean), message (string)].

<a name="dhapi.get_logs"></a>
#### get\_logs

```python
get_logs(dhurl, cookies, deployid)
```

Get the logs for the deployment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `deployment_id` _int_ - id of the deployment to check


**Returns**:

- `list` - [True if successful fetch, otherwise False (boolean), output lines (string)].

<a name="dhapi.get_attrs"></a>
#### get\_attrs

```python
get_attrs(dhurl, cookies, app, comp, env, srv)
```

Get the attributes for this deployment base on app version and env.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of the application including domain name.
- `compname` _string_ - name of the component including domain name
- `env` _string_ - name of the environment including domain name
- `srv` _string_ - name of the end-point including domain name


**Returns**:

- `dict` - key/value pair of attributes.

<a name="dhapi.get_application_attrs"></a>
#### get\_application\_attrs

```python
get_application_attrs(dhurl, cookies, appid)
```

Get the attributes for an application.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _id_ - id of the application


**Returns**:

- `string` - json string of the key/value attributes.

<a name="dhapi.find_domain"></a>
#### find\_domain

```python
find_domain(dhurl, cookies, findname)
```

Get the domain name and id that matches best with the passed in name.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `findname` _string_ - domain name to match


**Returns**:

  string or None if not found: the full domain name

<a name="dhapi.clean_name"></a>
#### clean\_name

```python
clean_name(name)
```

Remove periods and dashes from the name.

**Arguments**:

- `name` _string_ - string to clean


**Returns**:

- `string` - the name with periods and dashes changed to userscores.

<a name="dhapi.get_component"></a>
#### get\_component

```python
get_component(dhurl, cookies, compname, compvariant, compversion, id_only, latest)
```

Get the component json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain name
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `id_only` _boolean_ - return just the id and not the whole json string
- `latest` _boolean_ - return the latest version


**Returns**:

- `int` - if id_only = True
- `string` - if id_only = False. If latest = True then latest version json is returned otherwise current version json string is returned.

<a name="dhapi.get_environment"></a>
#### get\_environment

```python
get_environment(dhurl, cookies, env)
```

Get the environment json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `env` _string_ - name of the environment


**Returns**:

- `list` - [envid or -1 if not found, name (string)]
- `string` - if id_only = False. If latest = True then latest version json is returned otherwise current version json string is returned.

<a name="dhapi.get_component_name"></a>
#### get\_component\_name

```python
get_component_name(dhurl, cookies, compid)
```

Get the full component name.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compid` _int_ - id of the component


**Returns**:

- `string` - full name of the component

<a name="dhapi.get_component_fromid"></a>
#### get\_component\_fromid

```python
get_component_fromid(dhurl, cookies, compid)
```

Get the component json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compid` _int_ - id of the component


**Returns**:

- `string` - json string for the component

<a name="dhapi.get_component_attrs"></a>
#### get\_component\_attrs

```python
get_component_attrs(dhurl, cookies, compid)
```

Get the component attributes json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compid` _int_ - id of the component


**Returns**:

- `dict` - json string to the attributes

<a name="dhapi.get_application_name"></a>
#### get\_application\_name

```python
get_application_name(dhurl, cookies, appid)
```

Get the application name.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id of the application


**Returns**:

- `string` - full name of the application

<a name="dhapi.new_component_version"></a>
#### new\_component\_version

```python
new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, component_items, compautoinc)
```

Create a new component version and base version if needed.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `kind` _string_ - docker or file
- `component_items` _list_ - component items for the file type
- `compautoinc` _boolean_ - auto increment an existing version to the new version

**Returns**:

- `int` - id of the new component, -1 if an error occurred.

<a name="dhapi.new_docker_component"></a>
#### new\_docker\_component

```python
new_docker_component(dhurl, cookies, compname, compvariant, compversion, parent_compid)
```

Create a new docker component.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `parent_compid` _int_ - parent component version for the new component

**Returns**:

- `int` - id of the new component, -1 if an error occurred.

<a name="dhapi.new_file_component"></a>
#### new\_file\_component

```python
new_file_component(dhurl, cookies, compname, compvariant, compversion, parent_compid, component_items)
```

Create a new file component.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `parent_compid` _int_ - parent component version for the new component
- `component_items` _list_ - list of items for the component

**Returns**:

- `int` - id of the new component, -1 if an error occurred.

<a name="dhapi.new_component_item"></a>
#### new\_component\_item

```python
new_component_item(dhurl, cookies, compid, kind, component_items)
```

Create a new component item for the component.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `kind` _string_ - docker or file for the component kind

**Returns**:

- `int` - id of the new component item, -1 if an error occurred.

<a name="dhapi.update_name"></a>
#### update\_name

```python
update_name(dhurl, cookies, compname, compvariant, compversion, compid)
```

Update the name of the component for the compid to the new name.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `compid` _int_ - id to the component to update the name of

**Returns**:

- `string` - json string of the component update.

<a name="dhapi.new_component"></a>
#### new\_component

```python
new_component(dhurl, cookies, compname, compvariant, compversion, kind, parent_compid)
```

Create the component object based on the component name and variant.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `kind` _string_ - docker or file for the kind of component
- `parent_compid` - id of the parent component version


**Returns**:

- `int` - component id of the new component otherwise None.

<a name="dhapi.update_component_attrs"></a>
#### update\_component\_attrs

```python
update_component_attrs(dhurl, cookies, compname, compvariant, compversion, attrs, crdatasource, crlist)
```

Update the attributes, key/value pairs, for the component and CR list.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compname` _string_ - name of the component including domain
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `attrs` _dict_ - key/value dictionary
- `crdatasource` _string_ - name of the CR data source
- `cdlist` _list_ - list of CRs to assign to the component


**Returns**:

- `list` - [True for success, otherwise False, json string of update, url for update].

<a name="dhapi.update_compid_attrs"></a>
#### update\_compid\_attrs

```python
update_compid_attrs(dhurl, cookies, compid, attrs, crdatasource, crlist)
```

Update the attributes, key/value pairs, for the component and CR list.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compid` _int_ - id of the component to update
- `attrs` _dict_ - key/value dictionary
- `crdatasource` _string_ - name of the CR data source
- `cdlist` _list_ - list of CRs to assign to the component


**Returns**:

- `list` - [True for success, otherwise False, json string of update, url for update].

<a name="dhapi.update_envid_attrs"></a>
#### update\_envid\_attrs

```python
update_envid_attrs(dhurl, cookies, envid, attrs)
```

Update the attributes, key/value pairs, for the environment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `envid` _int_ - id of the environment to update
- `attrs` _dict_ - key/value dictionary


**Returns**:

- `list` - [True for success, otherwise False, json string of update, url for update].

<a name="dhapi.get_application"></a>
#### get\_application

```python
get_application(dhurl, cookies, appname, appversion, id_only)
```

Get the application json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id of the application
- `id_only` _boolean_ - True return the id only otherwise json string


**Returns**:

- `int` - if id_only = True then return the appid otherwise return json string for the application.

<a name="dhapi.get_application_fromid"></a>
#### get\_application\_fromid

```python
get_application_fromid(dhurl, cookies, appid, appversion)
```

Get the application json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id of the application
- `appversion` _string_ - 'latest' to get the last application version


**Returns**:

- `list` - [id or -1 if not found, application name, latest version id].

<a name="dhapi.get_base_component"></a>
#### get\_base\_component

```python
get_base_component(dhurl, cookies, compid, id_only)
```

Get the base component json string.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `compid` _int_ - id of the component
- `id_only` _boolean_ - True return the id only otherwise json string


**Returns**:

- `int` - if id_only = True then return the appid otherwise return json string for the component.

<a name="dhapi.get_component_from_tag"></a>
#### get\_component\_from\_tag

```python
get_component_from_tag(dhurl, cookies, image_tag)
```

Get the component based on the docker tag.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `image_tag` _string_ - image tag


**Returns**:

- `int` - return the compid if found otherwise -1.

<a name="dhapi.new_application"></a>
#### new\_application

```python
new_application(dhurl, cookies, appname, appversion, appautoinc, envs)
```

Create a new application version and base version if needed.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of the application including domain
- `compversion` _string_ - version of the application, optional
- `appautoinc` _boolean_ - auto increment an existing version to the new version

**Returns**:

- `list` - [id of the new application, -1 if an error occurred, application name]

<a name="dhapi.add_compver_to_appver"></a>
#### add\_compver\_to\_appver

```python
add_compver_to_appver(dhurl, cookies, appid, compid)
```

Add a component version to an application version.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id of the application
- `compid` _int_ - id of the component to add to the application


**Returns**:

  no data returned

<a name="dhapi.assign_comp_to_app"></a>
#### assign\_comp\_to\_app

```python
assign_comp_to_app(dhurl, cookies, appid, compid, parent_compid, xpos, ypos)
```

Assign component to application in the correct postion in the tree.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appid` _int_ - id of the application
- `compid` _int_ - id of the component to add to the application
- `parent_compid` _int_ - parent component in the layout panel
- `xpos` _int_ - xpos in the layout panel
- `ypos` _int_ - ypos in the layout panel


**Returns**:

  no data returned

<a name="dhapi.assign_app_to_env"></a>
#### assign\_app\_to\_env

```python
assign_app_to_env(dhurl, cookies, appname, envs)
```

Assign an application to environment to enable deployments.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `appname` _string_ - name of application
- `envs` _list_ - list of environments to assign the application to


**Returns**:

  no data returned

<a name="dhapi.clone_repo"></a>
#### clone\_repo

```python
clone_repo(project)
```

Clones a repo into the working directory and reads the features.toml file into a dictionary.

**Arguments**:

- `project` _string_ - name of the github org/project to clone


**Returns**:

- `dict` - dictionary of the features.toml file.  None if no features.toml is in the repo.

<a name="dhapi.import_cluster"></a>
#### import\_cluster

```python
import_cluster(dhurl, cookies, domain, appname, appversion, appautoinc, deployenv, crdatasource, crlist, cluster_json, msname, msbranch)
```

Parse the kubernetes deployment yaml for component name and version.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `kubeyaml` _string_ - path to the output for the deployment yaml
- `defaultdomain` _string_ - domain name to use for the component


**Returns**:

  list of dict: a list of dictionary items defining the component found.

<a name="dhapi.log_deploy_application"></a>
#### log\_deploy\_application

```python
log_deploy_application(dhurl, cookies, deploydata)
```

Record a deployment of an application to an environment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `deploydata` _string_ - path to a json file that contains
  the component version, application and environment to record.


**Returns**:

- `string` - the json string from the file

<a name="dhapi.run_circleci_pipeline"></a>
#### run\_circleci\_pipeline

```python
run_circleci_pipeline(pipeline)
```

Call the CircleCI REST api to run a pipeline.

**Arguments**:

- `pipeline` _string_ - name of the pipeline to run


**Returns**:

- `string` - result of the api call.

<a name="dhapi.upload_helm"></a>
#### upload\_helm

```python
upload_helm(dhurl, cookies, fullcompname, chart, chartversion, chartvalues, helmrepo, helmrepouser, helmrepopass, helmrepourl, helmopts, deployid, dockeruser, dockerpass, helmtemplate)
```

Gather the helm chart and values and upload to the deployment log

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `fullcompname` _string_ - full name of the component including variant and version
- `chart` _string_ - name of the chart.  "chart org/chart name"
- `chartversion` _string_ - version of the chart. "" for no version
- `chartvalues` _string_ - path name to the values file for the chart
- `helmrepo` _string_ - name of the helm repo
- `helmrepouser` _string_ - username to use to login to a private repo
- `helmrepopass` _string_ - password for the helmrepouser
- `helmrepourl` _string_ - url for the helm repo
- `helmopts` _string_ - additional helm options used for the deployment
- `deployid` _int_ - deployment id to associate the helm capture to
- `dockeruser` _string_ - docker repo user used to get the image digest
- `dockerpass` _string_ - password for the dockeruser
- `helmtemplate` _string_ - path name to the file that contains the helm template output


**Returns**:

  Void

<a name="dhapi.set_kvconfig"></a>
#### set\_kvconfig

```python
set_kvconfig(dhurl, cookies, kvconfig, appname, appversion, appautoinc, compname, compvariant, compversion, compautoinc, kind, env, crdatasource, crlist)
```

Update the attributes for the component based on the properties files found in the cloned directory.

A comparision is done to see if a new component version is needed.  If a new key/values are found then
the application version will be created for the environment.

**Arguments**:

- `dhurl` _string_ - url to the server
- `cookies` _string_ - cookies from login
- `kvconfig` _string_ - a git repo or a directory to search for properties files
- `appname` _string_ - name of the application
- `appversion` _string_ - version of the application
- `appautoinc` _boolean_ - automatically create a new application version
- `compname` _string_ - name of the component
- `compvariant` _string_ - variant of the component, optional
- `compversion` _string_ - version of the component, optional
- `compautoinc` _boolean_ - automatically create a new component version
- `kind` _string_ - docker or file kind for the component
- `env` _string_ - environment to assign the key/value component to
- `crdatasource` _string_ - name of the CR data source
- `crlist` _list_ - list of CR to assign to the component


**Returns**:

  no data returned
