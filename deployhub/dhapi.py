"""DeployHub RESTapi interface for Python."""

# pylint: disable=E0401,E0611
# pyright: reportMissingImports=false,reportMissingModuleSource=false

# To generate markdown use:
# pydoc-markdown -I deployhub > doc/deployhub.md

import base64
import io
import json
import os
import subprocess  # nosec B404
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from pprint import pprint

import certifi
import configobj
import qtoml
import requests
from configobj import ConfigObj
from flatten_dict import flatten


def url_validator(url):
    try:
        urllib.parse.urlparse(url)
        return True
    except BaseException:
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
        if isinstance(path, Path):
            return str(path)
        elif hasattr(path_type, "__fspath__"):
            raise
    else:
        if isinstance(path, (str, bytes)):
            return path
        else:
            raise TypeError("expected __fspath__() to return str or bytes, " "not " + type(path).__name__)

    raise TypeError("expected str, bytes, pathlib.Path or os.PathLike object, not " + path_type.__name__)


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
        res = requests.get(url, cookies=cookies, timeout=300)
        if res is None:
            return None
        if res.status_code != 200:
            return None
        return res.json()
    except requests.exceptions.ConnectionError as conn_error:
        print(str(conn_error))
    except Exception as err:
        print(f"Other error occurred: {err}")
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
        if "/import" in url:
            res = requests.post(url, data=payload, cookies=cookies, headers={"Content-Type": "application/json"}, timeout=1800)
        else:
            res = requests.post(url, data=payload, cookies=cookies, headers={"Content-Type": "application/json", "host": "console.deployhub.com"}, timeout=300)

        if res is None:
            return None

        if res.status_code < 200 and res.status_code > 299:
            return None

        try:
            json_data = res.json()
            return json_data
        except ValueError:
            return {}
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

    cmd = " ".join(["curl", "-X", "POST", url, "-H", "Accept: application/json", "-H", "Circle-Token:" + token, "-q"])
    lines = run_cmd(cmd).split("\n")
    return lines


def is_empty(my_string):
    """
    Is the string empty.

    Args:
        my_string (string): string to check emptyness on

    Returns:
        boolean: True if the string is None or blank, otherwise False.
    """
    if isinstance(my_string, int):
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
    if isinstance(my_string, int):
        my_string = str(my_string)

    return bool(my_string and my_string.strip())


