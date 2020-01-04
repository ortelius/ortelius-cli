#!/usr/local/bin/python3

import sys
import click

from deployhub import dhapi


@click.command()
@click.option('--dhurl', help='DeployHub Url', required=True)
@click.option('--dhuser', help='DeployHub User', required=True)
@click.option('--dhpass', help='DeployHub Password', required=True)
@click.option('--appname', help='Application Name', required=True)
@click.option('--env', help='Environment', required=True)
def main(dhurl, dhuser, dhpass, appname, env):

    print("Logging into DeployHub")
    cookies = dhapi.login(dhurl, dhuser, dhpass)

    if cookies is None:
        return

    # Deploy Application to Environment
    print(f'Deploying {appname} to {env}')
    data = dhapi.deploy_application(dhurl, cookies, appname, env)

    deployid = data[0]
    if (deployid < 0):
        print(data[1])
        sys.exit(1)

    print(f"Fetching Logs for {deployid}")
    data = dhapi.get_logs(dhurl, cookies, deployid)

    print(data[1])
    if (data[0]):
        print("Successful")
        sys.exit(0)
    else:
        print("Failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
