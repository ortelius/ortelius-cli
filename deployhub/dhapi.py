"""This module interfaces with the DeployHub RestAPIs to perform login, deploy, move and approvals."""

import os
import re
import subprocess
import tempfile
import time
import urllib
from pprint import pprint

import qtoml
import requests
import yaml


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
    data = get_application(dhurl, cookies, appname, appversion)
    appid = data[0]

    data = get_json(dhurl + "/dmadminweb/API/deploy?app=" + str(appid) + "&env=" + urllib.parse.quote(env), cookies)

    if (data is None):
        return [-1, "Deployment Failed"]

    if (data.get('success', False)):
        return [data.get('deploymentid', -1), ""]

    return [-1, data.get('error', "")]


def move_application(dhurl, cookies, appname, appversion, from_domain, task):
    """Move an application from the from_domain using the task"""
    data = get_application(dhurl, cookies, appname, appversion)
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
    data = get_application(dhurl, cookies, appname, appversion)
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

    data = get_json(dhurl + "/dmadminweb/API/application/" + app, cookies)

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


def get_component(dhurl, cookies, compname, compvariant, compversion):
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

    data = get_json(dhurl + "/dmadminweb/API/component/" + urllib.parse.quote(component), cookies)

    if (data is None):
        return [-1, ""]

    if (data['success']):
        compid = data['result']['id']
        name = data['result']['name']

        if (name != check_compname):
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
    data = get_json(dhurl + "/dmadminweb/API/component/" + str(compid), cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['name']
    return name


def get_application_name(dhurl, cookies, appid):
    name = ""
    data = get_json(dhurl + "/dmadminweb/API/application/" + str(appid), cookies)

    if (data is None):
        return name

    if (data['success']):
        name = data['result']['name']
    return name


def new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, component_items):
    compvariant = clean_name(compvariant)
    compversion = clean_name(compversion)

    if ((compvariant == "" or compvariant is None) and compversion is not None and compversion != ""):
        compvariant = compversion
        compversion = None

    # Get latest version of compnent variant
    data = get_component(dhurl, cookies, compname, compvariant, compversion)
    if (data[0] == -1):
        data = get_component(dhurl, cookies, compname, compvariant, None)
        if (data[0] == -1):
            data = get_component(dhurl, cookies, compname, "", None)

    compid = data[0]
    found_compname = data[1]
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

    # Create base component variant
    # if one is not found
    # Get the new compid of the new component variant

    if (compid < 0):
        if (compversion is None or compversion == ""):
            compid = new_file_component(dhurl, cookies, compname, "", "", -1, None)
        else:
            compid = new_file_component(dhurl, cookies, compname, compvariant, "", -1, None)

    # Create component items for the component
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
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + urllib.parse.quote(compname + ";" + compvariant), cookies)
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
    pprint(parent_compid)
    if (parent_compid < 0):
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + urllib.parse.quote(compname + ";" + compvariant), cookies)
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
        data = get_json(dhurl + "/dmadminweb/API/new/compver/" + urllib.parse.quote(compname + ";" + compvariant), cookies)
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
    data = get_component(dhurl, cookies, compname, compvariant, compversion)
    compid = data[0]

    if (compid < 0):
        return

    count = 0
    attr_str = ""

    for key in attrs.keys():
        value = attrs.get(key, "")
        if (value is None):
            value = ""

        if (count == 0):
            attr_str = attr_str + "name=" + urllib.parse.quote(key) + "&value=" + urllib.parse.quote(value)
        else:
            attr_str = attr_str + "&name" + str(count) + "=" + urllib.parse.quote(key) + "&value" + str(count) + "=" + urllib.parse.quote(value)

        count = count + 1

    if (attr_str):
        # Update Attrs for component
        data = get_json(dhurl + "/dmadminweb/API/setvar/component/" + str(compid) + "?" + attr_str, cookies)
        if (not data):
            return [False, "Could not update attributes on '" + compname + "'"]
        return [True, data, dhurl + "/dmadminweb/API/setvar/component/" + str(compid) + "?" + attr_str]

    return [False, "No attributes to update on '" + compname + "'"]


def get_application(dhurl, cookies, appname, appversion):
    appversion = clean_name(appversion)

    application = ""

    if (appversion is not None and appversion != ""):
        application = appname + ";" + appversion
    else:
        application = appname

    data = get_json(dhurl + "/dmadminweb/API/application/" + urllib.parse.quote(application), cookies)

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


def get_base_component(dhurl, cookies, compid):
    data = get_json(dhurl + "/dmadminweb/API/component/" + str(compid), cookies)

    if (data is None):
        return [-1, "", -1]

    result = data.get('result', None)

    while (result and result.get('predecessor', None)):
        data2 = get_json(dhurl + "/dmadminweb/API/component/" + str(result['predecessor']['id']), cookies)

        if (data2 is None):
            break

        result = data2.get('result', None)

    return result['id']


def new_application(dhurl, cookies, appname, appversion, envs):
    appversion = clean_name(appversion)

    appid = 0
    parent_appid = -1

    domain = ""
    if ('.' in appname):
        parts = appname.split('.')
        if (parts):
            parts.pop()
        domain = '.'.join(parts)
        domain = "domain=" + urllib.parse.quote(domain)
        appname = appname.split('.')[-1]

    # Get Base Version
    data = get_application(dhurl, cookies, appname, "")
    parent_appid = data[0]

    # Create base version
    if (parent_appid < 0):
        data = get_json(dhurl + "/dmadminweb/API/new/application/" + urllib.parse.quote(appname) + "?" + domain, cookies)
        if (data.get('success', False)):
            data = get_application(dhurl, cookies, appname, "")
            parent_appid = data[0]

        if (envs is not None):
            for env in envs:
                data = get_json(dhurl + "/dmadminweb/API/assign/application/" + urllib.parse.quote(appname) + "/" + urllib.parse.quote(env), cookies)

    # Refetch parent to get version list
    data = get_application(dhurl, cookies, appname, "")
    latest_appid = data[2]

    # Refetch the current app version to see if we need to create it or not
    data = get_application(dhurl, cookies, appname, appversion)
    appid = data[0]

    if (appid < 0):
        data = get_json(dhurl + "/dmadminweb/API/newappver/" + str(latest_appid) + "/?name=" + urllib.parse.quote(appname + ";" + appversion) + "&" + domain, cookies)

        if (not data.get('success', False)):
            return [-1, data.get('error', "")]

        appid = data['result']['id']

    return [appid, ""]


def add_compver_to_appver(dhurl, cookies, appid, compid):
    replace_compid = -1
    basecompid = get_base_component(dhurl, cookies, compid)
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
                app_basecompid = get_base_component(dhurl, cookies, comp['id'])
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
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=acvm&a=" + str(appid) + "&c=" + str(compid) + "&xpos=" + str(xpos) + "&ypos=" + str(ypos), cookies)
    get_json(dhurl + "/dmadminweb/UpdateAttrs?f=cal&a=" + str(appid) + "&fn=" + str(parent_compid) + "&tn=" + str(compid), cookies)


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


# def update_versions(project, compname, compvariant, compversion):
#    # Clone apprepo
#    data = clone_repo(project)
#    if (data is not None):
#        pprint(data)