def sslcerts(dhurl, customcert):
    try:
        requests.get(dhurl, timeout=3000)
    except requests.exceptions.SSLError:
        print("Adding custom certs to certifi store...")
        cafile = certifi.where()
        ca = ""
        customca = ""
        with open(customcert, "rb") as infile:
            customca = infile.read()
        with open(cafile, "rb") as infile:
            ca = infile.read()

        temp_dir = tempfile.TemporaryDirectory().name

        with open(temp_dir + "/customca.pem", "ab") as outfile:
            outfile.write(ca)
            outfile.write(customca)
        os.environ["REQUESTS_CA_BUNDLE"] = temp_dir + "/customca.pem"


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
        result = requests.post(dhurl + "/dmadminweb/API/login", data={"user": user, "pass": password}, timeout=300)
        cookies = result.cookies
        if result.status_code == 200:
            data = result.json()
            if not data.get("success", False):
                errors.append(data.get("error", ""))
                return None
            cookies = {"token":  data.get("token", "")}

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

    if data is None:
        return [-1, "Deployment Failed"]

    if data.get("success", False):
        return [data.get("deploymentid", -1), ""]

    return [-1, data.get("error", "")]


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

    if data is None:
        return [-1, "Deployment Failed"]

    if data.get("success", False):
        return [data.get("deploymentid", -1), ""]

    return [-1, data.get("error", "")]


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

    fromid = ""
    # Get from domainid
    data = get_json(dhurl + "/dmadminweb/API/domain/" + urllib.parse.quote(from_domain), cookies)
    if data is not None:
        if data.get("result", None) is not None:
            result = data.get("result", {})
            if result.get("id", None) is not None:
                fromid = str(result.get("id", ""))

    # Get from Tasks
    data = get_json(dhurl + "/dmadminweb/GetTasks?domainid=" + fromid, cookies)
    taskid = "0"

    if data is not None:
        for atask in data:
            if atask.get("name", "") == task:
                if atask.get("id", None) is not None:
                    taskid = str(atask.get("id", ""))
    # Move App Version
    data = get_json(dhurl + "/dmadminweb/RunTask?f=run&tid=" + taskid + "&notes=&id=" + appid + "&pid=" + fromid, cookies)

    if data is None:
        return [-1, "Move Failed"]

    if data.get("success", False):
        return [appid, "Move Successful"]

    return [-1, data.get("error", "")]


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

    if data is None:
        return [-1, "Approval Failed"]

    if data.get("success", False):
        return [appid, "Approval Successful"]

    return [-1, data.get("error", "")]


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

    if data is None:
        return [False, {"msg": "Could not get log #" + str(deployment_id)}]

    if data.get("text"):
        return [False, {"msg": "Could not get log #" + str(deployment_id)}]

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

    while done == 0:
        res = is_deployment_done(dhurl, cookies, deployid)

        if res is not None:
            if res[0]:
                data = res[1]
                if data.get("success", False) and data.get("iscomplete", False):
                    done = 1
            else:
                done = 1

        time.sleep(10)

    data = get_json(dhurl + "/dmadminweb/API/log/" + str(deployid), cookies)

    if data is None or not data:
        return [False, "Could not get log #" + str(deployid)]

    lines = data.get("logoutput", "")
    exitcode = data.get("exitcode", 1)
    output = ""

    for line in lines:
        output = output + line + "\n"

    if exitcode == 0:
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
    envid = "-1"
    appid = "-1"
    srvid = "-1"
    compid = "-1"
    servers = []
    env_attrs = []
    srv_attrs = []
    app_attrs = []
    comp_attrs = []

    data = get_json(dhurl + "/dmadminweb/API/environment/" + urllib.parse.quote(env), cookies)
    if data is not None:
        if data.get("result", None) is not None:
            result = data.get("result", {})
            if result.get("id", None) is not None:
                envid = str(result.get("id", ""))
            if result.get("servers", None) is not None:
                servers = result.get("servers", [])

    data = get_json(dhurl + "/dmadminweb/API/getvar/environment/" + envid, cookies)

    if data is not None:
        env_attrs = data.get("attributes", [])
    for a_srv in servers:
        if srv == a_srv["name"]:
            srvid = str(a_srv["id"])
            data = get_json(dhurl + "/dmadminweb/API/getvar/server/" + srvid, cookies)
            if data is not None:
                srv_attrs = data.get("attributes", [])
            break

    data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(app), cookies)

    if data is not None:
        result = data.get("result", {})

        if app == result.get("name", ""):
            appid = str(result.get("id", ""))
        else:
            versions = result.get("versions", [])
            for a_ver in versions:
                if app == a_ver.get("name", ""):
                    appid = str(a_ver.get("id", ""))
                    break

    data = get_json(dhurl + "/dmadminweb/API/getvar/application/" + appid, cookies)
    if data is not None:
        app_attrs = data.get("attributes", [])

    data = get_json(dhurl + "/dmadminweb/API/component/" + comp, cookies)
    if data is not None:
        result = data.get("result", {})
        compid = str(result.get("id", ""))

    data = get_json(dhurl + "/dmadminweb/API/getvar/component/" + compid, cookies)
    if data is not None:
        comp_attrs = data.get("attributes", [])

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
    if data is None:
        return {}

    app_attrs = data.get("attributes", {})
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

    if data is None:
        return None

    for dom in data:
        if dom.get("name", None) is not None:
            name = dom.get("name", "")
            child = name.split(".")[-1]
            if child == findname:
                return dom
            else:
                child = child.replace(" ", "").lower()
                if child == findname:
                    dom["name"] = "GLOBAL.Chasing Horses LLC." + name
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
    if name is None:
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

    if (compvariant == "" or compvariant is None) and compversion is not None and compversion != "":
        compvariant = compversion
        compversion = None

    component = ""

    if compvariant is not None and compvariant != "" and compversion is not None and compversion != "":
        component = compname + ";" + compvariant + ";" + compversion
    elif compvariant is not None and compvariant != "":
        component = compname + ";" + compvariant
    else:
        component = compname

    check_compname = ""
    short_compname = ""

    if "." in compname:
        short_compname = compname.split(".")[-1]

    if compvariant is not None and compvariant != "" and compversion is not None and compversion != "":
        check_compname = short_compname + ";" + compvariant + ";" + compversion
    elif compvariant is not None and compvariant != "":
        check_compname = short_compname + ";" + compvariant
    else:
        check_compname = short_compname

    param = ""
    if id_only:
        param = "&idonly=Y"

    if latest:
        param = param + "&latest=Y"

    data = get_json(dhurl + "/dmadminweb/API/component/?name=" + urllib.parse.quote(component) + param, cookies)

    if data is None:
        return [-1, ""]

    if data["success"]:
        compid = data["result"]["id"]
        name = data["result"]["name"]

        if name != check_compname and "versions" in data["result"]:
            vers = data["result"]["versions"]
            for ver in vers:
                if ver["name"] == check_compname:
                    compid = ver["id"]
                    name = ver["name"]
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

    if data is None:
        return [-1, ""]

    if data["success"]:
        envid = data["result"]["id"]
        name = data["result"]["name"]

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

    if data is None:
        return name

    if data["success"]:
        name = data["result"]["domain"] + "." + data["result"]["name"]
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


