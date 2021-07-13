"""DeployHub RESTapi interface for Python."""

# To generate markdown use:
# pydoc-markdown -I deployhub > doc/deployhub.md

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib
from pathlib import Path
from pprint import pprint
from urllib.parse import urlparse

import configobj
import qtoml
import requests
from configobj import ConfigObj
from flatten_dict import flatten


def url_validator(url):
    try:
        result = urlparse(url)
        return True
    except:
        return False

def fspath(path):
    """See https://www.python.org/dev/peps/pep-0519/#os for details."""
    if isinstance(path, (str, bytes)):
        return path

    # Work from the object's type to match method resolution of other magic
    # methods.
    path_type = type(path)
    try:
        path = path_type.__fspath__(path)
    except AttributeError:
        # Added for Python 3.5 support.
        if isinstance(path, pathlib.Path):
            return str(path)
        elif hasattr(path_type, '__fspath__'):
            raise
    else:
        if isinstance(path, (str, bytes)):
            return path
        else:
            raise TypeError("expected __fspath__() to return str or bytes, "
                            "not " + type(path).__name__)

    raise TypeError("expected str, bytes, pathlib.Path or os.PathLike object, not "
                    + path_type.__name__)


def get_json(url, cookies):
    """
    Get URL as json string.

    Args:
        url (string): url to server
        cookies (string) - login cookies

    Returns:
        string: The json string.

    """
    try:
        res = requests.get(url, cookies=cookies)
        if (res is None):
            return None
        if (res.status_code != 200):
            return None
        return res.json()
    except requests.exceptions.ConnectionError as conn_error:
        print(str(conn_error))
    return None


def post_json(url, payload, cookies):
    """
    Post URL as json string.

    Args:
        url (string): url to server
        payload (string): json payload to post
        cookies (string): login cookies

    Returns:
        string: The json string.
    """
    try:
        res = requests.post(url, data=payload, cookies=cookies, headers={"Content-Type":"application/json"})
        if (res is None):
            return None
        if (res.status_code != 200):
            return None
        return res.json()
    except requests.exceptions.ConnectionError as conn_error:
        print(str(conn_error))
    return None


def post_json_with_header(url, token):
    """
    Post URL as json string.

    Args:
        url (string): url to server
        token (string): CircleCI token for header

    Returns:
        string: The json string
    """
    pprint(url)
    lines = subprocess.run(["curl", "-X", "POST", url, "-H", 'Accept: application/json', "-H", 'Circle-Token:' + token, "-q"], check=False, stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")
    return lines


def is_empty(my_string):
    """
    Is the string empty.

    Args:
        my_string (string): string to check emptyness on

    Returns:
        boolean: True if the string is None or blank, otherwise False.
    """
    if (isinstance(my_string, int)):
        my_string = str(my_string)
    return not (my_string and my_string.strip())


def is_not_empty(my_string):
    """
    Is the string NOT empty.

    Args:
        my_string (string): string to check emptyness on

    Returns:
        boolean: False if the string is None or blank, otherwise True.
    """
    if (isinstance(my_string, int)):
        my_string = str(my_string)

    return bool(my_string and my_string.strip())


def login(dhurl, user, password, errors):
    """
    Login to DeployHub using the DH Url, userid and password.

    Args:
        dhurl (string): url to server
        user (string): username to login with
        password (string): password for login
        errors (list): list to return any errors back to the caller

    Returns:
        string: the cookies to be used in subsequent API calls.
    """
    try:
        result = requests.post(dhurl + "/dmadminweb/API/login", data={'user': user, 'pass': password})
        cookies = result.cookies
        if (result.status_code == 200):
            data = result.json()
            if (not data.get('success', False)):
                errors.append(data.get('error', ''))
                return None
            return cookies
    except requests.exceptions.ConnectionError as conn_error:
        errors.append(str(conn_error))
    return None


def deploy_application_by_appid(dhurl, cookies, appid, env):
    """
    Deploy the application to the environment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id to the application
        env (string): full name of the environemt

    Returns:
        list: [deployment_id (int) -1 for error, message (string)].
    """
    data = get_json(dhurl + "/dmadminweb/API/deploy?app=" + str(appid) + "&env=" + urllib.parse.quote(env) + "&wait=N", cookies)

    if (data is None):
        return [-1, "Deployment Failed"]

    if (data.get('success', False)):
        return [data.get('deploymentid', -1), ""]

    return [-1, data.get('error', "")]


def deploy_application(dhurl, cookies, appname, appversion, env):
    """
    Deploy the application to the environment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of the application including domain name
        appversion (string): version of application. Should include vairiant if used.
        env (string): full name of the environment

    Returns:
        list: [deployment_id (int) -1 for error, message (string)].
    """
    data = get_application(dhurl, cookies, appname, appversion, True)
    appid = data[0]

    data = get_json(dhurl + "/dmadminweb/API/deploy?app=" + str(appid) + "&env=" + urllib.parse.quote(env) + "&wait=N", cookies)

    if (data is None):
        return [-1, "Deployment Failed"]

    if (data.get('success', False)):
        return [data.get('deploymentid', -1), ""]

    return [-1, data.get('error', "")]


def move_application(dhurl, cookies, appname, appversion, from_domain, task):
    """
    Move an application from the from_domain using the task.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of the application including domain name
        appversion (string): version of application. Should include vairiant if used.
        from_domain (string): full name of the domain to move from
        task (string): task to use to do the move

    Returns:
        list: [appid (int) -1 for error, message (string)].
    """
    data = get_application(dhurl, cookies, appname, appversion, True)
    appid = data[0]

    # Get from domainid
    data = get_json(dhurl + "/dmadminweb/API/domain/" + urllib.parse.quote(from_domain), cookies)
    fromid = str(data['result']['id'])

    # Get from Tasks
    data = get_json(dhurl + "/dmadminweb/GetTasks?domainid=" + fromid, cookies)
    taskid = "0"

    for atask in data:
        if (atask['name'] == task):
            taskid = str(atask['id'])

    # Move App Version
    data = get_json(dhurl + "/dmadminweb/RunTask?f=run&tid=" + taskid + "&notes=&id=" + appid + "&pid=" + fromid, cookies)

    if (data is None):
        return [-1, "Move Failed"]

    if (data.get('success', False)):
        return [appid, "Move Successful"]

    return [-1, data.get('error', "")]


def approve_application(dhurl, cookies, appname, appversion):
    """
    Approve the application for the current domain that it is in.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of the application including domain name
        appversion (string): version of application. Should include vairiant if used.

    Returns:
        list: [appid (int) -1 for error, message (string)].
    """
    data = get_application(dhurl, cookies, appname, appversion, True)
    appid = data[0]

    data = get_json(dhurl + "/dmadminweb/API/approve/" + appid, cookies)

    if (data is None):
        return [-1, "Approval Failed"]

    if (data.get('success', False)):
        return [appid, "Approval Successful"]

    return [-1, data.get('error', "")]


def is_deployment_done(dhurl, cookies, deployment_id):
    """
    Check to see if the deployment has completed.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        deployment_id (int): id of the deployment to check

    Returns:
        list: [True if done, otherwise False (boolean), message (string)].
    """
    data = get_json(dhurl + "/dmadminweb/API/log/" + str(deployment_id) + "?checkcomplete=Y", cookies)

    if (data is None):
        return [False, {'msg': "Could not get log #" + str(deployment_id)}]

    if (data.get('text')):
        return [False, {'msg': "Could not get log #" + str(deployment_id)}]

    return [True, data]


def get_logs(dhurl, cookies, deployid):
    """
    Get the logs for the deployment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        deployment_id (int): id of the deployment to check

    Returns:
        list: [True if successful fetch, otherwise False (boolean), output lines (string)].
    """
    done = 0

    while (done == 0):
        res = is_deployment_done(dhurl, cookies, deployid)

        if (res is not None):
            if (res[0]):
                data = res[1]
                if (data.get('success', False) and data.get('iscomplete', False)):
                    done = 1
            else:
                done = 1

        time.sleep(10)

    data = get_json(dhurl + "/dmadminweb/API/log/" + str(deployid), cookies)

    if (data is None or not data):
        return [False, "Could not get log #" + str(deployid)]

    lines = data.get('logoutput', '')
    exitcode = data.get('exitcode', 1)
    output = ""

    for line in lines:
        output = output + line + "\n"

    if (exitcode == 0):
        return [True, output]
    else:
        return [False, output]


def get_attrs(dhurl, cookies, app, comp, env, srv):
    """
    Get the attributes for this deployment base on app version and env.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of the application including domain name.
        compname (string): name of the component including domain name
        env (string): name of the environment including domain name
        srv (string): name of the end-point including domain name

    Returns:
        dict: key/value pair of attributes.
    """
    data = get_json(dhurl + "/dmadminweb/API/environment/" + urllib.parse.quote(env), cookies)
    envid = str(data['result']['id'])
    servers = data['result']['servers']

    data = get_json(dhurl + "/dmadminweb/API/getvar/environment/" + envid, cookies)
    env_attrs = data['attributes']

    for a_srv in servers:
        if (srv == a_srv['name']):
            srvid = str(a_srv['id'])
            data = get_json(dhurl + "/dmadminweb/API/getvar/server/" + srvid, cookies)
            srv_attrs = data['attributes']
            break

    data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(app), cookies)

    if (app == data['result']['name']):
        appid = str(data['result']['id'])
    else:
        for a_ver in data['result']['versions']:
            if (app == a_ver['name']):
                appid = str(a_ver['id'])
                break

    data = get_json(dhurl + "/dmadminweb/API/getvar/application/" + appid, cookies)
    app_attrs = data['attributes']

    data = get_json(dhurl + "/dmadminweb/API/component/" + comp, cookies)
    compid = str(data['result']['id'])

    data = get_json(dhurl + "/dmadminweb/API/getvar/component/" + compid, cookies)
    comp_attrs = data['attributes']

    result = {}
    for entry in env_attrs:
        result.update(entry)

    for entry in srv_attrs:
        result.update(entry)

    for entry in app_attrs:
        result.update(entry)

    for entry in comp_attrs:
        result.update(entry)

    return result


