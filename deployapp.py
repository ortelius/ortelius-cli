from pprint import pprint
import click

from deployhub import dhapi


@click.command()
@click.option('--dhurl', help='DeployHub Url', required=True)
@click.option('--dhuser', help='DeployHub User', required=True)
@click.option('--dhpass', help='DeployHub Password', required=True)
@click.option('--appname', help='Application Name', required=True)
@click.option('--appversion', help='Application Version')
@click.option('--compname', help='Component Name', required=True)
@click.option('--compvariant', help='Component Variant')
@click.option('--compversion', help='Component Version')
@click.option('--docker', 'kind', flag_value='docker',
              default=True, help='Component Item Type')
@click.option('--file', 'kind', flag_value='file')
@click.option('--compattr', help='Component Attribute', multiple=True)
@click.option('--env', help='Environments', multiple=True)
def main(dhurl, dhuser, dhpass, appname, appversion, compname, compvariant, compversion, kind, env, compattr):

    print("Logging into DeployHub")
    cookies = dhapi.login(dhurl, dhuser, dhpass)

    if cookies is None:
        return

    if (compvariant is None):
        compvariant = ""

    # create component version
    print("Creating Component")
    compid = dhapi.new_component_version(dhurl, cookies, compname, compvariant, compversion, kind, None)
    print("Creation Done: " + str(compid))

    attrs = {}
    print("Updating Component Attributes\n")
    for attr in compattr:
        (key, value) = attr.split(':', 1)
        attrs[key] = value

    pprint(attrs)
    print("")

    data = dhapi.update_component_attrs(dhurl, cookies, compname, "", compversion, attrs)
    print("Attribute Update Done")

    print("Creating Application Version")
    data = dhapi.new_application(dhurl, cookies, appname, appversion, env)
    appid = data[0]
    print("Creation Done: " + str(appid))

    print("Assigning Component Version to Application Version")
    data = dhapi.add_compver_to_appver(dhurl, cookies, appid, compid)
    print("Assignment Done")


if __name__ == '__main__':
    main()