def get_previous_commit(dhurl, cookies, compname, compvariant):
    """
    Get the git commit associated with the previous component
    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        compname (int): name of the component

    Returns:
        string: string of the commit
    """
    data = get_component(dhurl, cookies, compname, compvariant, "", True, True)
    parent_compid = data[0]
    if parent_compid > 0:
        data = get_component_fromid(dhurl, cookies, parent_compid)
        if data is not None:
            if data.get("result", None) is not None:
                return data["result"].get("gitcommit", "")
    return ""


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

    if data is None:
        return []

    if "attributes" in data:
        return data["attributes"]

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

    if data is None:
        return name

    if data["success"]:
        name = data["result"]["domain"] + "." + data["result"]["name"]
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

    if (compvariant == "" or compvariant is None) and compversion is not None and compversion != "":
        compvariant = compversion
        compversion = None

    domain = ""

    compname = compname.rstrip(";")
    compvariant = compvariant.rstrip(";")
    if compversion is not None:
        compversion = compversion.rstrip(";")

    if "." in compname:
        parts = compname.split(".")
        if parts:
            parts.pop()
        domain = ".".join(parts) + "."

    # Get latest version of compnent variant
    data = get_component(dhurl, cookies, compname, compvariant, compversion, False, True)
    if data[0] == -1:
        data = get_component(dhurl, cookies, compname, compvariant, None, False, True)
        if data[0] == -1:
            data = get_component(dhurl, cookies, compname, "", None, False, True)

    latest_compid = data[0]
    found_compname = data[1]
    check_compname = ""
    compid = latest_compid

    short_compname = ""

    if "." in compname:
        short_compname = compname.split(".")[-1]

    if compvariant is not None and compvariant != "" and compversion is not None and compversion != "":
        check_compname = short_compname + ";" + compvariant + ";" + compversion
    elif compvariant is not None and compvariant != "":
        check_compname = short_compname + ";" + compvariant
    else:
        check_compname = short_compname

    # Create base component variant
    # if one is not found
    # Get the new compid of the new component variant
    if compvariant is None:
        compvariant = ""

    if compversion is None:
        compversion = ""

    if latest_compid < 0:
        if kind.lower() == "docker":
            compid = new_docker_component(dhurl, cookies, compname, compvariant, compversion, -1)
        else:
            compid = new_file_component(dhurl, cookies, compname, compvariant, compversion, -1, None)
    else:
        # Create component items for the component
        if compautoinc is None:
            if found_compname == "" or found_compname != check_compname:
                if kind.lower() == "docker":
                    compid = new_docker_component(dhurl, cookies, compname, compvariant, compversion, compid)
                else:
                    compid = new_file_component(dhurl, cookies, compname, compvariant, compversion, compid, component_items)
            elif compid > 0:
                if kind.lower() == "docker":
                    new_component_item(dhurl, cookies, compid, "docker", None)
                else:
                    new_component_item(dhurl, cookies, compid, "file", component_items)
        else:
            parts = found_compname.split(";")
            if len(parts) >= 3:  # hipster-store;master;v1_3_334-gabc635
                latest_compversion = parts[2]
            elif len(parts) == 2:
                latest_compversion = parts[1]
            else:
                latest_compversion = ""

            verschema = ""
            gitcommit = ""

            if "-g" in latest_compversion:  # git commit
                verschema = latest_compversion.split("-g")[0]
                gitcommit = latest_compversion.split("-g")[1]
            elif "_g" in latest_compversion:  # git commit
                verschema = latest_compversion.split("_g")[0]
                gitcommit = latest_compversion.split("_g")[1]
            else:
                verschema = latest_compversion
                gitcommit = ""

            compid = latest_compid

            if compvariant == verschema:
                verschema = ""

            # inc schemantic version & loop until we don't have an exisiting version
            while compid >= 0:
                if "_" in verschema:
                    schema_parts = verschema.split("_")
                    incnum = schema_parts.pop()
                    incnum = str(int(incnum) + 1)
                    schema_parts += [incnum]
                    verschema = "_".join(schema_parts) + gitcommit
                elif verschema.isdigit():
                    verschema = str(int(verschema) + 1) + gitcommit
                else:
                    verschema = "1" + gitcommit

                compversion = verschema

                data = get_component(dhurl, cookies, domain + compname, compvariant, compversion, True, False)
                compid = data[0]

            if kind.lower() == "docker":
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

    if (compvariant is None or compvariant == "") and compversion is not None and compversion != "":
        compvariant = compversion
        compversion = None

    compid = 0
    # Create base version
    if parent_compid < 0:
        if is_empty(compvariant):
            data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname), cookies)
        else:
            data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        if data is not None:
            result = data.get("result", {})
            compid = int(result.get("id", "0"))
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        if data is not None:
            if data is not None:
                result = data.get("result", {})
                compid = int(result.get("id", "0"))

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

    if (compvariant is None or compvariant == "") and compversion is not None and compversion != "":
        compvariant = compversion
        compversion = None

    compid = 0

    # Create base version
    if parent_compid < 0:
        if is_empty(compvariant):
            data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname), cookies)
        else:
            data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        if data is not None:
            if data is not None:
                result = data.get("result", {})
                compid = int(result.get("id", "0"))
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        if data is not None:
            if data is not None:
                result = data.get("result", {})
                compid = int(result.get("id", "0"))
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
    data = None
    # Get compId
    if kind.lower() == "docker" or component_items is None:
        data = get_json(dhurl + "/dmadminweb/UpdateAttrs?f=inv&c=" + str(compid) + "&xpos=100&ypos=100&kind=" + kind + "&removeall=Y", cookies)
    else:
        ypos = 100

        i = 0
        parent_item = -1

        for item in component_items:
            tmpstr = ""
            ciname = ""
            for entry in item:
                if entry["key"].lower() == "name":
                    ciname = entry["value"]
                else:
                    tmpstr = tmpstr + "&" + urllib.parse.quote(entry["key"]) + "=" + urllib.parse.quote(entry["value"])

            if i == 0:
                tmpstr = tmpstr + "&removeall=Y"

            data = get_json(dhurl + "/dmadminweb/API/new/compitem/" + urllib.parse.quote(ciname) + "?component=" + str(compid) + "&xpos=100&ypos=" + str(ypos) + "&kind=" + kind + tmpstr, cookies)

            if data is not None:
                if data.get("result", None) is not None:
                    result = data.get("result", {})
                    workid = result.get("id", -1)
                    if parent_item > 0:
                        get_json(dhurl + "/dmadminweb/UpdateAttrs?f=iad&c=" + str(compid) + "&fn=" + str(parent_item) + "&tn=" + str(workid), cookies)
                    parent_item = workid

            ypos = ypos + 100
            i = i + 1
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

    if (compvariant is None or compvariant == "") and compversion is not None and compversion != "":
        compvariant = compversion
        compversion = None

    if "." in compname:
        compname = compname.split(".")[-1]

    if compvariant is not None and compvariant != "" and compversion is not None and compversion != "":
        data = get_json(dhurl + "/dmadminweb/UpdateSummaryData?objtype=23&id=" + str(compid) + "&change_1=" + urllib.parse.quote(compname + ";" + compvariant + ";" + compversion), cookies)
    elif compvariant is not None and compvariant != "":
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
    compid = -1

    # Create base version
    if parent_compid is None:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/?name=" + urllib.parse.quote(compname + ";" + compvariant), cookies)
        if data is not None:
            if data is not None:
                result = data.get("result", {})
                compid = int(result.get("id", -1))
    else:
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + str(parent_compid), cookies)
        if data is not None:
            if data is not None:
                result = data.get("result", {})
                compid = int(result.get("id", -1))
    update_name(dhurl, cookies, compname, compvariant, compversion, compid)

    if kind is not None:
        new_component_item(dhurl, cookies, compid, kind, None)

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

    if compid < 0:
        return

    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid), payload, cookies)
    if data is None:
        return [False, "Could not update attributes on '" + compname + "'"]

    if is_not_empty(crdatasource):
        get_json(dhurl + "/dmadminweb/API2/assign/defect/cv" + str(compid) + "?del=y", cookies)

        allcrs = ",".join(crlist)
        crlist = allcrs.split(",")

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
    if data is not None and data.get("error", None) is not None:
        return [False, "Could not update attributes on '" + str(compid) + "' " + data.get("error", "")]

    if is_not_empty(crdatasource):
        for bugid in crlist:
            get_json(dhurl + "/dmadminweb/API2/assign/defect/" + str(compid) + "?ds=" + crdatasource + "&bugid=" + str(bugid), cookies)

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
    if not data:
        return [False, "Could not update attributes on '" + str(envid) + "'"]
    return [True, data, dhurl + "/dmadminweb/API/setvar/environment/" + str(envid)]