def get_application_attrs(dhurl, cookies, appid):
    """
    Get the attributes for an application.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (id): id of the application

    Returns:
        string: json string of the key/value attributes.
    """
    data = get_json(dhurl + "/dmadminweb/API/getvar/application/" + str(appid), cookies)
    app_attrs = data['attributes']
    return app_attrs


def find_domain(dhurl, cookies, findname):
    """
    Get the domain name and id that matches best with the passed in name.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        findname (string): domain name to match

    Returns:
        string or None if not found: the full domain name
    """
    data = get_json(dhurl + "/dmadminweb/GetAllDomains", cookies)
    for dom in data:
        child = dom['name'].split('.')[-1]
        if (child == findname):
            return dom
        else:
            child = child.replace(" ", "").lower()
            if (child == findname):
                dom['name'] = 'GLOBAL.Chasing Horses LLC.' + dom['name']
                return dom
    return None


def clean_name(name):
    """
    Remove periods and dashes from the name.

    Args:
        name (string): string to clean

    Returns:
        string: the name with periods and dashes changed to userscores.
    """
    if (name is None):
        return name

    name = name.replace(".", "_")
    name = name.replace("-", "_")
    return name


def get_component(dhurl, cookies, compname, compvariant, compversion, id_only, latest):
    """
    Get the component json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain name
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        id_only (boolean): return just the id and not the whole json string
        latest (boolean): return the latest version

    Returns:
        int: if id_only = True
        string: if id_only = False. If latest = True then latest version json is returned otherwise current version json string is returned.
    """
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant == "" or compvariant is None) and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    component = ""

    if (compvariant is not None and compvariant != "" and compversion is not None and compversion != ""):
        component = compname + ";" + compvariant + ";" + compversion
    elif (compvariant is not None and compvariant != ""):
        component = compname + ";" + compvariant
    else:
        component = compname

    check_compname = ""
    short_compname = ""

    if ('.' in compname):
        short_compname = compname.split('.')[-1]

    if (compvariant is not None and compvariant != "" and compversion is not None and compversion != ""):
        check_compname = short_compname + ";" + compvariant + ";" + compversion
    elif (compvariant is not None and compvariant != ""):
        check_compname = short_compname + ";" + compvariant
    else:
        check_compname = short_compname

    param = ""
    if (id_only):
        param = "&idonly=Y"

    if (latest):
        param = param + "&latest=Y"

    data = get_json(dhurl + "/dmadminweb/API/component/?name=" + urllib.parse.quote(component) + param, cookies)

    if (data is None):
        return [-1, ""]

    if (data['success']):
        compid = data['result']['id']
        name = data['result']['name']

        if (name != check_compname and 'versions' in data['result']):
            vers = data['result']['versions']
            for ver in vers:
                if (ver['name'] == check_compname):
                    compid = ver['id']
                    name = ver['name']
                    break

        return [compid, name]

    return [-1, ""]


def get_environment(dhurl, cookies, env):
    """
    Get the environment json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        env (string): name of the environment

    Returns:
        list: [envid or -1 if not found, name (string)]
        string: if id_only = False. If latest = True then latest version json is returned otherwise current version json string is returned.
    """
    name = ""
    data = get_json(dhurl + "/dmadminweb/API/environment/?name=" + urllib.parse.quote(env), cookies)

    if (data is None):
        return [-1, ""]

    if (data['success']):
        envid = data['result']['id']
        name = data['result']['name']

        return [envid, name]

    return [-1, ""]


