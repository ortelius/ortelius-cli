"""This module interfaces with the DeployHub RestAPIs to perform login, deploy, move and approvals."""

import os
import re
import subprocess
import tempfile
import time
import urllib
from pathlib import Path
from pprint import pprint

import json
import qtoml
import requests
import yaml
import configobj
from configobj import ConfigObj
from flatten_dict import flatten

def fspath(path):
    '''https://www.python.org/dev/peps/pep-0519/#os'''
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
    """ Get URL as json string.
        Returns: json string"""

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
    """ Post URL as json string.
        Returns: json string"""

    try:
        res = requests.post(url, data=payload, cookies=cookies)
        if (res is None):
            return None
        if (res.status_code != 200):
            return None
        return res.json()
    except requests.exceptions.ConnectionError as conn_error:
        print(str(conn_error))
    return None

def is_empty(my_string):
    """Is the string empty"""
    return not (my_string and my_string.strip())


def is_not_empty(my_string):
    """Is the string NOT empty"""
    return bool(my_string and my_string.strip())


def login(dhurl, user, password, errors):
    """Login to DeployHub using the DH Url, userid and password.
    Returns: cookies to be used in subsequent API calls"""

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


def deploy_application(dhurl, cookies, appname, appversion, env):
    """Deploy the application to the environment
    Returns: deployment_id"""
    data = get_application(dhurl, cookies, appname, appversion, True)
    appid = data[0]

    data = get_json(dhurl + "/dmadminweb/API/deploy?app=" + str(appid) + "&env=" + urllib.parse.quote(env) + "&wait=N", cookies)

    if (data is None):
        return [-1, "Deployment Failed"]

    if (data.get('success', False)):
        return [data.get('deploymentid', -1), ""]

    return [-1, data.get('error', "")]


def move_application(dhurl, cookies, appname, appversion, from_domain, task):
    """Move an application from the from_domain using the task"""
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
    """Approve the application for the current domain that it is in."""
    data = get_application(dhurl, cookies, appname, appversion, True)
    appid = data[0]

    data = get_json(dhurl + "/dmadminweb/API/approve/" + appid, cookies)

    if (data is None):
        return [-1, "Approval Failed"]

    if (data.get('success', False)):
        return [appid, "Approval Successful"]

    return [-1, data.get('error', "")]


def is_deployment_done(dhurl, cookies, deployment_id):
    """Check to see if the deployment has completed"""
    data = get_json(dhurl + "/dmadminweb/API/log/" + str(deployment_id) + "?checkcomplete=Y", cookies)

    if (data is None):
        return [False, {'msg': "Could not get log #" + str(deployment_id)}]

    if (data.get('text')):
        return [False, {'msg': "Could not get log #" + str(deployment_id)}]

    return [True, data]


def get_logs(dhurl, cookies, deployid):
    """Get the logs for the deployment.
    Returns: array successful as boolean, log as a String"""
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
    """Get the attributes for this deployment base on app version and env.
    Returns: json of attributes"""

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


def find_domain(dhurl, cookies, findname):
    """Get the domain name and id that matches best with the passed in name"""

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
    if (name is None):
        return name

    name = name.replace(".", "_")
    name = name.replace("-", "_")
    return name


def get_component(dhurl, cookies, compname, compvariant, compversion, id_only, latest):
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


def get_component_name(dhurl, cookies, compid):
    name = ""
    data = get_json(dhurl + "/dmadminweb/API/component/" + str(compid) + "?idonly=Y", cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['name']
    return name

def get_component_attrs(dhurl, cookies, compid):

    data = get_json(dhurl + "/dmadminweb/API/getvar/component/" + str(compid), cookies)

    if (data is None):
        return []

    if ('attributes' in data):
        return data['attributes']

    return []

def get_application_name(dhurl, cookies, appid, id_only):
    name = ""

    param = ""
    if (id_only):
        param = "?idonly=Y"

    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid) + param, cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['name']
    return name


def new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, component_items, compautoinc):
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
    """Create the component object based on the component name and variant.
    Returns: component id of the new component otherwise None"""

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


def update_component_attrs(dhurl, cookies, compname, compvariant, compversion, attrs):
    # Get latest version of compnent variant
    data = get_component(dhurl, cookies, compname, compvariant, compversion, True, False)
    compid = data[0]

    if (compid < 0):
        return

    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid), payload, cookies)
    if (not data):
        return [False, "Could not update attributes on '" + compname + "'"]
    return [True, data, dhurl + "/dmadminweb/API/setvar/component/" + str(compid)]

def update_compid_attrs(dhurl, cookies, compid, attrs):

    payload = json.dumps(attrs)

    data = post_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid), payload, cookies)
    if (not data):
        return [False, "Could not update attributes on '" + str(compid) + "'"]
    return [True, data, dhurl + "/dmadminweb/API/setvar/component/" + str(compid)]