def is_compassigned2app(dhurl, cookies, appid, compid):
    """
    Check to see if the component is already assigned to the application version.

    Args:
        dhurl (string): url to the server
        cookies (string): cookies from login
        appid (int): id of the application
        compid (int): id of the component

    Returns:
        boolean: True if the component is assigned to the application version.
    """

    data = get_json(dhurl + "/dmadminweb/API/compassigned2app/" + str(appid) + "/" + str(compid), cookies)

    if data is None:
        return False

    return data.get("result", False)


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
    name = ""
    appid = -1

    param = ""
    if id_only:
        param = "&idonly=Y"

    if appversion.lower() == "latest":
        param = param + "&latest=Y"
        appversion = ""

    if appversion is not None and appversion != "":
        application = appname + ";" + appversion
    else:
        application = appname

    data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(application) + param, cookies)

    if data is None:
        return [-1, "", -1]

    if data.get("success", False):
        vlist = []
        result = data.get("result", None)
        if result:
            appid = result.get("id", -1)
            name = result.get("name", "")
            vlist = result.get("versions", None)
            latest = -1

        if vlist:
            latest = vlist[-1]["id"]
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
    appid = -1
    name = ""
    appversion = clean_name(appversion)
    param = ""

    if appversion.lower() == "latest":
        param = "?latest=Y"
        appversion = ""

    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid) + param, cookies)

    if data is None:
        return [-1, "", -1]
    if data.get("success", False):
        vlist = []
        result = data.get("result", None)
        if result:
            appid = result.get("id", -1)
            name = result.get("name", "")
            vlist = result.get("versions", None)
            latest = -1

        if vlist:
            latest = vlist[-1]["id"]
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

    if data is None:
        return [-1, "", -1]

    result = data.get("result", None)

    if result is None:
        return [-1, "", -1]

    return result["id"]


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

    if data is None:
        return -1

    return data.get("id", -1)