def get_component_name(dhurl, cookies, compid):
    """
    Get the full component name.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compid (int): id of the component

    Returns:
        string: full name of the component
    """
    name = ""
    data = get_json(dhurl + "/dmadminweb/API/component/" + str(compid) + "?idonly=Y", cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['domain'] + "." + data['result']['name']
    return name


def get_component_fromid(dhurl, cookies, compid):
    """
    Get the component json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compid (int): id of the component

    Returns:
        string: json string for the component
    """
    data = get_json(dhurl + "/dmadminweb/API/component/" + str(compid), cookies)
    return data


def get_component_attrs(dhurl, cookies, compid):
    """
    Get the component attributes json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compid (int): id of the component

    Returns:
        dict: json string to the attributes
    """
    data = get_json(dhurl + "/dmadminweb/API/getvar/component/" + str(compid), cookies)

    if (data is None):
        return []

    if ('attributes' in data):
        return data['attributes']

    return []


def get_application_name(dhurl, cookies, appid):
    """
    Get the application name.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application

    Returns:
        string: full name of the application
    """
    name = ""

    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid), cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['domain'] + '.' + data['result']['name']
    return name


def new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, component_items, compautoinc):
    """
    Create a new component version and base version if needed.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        kind (string): docker or file
        component_items (list): component items for the file type
        compautoinc (boolean): auto increment an existing version to the new version
    Returns:
        int: id of the new component, -1 if an error occurred.
    """
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant == "" or compvariant is None) and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    domain = ""

    if ('.' in compname):
        parts = compname.split('.')
        if (parts):
            parts.pop()
        domain = '.'.join(parts) + "."

    # Get latest version of compnent variant
    data = get_component(dhurl, cookies, compname, compvariant, compversion, False, True)
    if (data[0] == -1):
        data = get_component(dhurl, cookies, compname, compvariant, None, False, True)
        if (data[0] == -1):
            data = get_component(dhurl, cookies, compname, "", None, False, True)

    latest_compid = data[0]
    found_compname = data[1]
    check_compname = ""
    compid = latest_compid

    short_compname = ""

    if ('.' in compname):
        short_compname = compname.split('.')[-1]

    if (compvariant is not None and compvariant != "" and compversion is not None and compversion != ""):
        check_compname = short_compname + ";" + compvariant + ";" + compversion
    elif (compvariant is not None and compvariant != ""):
        check_compname = short_compname + ";" + compvariant
    else:
        check_compname = short_compname

    # Create base component variant
    # if one is not found
    # Get the new compid of the new component variant
    if (compvariant is None):
        compvariant = ""

    if (compversion is None):
        compversion = ""

    if (latest_compid < 0):
        if (kind.lower() == "docker"):
            compid = new_docker_component(dhurl, cookies, compname, compvariant, compversion, -1)
        else:
            compid = new_file_component(dhurl, cookies, compname, compvariant, compversion, -1, None)
    else:
        # Create component items for the component
        if (compautoinc is None):
            if (found_compname == "" or found_compname != check_compname):
                if (kind.lower() == "docker"):
                    compid = new_docker_component(dhurl, cookies, compname, compvariant, compversion, compid)
                else:
                    compid = new_file_component(dhurl, cookies, compname, compvariant, compversion, compid, component_items)
            elif (compid > 0):
                if (kind.lower() == "docker"):
                    new_component_item(dhurl, cookies, compid, "docker", None)
                else:
                    new_component_item(dhurl, cookies, compid, "file", component_items)
        else:
            parts = found_compname.split(';')
            if (len(parts) >= 3):  # hipster-store;master;v1_3_334-gabc635
                latest_compname = parts[0]
                latest_compvariant = parts[1]
                latest_compversion = parts[2]
            elif (len(parts) == 2):
                latest_compname = parts[0]
                latest_compvariant = ""
                latest_compversion = parts[1]
            else:
                latest_compname = found_compname
                latest_compvariant = ""
                latest_compversion = ""

            if ("-g" in latest_compversion):  # git commit
                verschema = latest_compversion.split('-g')[0]
                gitcommit = latest_compversion.split('-g')[1]
            elif ("_g" in latest_compversion):  # git commit
                verschema = latest_compversion.split('_g')[0]
                gitcommit = latest_compversion.split('_g')[1]
            else:
                verschema = latest_compversion
                gitcommit = ""

            compid = latest_compid

            if (compvariant == verschema):
                verschema = ""

            # inc schemantic version & loop until we don't have an exisiting version
            while (compid >= 0):
                if ('_' in verschema):
                    schema_parts = verschema.split('_')
                    incnum = schema_parts.pop()
                    incnum = str(int(incnum) + 1)
                    schema_parts.append(incnum)
                    verschema = '_'.join(schema_parts) + gitcommit
                elif (verschema.isdigit()):
                    verschema = str(int(verschema) + 1) + gitcommit
                else:
                    verschema = "1" + gitcommit

                compversion = verschema

                data = get_component(dhurl, cookies, domain + compname, compvariant, compversion, True, False)
                compid = data[0]

            if (kind.lower() == "docker"):
                compid = new_docker_component(dhurl, cookies, compname, compvariant, compversion, latest_compid)
            else:
                compid = new_file_component(dhurl, cookies, compname, compvariant, compversion, latest_compid, None)

    return compid


def new_docker_component(dhurl, cookies, compname, compvariant, compversion, parent_compid):
    """
    Create a new docker component.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        parent_compid (int): parent component version for the new component
    Returns:
        int: id of the new component, -1 if an error occurred.
    """
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant is None or compvariant == "") and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    compid = 0
    # Create base version
    if (parent_compid < 0):
        data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        compid = data['result']['id']
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        compid = data['result']['id']
        update_name(dhurl, cookies, compname, compvariant, compversion, compid)

    new_component_item(dhurl, cookies, compid, "docker", None)

    return compid


def new_file_component(dhurl, cookies, compname, compvariant, compversion, parent_compid, component_items):
    """
    Create a new file component.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        parent_compid (int): parent component version for the new component
        component_items (list):  list of items for the component
    Returns:
        int: id of the new component, -1 if an error occurred.
    """
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant is None or compvariant == "") and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    compid = 0

    # Create base version
    if (parent_compid < 0):
        data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        compid = data['result']['id']
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        compid = data['result']['id']
        update_name(dhurl, cookies, compname, compvariant, compversion, compid)

    new_component_item(dhurl, cookies, compid, "file", component_items)

    return compid