def get_application(dhurl, cookies, appname, appversion, id_only):
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


def get_base_component(dhurl, cookies, compid, id_only):

    data = get_json(dhurl + "/dmadminweb/API/basecomponent/" + str(compid), cookies)

    if (data is None):
        return [-1, "", -1]

    result = data.get('result', None)

    if (result is None):
        return [-1, "", -1]

    return result['id']


def new_application(dhurl, cookies, appname, appversion, appautoinc, envs):
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
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acd&a=" + str(appid) + "&c=" + str(compid), cookies)
  #  print(dhurl + "/dmadminweb/UpdateAttrs?f=acvm&a=" + str(appid) + "&c=" + str(compid) + "&xpos=" + str(xpos) + "&ypos=" + str(ypos))
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acvm&a=" + str(appid) + "&c=" + str(compid) + "&xpos=" + str(xpos) + "&ypos=" + str(ypos), cookies)
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=cal&a=" + str(appid) + "&fn=" + str(parent_compid) + "&tn=" + str(compid), cookies)

def assign_app_to_env(dhurl, cookies, appname, envs):
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


def import_cluster(dhurl, cookies, kubeyaml, defaultdomain):
    newvals = {}
    complist = []

    if (os.path.exists(kubeyaml)):
        stream = open(kubeyaml, 'r')
        values = yaml.load(stream)
        newvals.update(values)
        stream.close()

        for item in newvals['items']:
            appname = item['metadata']['namespace']
            if ('default' in appname):
                appname = defaultdomain.split('.')[-1] + ' App'
            compname = item['metadata']['name']
            dom = find_domain(dhurl, cookies, compname)
            if (dom is None):
                compname = defaultdomain + '.' + compname
            else:
                compname = dom['name'] + '.' + compname
            image_tag = item['spec']['template']['spec']['containers'][0]['image']
            if ('@' in image_tag):
                (image, image_sha) = image_tag.split('@')
                image_sha = image_sha.split(':')[-1]
                (image, tag) = image.split(':')
                version = ""
                gitcommit = ""

                if ('-g'in tag):
                    (version, gitcommit) = re.split(r'-g', tag)

                compattr = []
                compattr.append('DockerRepo=' + image)
                compattr.append('DockerSha=' + image_sha)
                compattr.append('GitCommit=' + gitcommit)
                comp = {'project': appname, 'compname': compname, 'compvariant': version, 'compversion': 'g' + gitcommit, 'compattr': compattr}
                complist.append(comp)

    return complist

def log_deploy_application(dhurl, cookies, deploydata):
    url = dhurl + "/dmadminweb/API/deploy"

    payload = ""
    with open(deploydata, "r") as fin_data:
        payload = fin_data.read()

    data = {}
    if (is_not_empty(payload)):
        data = json.loads(payload)

        appname = data.get('appname', '')
        compversion = data.get('compversion', None)
        environment = data.get('environment', '')

        if (is_empty(appname) and compversion is not None):
            print(f'Recording hot fix {compversion} for {environment}')
            url = dhurl + "/dmadminweb/API/deploy"

            payload = {}
            payload['environment'] = environment
            payload['compversion'] = compversion
            payload['rc'] = 0

            post_json(url, json.dumps(payload), cookies)
        else:
            if (data.get('application', None) is not None and data.get('environment', None) is not None):
                post_json(url, payload, cookies)
    return data

def set_kvconfig(dhurl, cookies, kvconfig, appname, appversion, appautoinc, compname, compvariant, compversion, compautoinc, kind):
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
            old_attrs.append(key + "=" + value)

    new_attrs = []
    for key, value in attrs.items():
        key = key.replace("\\", "\\\\")
        value = value.replace("\\", "\\\\")
        new_attrs.append(key + "=" + value)

    diffs = set(new_attrs) ^ set(old_attrs)

    print("Comparing KV: %d Changes" % len(diffs))

    if (len(diffs) > 0):
        pprint(list(diffs))
        compid = new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, None, compautoinc)
        print("Creation Done: " + get_component_name(dhurl, cookies, compid))

        print("Updating Component Attributes\n")

        data = update_compid_attrs(dhurl, cookies, compid, attrs)

        print("Attribute Update Done")

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

            print("Creating Application Version '" + str(appname) + "' '" + appversion + "'")
            data = new_application(dhurl, cookies, appname, appversion, appautoinc, None)
            appid = data[0]
            print("Creation Done: " + get_application_name(dhurl, cookies, appid, True))

            print("Assigning Component Version to Application Version " + str(appid))

            data = add_compver_to_appver(dhurl, cookies, appid, compid)
            print("Assignment Done")
    return

# def update_versions(project, compname, compvariant, compversion):
#    # Clone apprepo
#    data = clone_repo(project)
#    if (data is not None):
#        pprint(data)