def new_application(dhurl, cookies, appname, appversion, appautoinc, envs, compid):
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
    parts = []

    if is_empty(appversion) and ";" in appname:
        parts = appname.split(";")
        appversion = parts.pop()
        appname = ";".join(parts)

    full_appname = appname

    if "." in appname:
        parts = appname.split(".")
        if parts:
            parts.pop()
        domain = ".".join(parts)
        domain = "domain=" + urllib.parse.quote(domain)
        appname = appname.split(".")[-1]

    # Get Base Version
    data = get_application(dhurl, cookies, full_appname, "", True)
    parent_appid = data[0]

    # Create base version
    if parent_appid < 0:
        data = get_json(dhurl + "/dmadminweb/API/new/application/?name=" + urllib.parse.quote(appname) + "&" + domain, cookies)
        if data is not None:
            if data.get("success", False):
                data = get_application(dhurl, cookies, appname, "", True)
            parent_appid = data[0]

        if envs is not None:
            for env in envs:
                data = get_json(dhurl + "/dmadminweb/API/assign/application/?name=" + urllib.parse.quote(full_appname) + "&env=" + urllib.parse.quote(env), cookies)

    # Refetch parent to get version list

    data = get_application(dhurl, cookies, full_appname, "latest", False)
    latest_appid = data[0]
    latest_name = data[1]

    # Refetch the current app version to see if we need to create it or not
    data = get_application(dhurl, cookies, full_appname, appversion, True)
    appid = data[0]

    # inc schemantic version & loop until we don't have an exisiting version
    while appautoinc is not None and appid >= 0:
        ver = appversion
        if "_" in ver:
            schema_parts = ver.split("_")
            incnum = schema_parts.pop()
            incnum = str(int(incnum) + 1)
            schema_parts.append(incnum)
            ver = "_".join(schema_parts)
        elif ver.isdigit():
            ver = str(int(ver) + 1)
        else:
            ver = "1"

        appversion = ver

        data = get_application(dhurl, cookies, full_appname, appversion, True)
        appid = data[0]

    compassigned2app = is_compassigned2app(dhurl, cookies, latest_appid, compid)

    if compassigned2app:
        return [latest_appid, ".".join(parts) + "." + latest_name]

    if appid < 0:
        data = get_json(dhurl + "/dmadminweb/API/newappver/" + str(latest_appid) + "/?name=" + urllib.parse.quote(appname + ";" + appversion) + "&" + domain, cookies)

        if data is not None:
            if not data.get("success", False):
                return [-1, data.get("error", "")]

            if data.get("result", None) is not None:
                result = data.get("result", {})
                if result.get("id", None) is not None:
                    appid = result.get("id", "")
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

    if data is None:
        return [-1, "", -1]

    if data.get("success", False):
        result = data.get("result", None)
        if result:
            complist = result.get("components", [])
            lastcompid = result.get("lastcompver", -1)

            for comp in complist:
                app_basecompid = get_base_component(dhurl, cookies, comp["id"], True)
                if app_basecompid == basecompid:
                    replace_compid = comp["id"]

                if comp["id"] == lastcompid:
                    xpos = comp["xpos"]
                    ypos = comp["ypos"] + 100

    if replace_compid >= 0:
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
    if "." in appname:
        parts = appname.split(".")
        if parts:
            parts.pop()
        domain = ".".join(parts)
        domain = "domain=" + urllib.parse.quote(domain)
        appname = appname.split(".")[-1]
    if envs is not None:
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

    lines = run_cmd("git clone -q git@github.com:" + project + ".git .").split("\n")
    for line in lines:
        print(line)

    data = None
    if not os.path.exists("features.toml"):
        print("features.toml not found")
        return data

    with open("features.toml", mode="r", encoding="utf-8") as fin:
        tmpstr = fin.read()
        data = qtoml.loads(tmpstr)
    return data