def new_component_item(dhurl, cookies, compid, kind, component_items):
    """
    Create a new component item for the component.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        kind (string): docker or file for the component kind
    Returns:
        int: id of the new component item, -1 if an error occurred.
    """
    # Get compId
    if (kind.lower() == "docker" or component_items is None):
        data = get_json(dhurl + "/dmadminweb/UpdateAttrs?f=inv&c=" + str(compid) + "&xpos=100&ypos=100&kind=" + kind + "&removeall=Y", cookies)
    else:
        ypos = 100

        i = 0
        parent_item = -1

        for item in component_items:
            tmpstr = ""
            ciname = ""
            for entry in item:
                if (entry['key'].lower() == "name"):
                    ciname = entry['value']
                else:
                    tmpstr = tmpstr + "&" + urllib.parse.quote(entry['key']) + "=" + urllib.parse.quote(entry['value'])

            if (i == 0):
                tmpstr = tmpstr + "&removeall=Y"

            data = get_json(dhurl + "/dmadminweb/API/new/compitem/" + urllib.parse.quote(ciname) + "?component=" + str(compid) + "&xpos=100&ypos=" + str(ypos) + "&kind=" + kind + tmpstr)

            if (data.size() > 0 and data['result'] is not None):
                if (parent_item > 0):
                    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=iad&c=" + str(compid) + "&fn=" + str(parent_item) + "&tn=" + str(data['result']['id']))
                parent_item = data['result']['id']

            ypos = ypos + 100
            i = i+1
    return data


def update_name(dhurl, cookies, compname, compvariant, compversion, compid):
    """
    Update the name of the component for the compid to the new name.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        compid (int): id to the component to update the name of
    Returns:
        string: json string of the component update.
    """
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant is None or compvariant == "") and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    if ('.' in compname):
        compname = compname.split('.')[-1]

    if (compvariant is not None and compvariant != "" and compversion is not None and compversion != ""):
        data = get_json(dhurl + "/dmadminweb/UpdateSummaryData?objtype=23&id=" + str(compid) + "&change_1=" + urllib.parse.quote(compname + ";" + compvariant + ";" + compversion), cookies)
    elif (compvariant is not None and compvariant != ""):
        data = get_json(dhurl + "/dmadminweb/UpdateSummaryData?objtype=23&id=" + str(compid) + "&change_1=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
    else:
        data = get_json(dhurl + "/dmadminweb/UpdateSummaryData?objtype=23&id=" + str(compid) + "&change_1=" + urllib.parse.quote(compname), cookies)

    return data


def new_component(dhurl, cookies, compname, compvariant, compversion, kind, parent_compid):
    """
    Create the component object based on the component name and variant.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        kind (string): docker or file for the kind of component
        parent_compid: id of the parent component version

    Returns:
        int: component id of the new component otherwise None.
    """
    # Create base version
    if (parent_compid is None):
        data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        compid = data['result']['id']
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        compid = data['result']['id']

    update_name(dhurl, cookies, compname, compvariant, compversion, compid)

    if (kind is not None):
        new_component_item(dhurl, cookies, compid, kind)

    return compid


def update_component_attrs(dhurl, cookies, compname, compvariant, compversion, attrs, crdatasource, crlist):
    """
    Update the attributes, key/value pairs, for the component and CR list.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (string): name of the component including domain
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        attrs (dict): key/value dictionary
        crdatasource (string): name of the CR data source
        cdlist (list): list of CRs to assign to the component

    Returns:
        list: [True for success, otherwise False, json string of update, url for update].
    """
    # Get latest version of compnent variant
    data = get_component(dhurl, cookies, compname, compvariant, compversion, True, False)
    compid = data[0]

    if (compid < 0):
        return

    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid), payload, cookies)
    if (data is None):
        return [False, "Could not update attributes on '" + compname + "'"]

    if (is_not_empty(crdatasource)):
        get_json(dhurl + "/dmadminweb/API2/assign/defect/cv" + str(compid) + "?del=y", cookies)

        allcrs = ",".join(crlist)
        crlist = allcrs.split(',')

        for bugid in crlist:
            bugid = bugid.strip()
            get_json(dhurl + "/dmadminweb/API2/assign/defect/cv" + str(compid) + "?ds=" + urllib.parse.quote(crdatasource) + "&bugid=" + str(bugid), cookies)

    return [True, data, dhurl + "/dmadminweb/API/setvar/component/" + str(compid)]


def update_compid_attrs(dhurl, cookies, compid, attrs, crdatasource, crlist):
    """
    Update the attributes, key/value pairs, for the component and CR list.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compid (int): id of the component to update
        attrs (dict): key/value dictionary
        crdatasource (string): name of the CR data source
        cdlist (list): list of CRs to assign to the component

    Returns:
        list: [True for success, otherwise False, json string of update, url for update].
    """
    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid) + "?delattrs=y", payload, cookies)
    if (data is not None and data.get('error', None) is not None):
        return [False, "Could not update attributes on '" + str(compid) + "' " + data.get('error', '')]

    if (is_not_empty(crdatasource)):
        for bugid in crlist:
            get_json(dhurl + "/dmadminweb/API2/assign/defect/" + str(compid) + "?ds=" + crdatasource + "&bugid=" + str(bugid))

    return [True, data, dhurl + "/dmadminweb/API/setvar/component/" + str(compid)]


def update_envid_attrs(dhurl, cookies, envid, attrs):
    """
    Update the attributes, key/value pairs, for the environment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        envid (int): id of the environment to update
        attrs (dict): key/value dictionary

    Returns:
        list: [True for success, otherwise False, json string of update, url for update].
    """
    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/environment/" + str(envid), payload, cookies)
    if (not data):
        return [False, "Could not update attributes on '" + str(envid) + "'"]
    return [True, data, dhurl + "/dmadminweb/API/setvar/environment/" + str(envid)]


def get_application(dhurl, cookies, appname, appversion, id_only):
    """
    Get the application json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application
        id_only (boolean): True return the id only otherwise json string

    Returns:
        int: if id_only = True then return the appid otherwise return json string for the application.
    """
    appversion = clean_name(appversion)

    application = ""

    param = ""
    if (id_only):
        param = "&idonly=Y"

    if (appversion.lower() == "latest"):
        param = param + "&latest=Y"
        appversion = ""

    if (appversion is not None and appversion != ""):
        application = appname + ";" + appversion
    else:
        application = appname

    data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(application) + param, cookies)

    if (data is None):
        return [-1, "", -1]

    if (data.get('success', False)):
        result = data.get('result', None)
        if (result):
            appid = result.get('id', -1)
            name = result.get('name', "")
            vlist = result.get('versions', None)
            latest = -1

        if (vlist):
            latest = vlist[-1]['id']
            return [appid, name, latest]
        return [appid, name, appid]

    return [-1, "", -1]


def get_application_fromid(dhurl, cookies, appid, appversion):
    """
    Get the application json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application
        appversion (string): 'latest' to get the last application version

    Returns:
        list: [id or -1 if not found, application name, latest version id].
    """
    appversion = clean_name(appversion)
    param = ""

    if (appversion.lower() == "latest"):
        param = "?latest=Y"
        appversion = ""

    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid) + param, cookies)

    if (data is None):
        return [-1, "", -1]

    if (data.get('success', False)):
        result = data.get('result', None)
        if (result):
            appid = result.get('id', -1)
            name = result.get('name', "")
            vlist = result.get('versions', None)
            latest = -1

        if (vlist):
            latest = vlist[-1]['id']
            return [appid, name, latest]
        return [appid, name, appid]

    return [-1, "", -1]


def get_base_component(dhurl, cookies, compid, id_only):
    """
    Get the base component json string.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compid (int): id of the component
        id_only (boolean): True return the id only otherwise json string

    Returns:
        int: if id_only = True then return the appid otherwise return json string for the component.
    """
    data = get_json(dhurl + "/dmadminweb/API/basecomponent/" + str(compid), cookies)

    if (data is None):
        return [-1, "", -1]

    result = data.get('result', None)

    if (result is None):
        return [-1, "", -1]

    return result['id']

def get_component_from_tag(dhurl, cookies, image_tag):
    """
    Get the component based on the docker tag.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        image_tag (string): image tag

    Returns:
        int: return the compid if found otherwise -1.
    """
    data = get_json(dhurl + "/dmadminweb/API/comp4tag?image=" + image_tag, cookies)

    if (data is None):
        return -1

    id = data.get('id', -1)

    return id


def new_application(dhurl, cookies, appname, appversion, appautoinc, envs):
    """
    Create a new application version and base version if needed.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of the application including domain
        compversion (string): version of the application, optional
        appautoinc (boolean): auto increment an existing version to the new version
    Returns:
        list: [id of the new application, -1 if an error occurred, application name]
    """
    appversion = clean_name(appversion)

    appid = 0
    parent_appid = -1

    domain = ""

    if (is_empty(appversion) and ';' in appname):
        parts = appname.split(';')
        appversion = parts.pop()
        appname = ';'.join(parts)

    full_appname = appname

    if ('.' in appname):
        parts = appname.split('.')
        if (parts):
            parts.pop()
        domain = '.'.join(parts)
        domain = "domain=" + urllib.parse.quote(domain)
        appname = appname.split('.')[-1]

    # Get Base Version
    data = get_application(dhurl, cookies, full_appname, "", True)
    parent_appid = data[0]

    # Create base version
    if (parent_appid < 0):
        data = get_json(dhurl + "/dmadminweb/API/new/application/?name=" + urllib.parse.quote(appname) + "&" + domain, cookies)
        if (data.get('success', False)):
            data = get_application(dhurl, cookies, appname, "", True)
            parent_appid = data[0]

        if (envs is not None):
            for env in envs:
                data = get_json(dhurl + "/dmadminweb/API/assign/application/?name=" + urllib.parse.quote(full_appname) + "&env=" + urllib.parse.quote(env), cookies)

    # Refetch parent to get version list

    data = get_application(dhurl, cookies, full_appname, "latest", False)
    latest_appid = data[0]

    # Refetch the current app version to see if we need to create it or not
    data = get_application(dhurl, cookies, full_appname, appversion, True)
    appid = data[0]

    # inc schemantic version & loop until we don't have an exisiting version
    while (appautoinc is not None and appid >= 0):
        ver = appversion
        if ('_' in ver):
            schema_parts = ver.split('_')
            incnum = schema_parts.pop()
            incnum = str(int(incnum) + 1)
            schema_parts.append(incnum)
            ver = '_'.join(schema_parts)
        elif (ver.isdigit()):
            ver = str(int(ver) + 1)
        else:
            ver = "1"

        appversion = ver

        data = get_application(dhurl, cookies, full_appname, appversion, True)
        appid = data[0]

    if (appid < 0):
        data = get_json(dhurl + "/dmadminweb/API/newappver/" + str(latest_appid) + "/?name=" + urllib.parse.quote(appname + ";" + appversion) + "&" + domain, cookies)

        if (not data.get('success', False)):
            return [-1, data.get('error', "")]

        appid = data['result']['id']

    return [appid, full_appname + ";" + appversion]


def add_compver_to_appver(dhurl, cookies, appid, compid):
    """
    Add a component version to an application version.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application
        compid (int): id of the component to add to the application

    Returns:
        no data returned
    """
    replace_compid = -1
    basecompid = get_base_component(dhurl, cookies, compid, True)
    lastcompid = 0
    xpos = 100
    ypos = 100
    complist = []

    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid), cookies)

    if (data is None):
        return [-1, "", -1]

    if (data.get('success', False)):
        result = data.get('result', None)
        if (result):
            complist = result.get('components', [])
            lastcompid = result.get('lastcompver', -1)

            for comp in complist:
                app_basecompid = get_base_component(dhurl, cookies, comp['id'], True)
                if (app_basecompid == basecompid):
                    replace_compid = comp['id']

                if (comp['id'] == lastcompid):
                    xpos = comp['xpos']
                    ypos = comp['ypos'] + 100

    if (replace_compid >= 0):
        data = get_json(dhurl + "/dmadminweb/API/replace/" + str(appid) + "/" + str(replace_compid) + "/" + str(compid), cookies)
    else:
        assign_comp_to_app(dhurl, cookies, appid, compid, lastcompid, xpos, ypos)


def assign_comp_to_app(dhurl, cookies, appid, compid, parent_compid, xpos, ypos):
    """
    Assign component to application in the correct postion in the tree.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application
        compid (int): id of the component to add to the application
        parent_compid (int): parent component in the layout panel
        xpos (int): xpos in the layout panel
        ypos (int): ypos in the layout panel

    Returns:
        no data returned
    """
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acd&a=" + str(appid) + "&c=" + str(compid), cookies)
  #  print(dhurl + "/dmadminweb/UpdateAttrs?f=acvm&a=" + str(appid) + "&c=" + str(compid) + "&xpos=" + str(xpos) + "&ypos=" + str(ypos))
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acvm&a=" + str(appid) + "&c=" + str(compid) + "&xpos=" + str(xpos) + "&ypos=" + str(ypos), cookies)
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=cal&a=" + str(appid) + "&fn=" + str(parent_compid) + "&tn=" + str(compid), cookies)


def assign_app_to_env(dhurl, cookies, appname, envs):
    """
    Assign an application to environment to enable deployments.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appname (string): name of application
        envs (list): list of environments to assign the application to

    Returns:
        no data returned
    """
    domain = ""
    if ('.' in appname):
        parts = appname.split('.')
        if (parts):
            parts.pop()
        domain = '.'.join(parts)
        domain = "domain=" + urllib.parse.quote(domain)
        appname = appname.split('.')[-1]
    if (envs is not None):
        for env in envs:
            get_json(dhurl + "/dmadminweb/API/assign/application/?name=" + urllib.parse.quote(appname) + "&env=" + urllib.parse.quote(env), cookies)