def import_cluster(dhurl, cookies, domain, appname, appversion, appautoinc, deployenv, crdatasource, crlist, cluster_json, msname, msbranch):  # pylint: disable=too-complex # noqa: C901
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
    envs = []
    newvals = {}
    complist = []

    if appversion is None:
        appversion = ""

    if os.path.exists(cluster_json):
        stream = open(cluster_json, mode="r", encoding="utf-8")
        values = json.load(stream)
        newvals.update(values)
        stream.close()

        items = newvals["items"]
        branch_containers = []
        master_containers = {}
        deployed_ms = {}
        tag = ""
        repo = ""

        for item in items:
            deploy_time = item["metadata"]["creationTimestamp"]
            labels = item["metadata"]["labels"]
            branch = labels.get("git/branch", "main")
            msversion = labels.get("app.kubernetes.io/version", "")
            # msdigest = labels.get("app.kubernetes.io/digest", "")
            compid = -1

            containers = item["spec"]["template"]["spec"]["containers"]
            for container in containers:
                full_msname = container["name"]
                image = container["image"]
                repo = image.split(":")[0]
                tag = image.split(":")[1]
                short_msname = repo.split("/")[-1]
                compname = domain + "." + short_msname
                compvariant = branch
                compversion = tag

                if full_msname == msname:
                    deployed_ms = {
                        "compid": compid,
                        "compname": compname,
                        "compvariant": compvariant,
                        "compversion": compversion,
                        "full_msname": full_msname,
                        "msname": short_msname,
                        "branch": branch,
                        "repo": repo,
                        "tag": tag,
                        "deploy_time": deploy_time,
                    }

                if branch in ("master", "main"):
                    if not msversion.startswith("1.") and msversion != "1":
                        continue

                    latest_container = master_containers.get(short_msname, None)
                    if latest_container is None:
                        master_containers[short_msname] = {
                            "compid": compid,
                            "compname": compname,
                            "compvariant": compvariant,
                            "compversion": compversion,
                            "full_msname": full_msname,
                            "msname": short_msname,
                            "branch": branch,
                            "repo": repo,
                            "tag": tag,
                            "deploy_time": deploy_time,
                        }
                    elif latest_container["deploy_time"] <= deploy_time:
                        master_containers[short_msname] = {
                            "compid": compid,
                            "compname": compname,
                            "compvariant": compvariant,
                            "compversion": compversion,
                            "full_msname": full_msname,
                            "msname": short_msname,
                            "branch": branch,
                            "repo": repo,
                            "tag": tag,
                            "deploy_time": deploy_time,
                        }
                elif msbranch is not None and branch == msbranch:
                    branch_containers.append(
                        {
                            "compid": compid,
                            "compname": compname,
                            "compvariant": compvariant,
                            "compversion": compversion,
                            "full_msname": full_msname,
                            "msname": short_msname,
                            "branch": branch,
                            "repo": repo,
                            "tag": tag,
                            "deploy_time": deploy_time,
                        }
                    )

        if msbranch is not None:
            complist = []
            if len(deployed_ms) == 0:
                deployed_ms = {"compid": -1, "msname": "", "tag": "", "branch": ""}
            else:
                complist.append(deployed_ms)

            for container in master_containers.values():
                if deployed_ms["msname"] != container["msname"]:
                    complist.append(container)
                elif deployed_ms["branch"] == container["branch"] and msbranch not in ("master", "main"):
                    complist.append(container)

        compid_list = []
        for item in complist:
            data = get_component(dhurl, cookies, item["compname"], item["compvariant"], item["compversion"], True, False)
            compid = -1
            if data is not None:
                compid = data[0]
            if compid == -1:
                print("Adding missing component: " + item["compname"] + ";" + item["compvariant"] + ";" + item["compversion"])
                compid = new_docker_component(dhurl, cookies, item["compname"], item["compvariant"], item["compversion"], -1)
                if compid > 0:
                    update_compid_attrs(dhurl, cookies, compid, {"DockerTag": tag, "DockerRepo": repo}, crdatasource, crlist)
            else:
                print(item["compname"] + ";" + item["compvariant"] + ";" + item["compversion"])
            compid_list.append(
                {
                    "compid": compid,
                    "name": item["compname"] + ";" + item["compvariant"] + ";" + item["compversion"],
                }
            )

        if len(compid_list) > 0:
            app = appname
            if appversion is not None and is_not_empty(appversion):
                app = appname + ";" + appversion
            data = get_json(dhurl + "/dmadminweb/API/application/?name=" + urllib.parse.quote(app) + "&latest=Y", cookies)
            appid = -1
            if data is not None and data.get("success", False):
                appid = data["result"]["id"]

            existing_ids = []

            if appid > 0:
                existing_comps = []
                data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid), cookies)
                if data is not None:
                    result = data.get("result", {})
                    existing_comps = result.get("components", [])

                for comp in existing_comps:
                    existing_ids.append(comp["id"])

            new_ids = []
            for item in compid_list:
                new_ids.append(item["compid"])

            if are_equal(existing_ids, new_ids):
                print("Application Version " + appname + ";" + appversion + " already exists")
            else:
                data = new_application(dhurl, cookies, appname, appversion, appautoinc, envs, -1)
                if data is not None:
                    appid = data[0]

                for compid in existing_ids:
                    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acd&a=" + str(appid) + "&c=" + str(compid), cookies)

                for item in compid_list:
                    compid = item["compid"]
                    name = item["name"]
                    print("Assigning Component Version " + name + " to Application Version " + appname + ";" + appversion)
                    add_compver_to_appver(dhurl, cookies, appid, compid)

            # create env and deploy to env
            deploydata = "deploy.json"
            deploy = {}
            deploy["application"] = appid
            deploy["environment"] = deployenv
            deploy["rc"] = 0
            with open(deploydata, mode="w", encoding="utf-8") as deployfp:
                json.dump(deploy, deployfp)
            deployfp.close()
            log_deploy_application(dhurl, cookies, deploydata)
    return