def clone_repo(project):
    """
    Clones a repo into the working directory and reads the features.toml file into a dictionary.

    Args:
        project (string): name of the github org/project to clone

    Returns:
        dict: dictionary of the features.toml file.  None if no features.toml is in the repo.
    """
    print("### Grabbing features.toml ###")

    tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)
    print(tempdir)

    pid = subprocess.Popen('git clone -q git@github.com:' + project + '.git .', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in pid.stdout.readlines():
        print(line)
        pid.wait()

    data = None
    if (not os.path.exists("features.toml")):
        print("features.toml not found")
        return data

    with open("features.toml", "r") as fin:
        tmpstr = fin.read()
        data = qtoml.loads(tmpstr)
    return data


def import_cluster(dhurl, cookies, domain, appname, appversion, appautoinc, deployenv, crdatasource, crlist, cluster_json, msname, msbranch):
    """
    Parse the kubernetes deployment yaml for component name and version.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        kubeyaml (string): path to the output for the deployment yaml
        defaultdomain (string): domain name to use for the component

    Returns:
        list of dict: a list of dictionary items defining the component found.
    """
    newvals = {}
    complist = []

    if (appversion is None):
        appversion = ""

    if (os.path.exists(cluster_json)):
        stream = open(cluster_json, 'r')
        values = json.load(stream)
        newvals.update(values)
        stream.close()

        items = newvals['items']
        branch_containers = []
        master_containers = {}
        deployed_ms = {}

        for item in items:
            deploy_time = item['metadata']['creationTimestamp']
            labels = item['metadata']['labels']
            branch = labels.get('git/branch', 'main')
            msversion = labels.get('app.kubernetes.io/version', '')
            msdigest = labels.get('app.kubernetes.io/digest', '')
            compid = -1

            containers = item['spec']['template']['spec']['containers']
            for container in containers:
                full_msname = container['name']
                image = container['image']
                repo = image.split(':')[0]
                tag = image.split(':')[1]
                short_msname = repo.split('/')[-1]
                compname = domain + "." + short_msname
                compvariant = branch
                compversion = tag

                if (full_msname == msname):
                    deployed_ms = {'compid' : compid, 'compname': compname, 'compvariant': compvariant, 'compversion': compversion, 'full_msname': full_msname, 'msname': short_msname, 'branch': branch, 'repo': repo, 'tag': tag, 'deploy_time': deploy_time}

                if (branch in ('master', 'main')):
                    if (not msversion.startswith('1.') and msversion != "1"):
                        continue

                    latest_container = master_containers.get(short_msname, None)
                    if (latest_container is None):
                        master_containers[short_msname] = {'compid' : compid, 'compname': compname, 'compvariant': compvariant, 'compversion': compversion, 'full_msname': full_msname, 'msname': short_msname, 'branch': branch, 'repo': repo, 'tag': tag, 'deploy_time': deploy_time}
                    elif (latest_container['deploy_time'] <= deploy_time):
                        master_containers[short_msname] = {'compid' : compid, 'compname': compname, 'compvariant': compvariant, 'compversion': compversion, 'full_msname': full_msname, 'msname': short_msname, 'branch': branch, 'repo': repo, 'tag': tag, 'deploy_time': deploy_time}
                elif (msbranch is not None and branch == msbranch):
                    branch_containers.append({'compid' : compid, 'compname': compname, 'compvariant': compvariant, 'compversion': compversion, 'full_msname': full_msname, 'msname': short_msname, 'branch': branch, 'repo': repo, 'tag': tag, 'deploy_time': deploy_time})

        if (msbranch is not None):
            complist = []
            if (len(deployed_ms) == 0):
                deployed_ms = {'compid': -1, 'msname': '', 'tag': '', 'branch': ''}
            else:
                complist.append(deployed_ms)

            for container in master_containers.values():
                if (deployed_ms['msname'] != container['msname']):
                    complist.append(container)
                elif (deployed_ms['branch'] == container['branch'] and msbranch not in ('master', 'main')):
                    complist.append(container)

        compid_list = []
        for item in complist:
            data = get_component(dhurl, cookies, item['compname'], item['compvariant'], item['compversion'], True, False)
            compid = -1
            if (data is not None):
                compid = data[0]
            if (compid == -1):
                print("Adding missing component: " + item['compname'] + ";" + item['compvariant'] + ";" + item['compversion'])
                compid = new_docker_component(dhurl, cookies, item['compname'], item['compvariant'], item['compversion'], -1)
                if (compid > 0):
                    update_compid_attrs(dhurl, cookies, compid, {'DockerTag': tag, 'DockerRepo': repo}, crdatasource, crlist)
            else:
                print(item['compname'] + ";" + item['compvariant'] + ";" + item['compversion'])
            compid_list.append({'compid': compid, 'name': item['compname'] + ";" + item['compvariant'] + ";" + item['compversion']})

        if (len(compid_list) > 0):
            app = appname
            if (appversion is not None and is_not_empty(appversion)):
                app = appname + ";" + appversion
            data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(app) + "&latest=Y", cookies)
            appid = -1
            if (data is not None and data['success']):
                appid = data['result']['id']

            existing_ids = []

            if (appid > 0):
                data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid), cookies)
                existing_comps = data['result']['components']

                for comp in existing_comps:
                    existing_ids.append(comp['id'])

            new_ids = []
            for item in compid_list:
                new_ids.append(item['compid'])


            if (areEqual(existing_ids, new_ids)):
                print("Application Version " + appname + ";" + appversion + " already exists")
            else:
                data = new_application(dhurl, cookies, appname, appversion, appautoinc, envs)
                if (data is not None):
                    appid = data[0]

                for compid in existing_ids:
                    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acd&a=" + str(appid) + "&c=" + str(compid), cookies)

                for item in compid_list:
                    compid = item['compid']
                    name = item['name']
                    print("Assigning Component Version " + name + " to Application Version " + appname + ";" + appversion)
                    add_compver_to_appver(dhurl, cookies, appid, compid)

            # create env and deploy to env
            deploydata = "deploy.json"
            deploy = {}
            deploy['application'] = appid
            deploy['environment'] = deployenv
            deploy['rc'] = 0
            with open(deploydata, 'w') as fp:
                json.dump(deploy, fp)
            fp.close()
            log_deploy_application(dhurl, cookies, deploydata)
    return

def areEqual(arr1, arr2):
    n = len(arr1)
    m = len(arr2)

    # If lengths of array are not
    # equal means array are not equal
    if (n != m):
        return False

    # Sort both arrays
    arr1.sort()
    arr2.sort()

    # Linearly compare elements
    for i in range(n):
        if (arr1[i] != arr2[i]):
            return False

    # If all elements were same.
    return True

def log_deploy_application(dhurl, cookies, deploydata):
    """
    Record a deployment of an application to an environment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        deploydata (string): path to a json file that contains
                             the component version, application and environment to record.

    Returns:
        string: the json string from the file
    """
    url = dhurl + "/dmadminweb/API/deploy"

    payload = ""
    with open(deploydata, "r") as fin_data:
        payload = fin_data.read()

    data = {}
    if (is_not_empty(payload)):
        data = json.loads(payload)

        compversion = data.get('compversion', None)
        environment = data.get('environment', '')
        application = data.get('application', '')

        if (is_not_empty(application) and is_not_empty(environment)):

            result = post_json(url, payload, cookies)
            data['deployid'] = result.get('deployid', -1)
            data['application'] = result.get('application', application)
            data['appid'] = result.get('appid', -1)
            application = data['application']

            print(f'Recorded deployment of {application} for {environment}')

            if (compversion is not None and len(compversion) > 0):
                print('Assigned components to ' + application + ':')
                print('  ' + "\n  ".join(compversion))

            if (result.get('errormsg', None) is not None):
                print(result.get('errormsg', None))

    return data


def run_circleci_pipeline(pipeline):
    """
    Call the CircleCI REST api to run a pipeline.

    Args:
        pipeline (string): name of the pipeline to run

    Returns:
        string: result of the api call.
    """
    url = "https://circleci.com/api/v2/project/" + pipeline + "/pipeline"
    data = post_json_with_header(url, os.environ.get("CI_TOKEN", ""))
    return data

def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def upload_helm(dhurl, cookies, fullcompname, chart, chartversion, chartvalues, helmrepo, helmrepouser, helmrepopass, helmrepourl, helmopts, deployid, dockeruser, dockerpass, helmtemplate):
    """
    Gather the helm chart and values and upload to the deployment log

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        fullcompname (string): full name of the component including variant and version
        chart (string): name of the chart.  "chart org/chart name"
        chartversion (string): version of the chart. "" for no version
        chartvalues (string):  path name to the values file for the chart
        helmrepo (string): name of the helm repo
        helmrepouser (string): username to use to login to a private repo
        helmrepopass (string): password for the helmrepouser
        helmrepourl (string): url for the helm repo
        helmopts (string): additional helm options used for the deployment
        deployid (int):  deployment id to associate the helm capture to
        dockeruser (string): docker repo user used to get the image digest
        dockerpass (string): password for the dockeruser
        helmtemplate (string): path name to the file that contains the helm template output

    Returns:
        Void
    """
    my_env = os.environ.copy()

    if not os.path.exists('helm'):
        os.makedirs('helm')

    print("Starting Helm Capture for Deployment #" + str(deployid))
    os.makedirs(os.path.dirname("helm/" + chartvalues), exist_ok=True)

    content_list = []

    if (os.path.isfile("helm/" + chartvalues)):
        my_file = open("helm/" + chartvalues, "r")
        content_list = my_file.readlines()
        my_file.close()

    content_list = list(filter(lambda x: 'pwd' not in x, content_list))
    content_list = list(filter(lambda x: 'pass' not in x, content_list))
    content_list = list(filter(lambda x: 'userid' not in x, content_list))
    content_list = list(filter(lambda x: 'username' not in x, content_list))
    content_list = list(filter(lambda x: 'aws_access_key_id' not in x, content_list))
    content_list = list(filter(lambda x: 'aws_secret_access_key' not in x, content_list))
    content_list = list(filter(lambda x: 'serviceprincipal' not in x, content_list))
    content_list = list(filter(lambda x: 'tenant' not in x, content_list))

    if (is_not_empty(chartvalues)):
        my_file = open("helm/" + chartvalues, "w")
        my_file.writelines(content_list)
        my_file.close()

    os.chdir('helm')

    upload = {}
    upload['files'] = []
    upload['component'] = fullcompname
    upload['deployid'] = deployid
    upload['helmrepo'] = helmrepo
    upload['helmrepourl'] = helmrepourl

    if ('/' not in chart):
        chart = 'library/' + chart

    upload['chartorg'] = chart.split('/')[0]
    upload['chartname'] = chart.split('/')[1]
    upload['chartversion'] = chartversion

    my_env['chartname'] = upload['chartname']
    my_env['chartorg'] = upload['chartorg']
    my_env['chartvalues'] = chartvalues
    my_env['chartversion'] = upload['chartversion']
    my_env['dockerpass'] = dockerpass
    my_env['dockeruser'] = dockeruser
    my_env['helmopts'] = helmopts
    my_env['helmrepo'] = upload['helmrepo']
    my_env['helmrepopass'] = helmrepopass
    my_env['helmrepourl'] = upload['helmrepourl']
    my_env['helmrepouser'] = helmrepouser
    my_env['helmtemplate'] = helmtemplate

    pid = subprocess.Popen(get_script_path() + "/helminfo.sh", env=my_env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    jstr = ""
    for line in pid.stdout.readlines():
        line = line.decode('utf-8')
        jstr = jstr + line

    pid.wait()
    print("# Helminfo Output")
    # pprint(jstr)
    dobj = json.loads(jstr)
    upload['chartdigest'] = dobj.get("chartdigest", "")
    upload['images'] = dobj.get("images", [])

    start_dir = "."

    filelist = []
    for root, d_names, f_names in os.walk(start_dir):  # pylint: disable=W0612
        for fname in f_names:
            if ('.DS_Store' not in fname):
                filelist.append(os.path.join(root, fname))

    filelist.sort()

    for fname in filelist:
        contents = {}
        contents['filename'] = fname

        file1 = open(fname, "rb")
        data = file1.read()
        file1.close()

        # second: base64 encode read data
        # result: bytes (again)
        base64_bytes = base64.b64encode(data)

        # third: decode these bytes to text
        # result: string (in utf-8)
        base64_string = base64_bytes.decode("utf-8")

        contents['data'] = base64_string
        upload['files'].append(contents)

    errors = []

    print("# Helminfo Upload")
    # pprint(upload)
    data = post_json(dhurl + "/dmadminweb/API/uploadhelm", json.dumps(upload), cookies)
    # pprint(data)
    print("Finished Helm Capture for Deployment #" + str(deployid))

def set_kvconfig(dhurl, cookies, kvconfig, appname, appversion, appautoinc, compname, compvariant, compversion, compautoinc, kind, env, crdatasource, crlist):
    """
    Update the attributes for the component based on the properties files found in the cloned directory.

    A comparision is done to see if a new component version is needed.  If a new key/values are found then
    the application version will be created for the environment.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        kvconfig (string): a git repo or a directory to search for properties files
        appname (string): name of the application
        appversion (string): version of the application
        appautoinc (boolean): automatically create a new application version
        compname (string): name of the component
        compvariant (string): variant of the component, optional
        compversion (string): version of the component, optional
        compautoinc (boolean): automatically create a new component version
        kind (string): docker or file kind for the component
        env (string): environment to assign the key/value component to
        crdatasource (string): name of the CR data source
        crlist (list): list of CR to assign to the component

    Returns:
        no data returned
    """
    if (is_empty(compvariant)):
        compvariant = ""

    if (is_empty(compvariant) and "-v" in compversion):
        compvariant = compversion.split("-v")[0]
        compversion = "v" + compversion.split("-v")[1]

    if (is_empty(compvariant) and "-V" in compversion):
        compvariant = compversion.split("-V")[0]
        compversion = "v" + compversion.split("-V")[1]

    saveappver = ""
    if (is_not_empty(appversion)):
        saveappver = appversion

    pwd = ""
    tempdir = ""

    if ('git@' in kvconfig):
        print("### Grabbing Config from Git ###")

        if ('#' in kvconfig):
            gitbranch = kvconfig.split('#')[1]
            kvconfig = kvconfig.split('#')[0]
        else:
            gitbranch = "master"

        repo = '/'.join(kvconfig.split('/')[:2])
        kvconfig = '/'.join(kvconfig.split('/')[1:])
        gitdir = kvconfig.split('/')[0]
        kvconfig = '/'.join(kvconfig.split('/')[1:])

        pwd = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)
        print(tempdir)

        lines = subprocess.run(['git', 'clone', '-q', repo], check=False, stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")
        for line in lines:
            print(line)

        os.chdir(gitdir)
        lines = subprocess.run(['git', 'checkout', gitbranch], check=False, stdout=subprocess.PIPE).stdout.decode('utf-8').split("\n")
        for line in lines:
            print(line)

    normal_dict = {}
    for file_path in Path(kvconfig).glob('**/*.properties'):
        filename = fspath(file_path)

        try:
            print(filename)
            config = ConfigObj(filename, encoding='iso-8859-1')
            filename = filename[len(kvconfig)+1:]
            normal_dict[filename] = config.dict()
        except configobj.ConfigObjError as error:
            print(error)

    flat_dict = flatten(normal_dict, reducer='path')

    if (is_not_empty(tempdir) and is_not_empty(pwd)):
        os.chdir(pwd)
    #    rmtree(tempdir)

    attrs = {}
    for key, value in flat_dict.items():
        if (isinstance(value, list)):
            value = ' '.join(value)

        attrs[key] = value

    print("")

    # create component version
    print("Getting Latest Component")
    data = get_component(dhurl, cookies, compname, compvariant, compversion, False, True)
    latest_compid = data[0]

    if (latest_compid < 0):
        data = get_component(dhurl, cookies, compname, "", "", False, True)
        latest_compid = data[0]

    old_attrs = []
    if (latest_compid > 0):
        comp_attrs = get_component_attrs(dhurl, cookies, latest_compid)

        for attr in comp_attrs:
            key = list(attr.keys())[0]
            value = attr[key]
            key = key.replace("\\\\", "/")
            key = key.replace("\\", "/")
            old_attrs.append(key + "=" + value)

    new_attrs = []
    for key, value in attrs.items():
        key = key.replace("\\\\", "/")
        key = key.replace("\\", "/")
        value = value.replace("\\", "\\\\")
        new_attrs.append(key + "=" + value)

    diffs = set(new_attrs) ^ set(old_attrs)

    print("Comparing KV: %d Changes" % len(diffs))

    if (len(diffs) > 0):
        pprint(list(diffs))
        compid = new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, None, compautoinc)
        print("Creation Done: " + get_component_name(dhurl, cookies, compid))

        print("Updating Component Attributes\n")

        data = update_compid_attrs(dhurl, cookies, compid, attrs, crdatasource, crlist)

        print("Attribute Update Done")
    else:
        data = get_component(dhurl, cookies, compname, compvariant, compversion, True, True)
        compid = data[0]

    if (is_not_empty(appname)):

        if (is_not_empty(saveappver)):
            appversion = saveappver

        if (is_empty(appversion)):
            parts = appname.split(';')
            if (len(parts) == 3):
                appname = parts[0] + ';' + parts[1]
                appversion = parts[2]

        if (is_empty(appversion)):
            parts = appname.split(';')
            if (len(parts) == 3):
                appname = parts[0] + ';' + parts[1]
                appversion = parts[2]

        if (is_empty(appversion)):
            appversion = ""