def are_equal(arr1, arr2):
    arr1_len = len(arr1)
    arr2_len = len(arr2)

    # If lengths of array are not
    # equal means array are not equal
    if arr1_len != arr2_len:
        return False

    # Sort both arrays
    arr1.sort()
    arr2.sort()

    # Linearly compare elements
    for i in range(arr1_len):
        if arr1[i] != arr2[i]:
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
    with open(deploydata, mode="r", encoding="utf-8") as fin_data:
        payload = fin_data.read()

    data = {}
    if is_not_empty(payload):
        data = json.loads(payload)

        compversion = data.get("compversion", None)
        environment = data.get("environment", "")
        application = data.get("application", "")

        if data.get("skipdeploy", None) is None:
            data["skipdeploy"] = "N"

        payload = json.dumps(data)

        if is_not_empty(application) and is_not_empty(environment):
            result = post_json(url, payload, cookies)
            if result is not None:
                data["deployid"] = result.get("deployid", -1)
                data["application"] = result.get("application", application)
                data["appid"] = result.get("appid", -1)
                application = data["application"]

                if result.get("errormsg", None) is not None:
                    print(result.get("errormsg", None))

            print(f"Recorded deployment of {application} for {environment}")

            if compversion is not None and len(compversion) > 0:
                print("Assigned components to " + application + ":")
                print("  " + "\n  ".join(compversion))
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
    if is_empty(compvariant):
        compvariant = ""

    if is_empty(compvariant) and "-v" in compversion:
        compvariant = compversion.split("-v")[0]
        compversion = "v" + compversion.split("-v")[1]

    if is_empty(compvariant) and "-V" in compversion:
        compvariant = compversion.split("-V")[0]
        compversion = "v" + compversion.split("-V")[1]

    cwd = ""
    tempdir = ""

    if "git@" in kvconfig:
        print("### Grabbing Config from Git ###")

        if "#" in kvconfig:
            gitbranch = kvconfig.split("#")[1]
            kvconfig = kvconfig.split("#")[0]
        else:
            gitbranch = "master"

        repo = "/".join(kvconfig.split("/")[:2])
        kvconfig = "/".join(kvconfig.split("/")[1:])
        gitdir = kvconfig.split("/", maxsplit=1)[0]
        kvconfig = "/".join(kvconfig.split("/")[1:])

        cwd = os.getcwd()
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)
        print(tempdir)

        lines = run_cmd("git clone -q " + repo).split("\n")
        for line in lines:
            print(line)

        os.chdir(gitdir)
        lines = run_cmd("git checkout " + gitbranch).split("\n")
        for line in lines:
            print(line)

    normal_dict = {}
    for file_path in Path(kvconfig).glob("**/*.properties"):
        filename = fspath(file_path)

        try:
            print(filename)
            config = ConfigObj(filename, encoding="iso-8859-1")
            work_dict = config.dict()
            temp_dict = normal_dict | work_dict
            normal_dict = temp_dict
        except configobj.ConfigObjError as error:
            print(error)

    for file_path in Path(kvconfig).glob("**/*.json"):
        filename = fspath(file_path)

        print(filename)
        with open(filename, mode="r", encoding="utf-8") as fp_json:
            data = json.load(fp_json)
            temp_dict = normal_dict | data
            normal_dict = temp_dict

    flat_dict = flatten(normal_dict, reducer="path")

    if is_not_empty(tempdir) and is_not_empty(cwd):
        os.chdir(cwd)
    #    rmtree(tempdir)

    attrs = {}
    for key, value in flat_dict.items():
        if isinstance(value, list):
            value = " ".join(value)

        attrs[key] = value

    print("")

    # create component version
    print("Getting Latest Component")
    data = get_component(dhurl, cookies, compname, compvariant, compversion, False, True)
    latest_compid = data[0]

    if latest_compid < 0:
        data = get_component(dhurl, cookies, compname, "", "", False, True)
        latest_compid = data[0]

    if latest_compid > 0:
        comp_attrs = get_component_attrs(dhurl, cookies, latest_compid)

        old_attrs = {}
        for attr in comp_attrs:
            key = list(attr.keys())[0]
            value = attr[key]
            old_attrs[key] = value

        all_attrs = old_attrs | attrs

        print("Updating Component Attributes\n")

        data = update_compid_attrs(dhurl, cookies, latest_compid, all_attrs, crdatasource, crlist)

    print("Attribute Update Done")
    return