#            print("Creating Application Version '" + str(appname) + "' '" + appversion + "'")
#            data = new_application(dhurl, cookies, appname, appversion, appautoinc, None)
#            appid = data[0]
#            print("Creation Done: " + get_application_name(dhurl, cookies, appid))
#
#            print("Assigning Component Version to Application Version " + str(appid))
#
#            data = add_compver_to_appver(dhurl, cookies, appid, compid)
#            print("Assignment Done")

        if (is_not_empty(env)):
            data = get_environment(dhurl, cookies, env)
            envid = data[0]

            data = get_application(dhurl, cookies, appname, appversion, False)

            appid = data[0]
            appname = data[1]

            config_component = get_component_name(dhurl, cookies, compid)
            if ('.' in config_component):
                config_component = config_component.split('.')[-1]

            print(f'Updating environment {env} with config component {config_component}')

            attrs = {}
            attrs["Config Component"] = "<a href='javascript:void(0);' onclick=\"chgsel({t: 'components_tab', id: 'cv" + str(compid) + "', odl: '', tm: 'application_menu', name: '" + config_component + "'})\" >" + config_component + "</a>"
            attrs["Last Deployed Application"] = "<a href='javascript:void(0);' onclick=\"chgsel({t: 'applications_tab', id: 'av" + str(appid) + "', odl: '', tm: 'application_menu', name: '" + appname + "'})\" >" + appname + "</a>"

            update_envid_attrs(dhurl, cookies, envid, attrs)
    return

def post_textfile(dhurl, cookies, compid, filename, file_type):

    file_data = ''
    if (os.path.exists(filename)):
        file_data = open(filename, 'rb').read()
    else:
        try:
            res = requests.get(filename)
            if (res.status_code == 200):
                file_data = res.content
        except requests.exceptions.ConnectionError as conn_error:
            print(str(conn_error))

    encoded_bytes = base64.encodebytes(file_data)

    file = []
    line_no = 1
    for line in encoded_bytes.splitlines():
        d = line.decode('utf-8')
        line_no += 1
        file.append(d)

    payload = {'compid': compid, 'filetype': file_type, 'file': file}
    result = post_json(dhurl+"/msapi/textfile/", json.dumps(payload), cookies)

    if (result is None):
        return ({"message": "Could not persist '" + filename + "' with compid: '" + str(compid) + "'"})
    return result

def update_deppkgs(dhurl, cookies, compid, filename):
    payload = ""
    with open(filename, "r") as fin_data:
        data = json.load(fin_data)
        payload = json.dumps(data)

    result = post_json(dhurl+"/msapi/deppkg?compid=" + str(compid), payload, cookies)

    if (result is None):
        return ({"message": "Could not persist '" + filename + "' with compid: '" + str(compid) + "'"})
    return result