def post_textfile(dhurl, cookies, compid, filename, file_type):
    file_data = bytes()
    if os.path.exists(filename):
        file_data = open(filename, "rb").read()
    else:
        try:
            res = requests.get(filename, timeout=300)
            if res.status_code == 200:
                file_data = res.content
        except requests.exceptions.ConnectionError:
            print("WARNING: " + filename + " not found")

    if is_empty(file_data):
        return

    encoded_bytes = base64.encodebytes(file_data)

    file = []
    line_no = 1
    for line in encoded_bytes.splitlines():
        d = line.decode("utf-8")
        line_no += 1
        file.append(d)

    payload = {"compid": compid, "filetype": file_type, "file": file}
    result = post_json(dhurl + "/msapi/textfile", json.dumps(payload), cookies)

    if result is None:
        return {"message": "Could not persist '" + filename + "' with compid: '" + str(compid) + "'"}
    return result


def update_deppkgs(dhurl, cookies, compid, filename, glic):

    result = None
    sbomtype = None
    data = get_json(dhurl + "/msapi/sbomtype", cookies)

    if data is not None:
        sbomtype = data.get("SBOMType", None)

    payload = ""

    parts = filename.split("@")
    filetype = parts[0].lower()
    filename = parts[1]

    with open(filename, mode="r", encoding="utf-8") as fin_data:
        data = json.load(fin_data)

        if sbomtype is not None and sbomtype == "fullfile":
            postdata = {}
            postdata["_key"] = str(compid)
            postdata["content"] = data
            json_data = json.dumps(postdata, indent=4)
            print(json_data)
            result = post_json(dhurl + "/msapi/package", json.dumps(postdata), cookies)
        else:
            if glic is not None:
                glic_hash = {}

                for lic in glic.get("dependencies", []):
                    if lic.get("moduleLicense", None) is not None:
                        glic_hash["pkg:maven/" + lic["moduleName"].replace(":", "/") + "@" + lic["moduleVersion"]] = lic.get("moduleLicense", "")

                newdata = []
                for sbom_pkg in data.get("components"):
                    if glic_hash.get(sbom_pkg["purl"], None) is not None:
                        sbom_pkg["licenses"] = [{"license": {"name": glic_hash.get(sbom_pkg["purl"], None)}}]

                    newdata.append(sbom_pkg)

                data["components"] = newdata

            payload = json.dumps(data)

            result = post_json(dhurl + "/msapi/deppkg/" + filetype + "?compid=" + str(compid), payload, cookies)

    if result is None:
        return {"message": "Could not persist '" + filename + "' with compid: '" + str(compid) + "'"}
    return result


def run_cmd(cmd):
    retval = ""

    if "git" in cmd and not os.path.exists(".git"):
        return retval

    pid = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)  # nosec B602
    retval = ""
    if pid.stdout is not None:
        for line in io.TextIOWrapper(pid.stdout, encoding="utf-8"):
            retval += line.rstrip()

    return retval
