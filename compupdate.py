from pprint import pprint
import click

from deployhub import dhapi


@click.command()
@click.option('--dhurl', help='DeployHub Url', required=True)
@click.option('--dhuser', help='DeployHub User', required=True)
@click.option('--dhpass', help='DeployHub Password', required=True)
@click.option('--kubeyaml', help='kubectl get deployment -o yaml (output)')
@click.option('--defaultdomain', help='Default Domain')
@click.option('--project', help='Application Project')
@click.option('--compname', help='Component Name')
@click.option('--compvariant', help='Component Variant')
@click.option('--compversion', help='Component Version')
@click.option('--compattr', help='Component Attribute', multiple=True)
def main(dhurl, dhuser, dhpass, kubeyaml, defaultdomain, project, compname, compvariant, compversion, compattr):
    cookies = dhapi.login(dhurl, dhuser, dhpass)
    complist = []

    if cookies is None:
        return

    if (kubeyaml is not None):
        complist = dhapi.import_cluster(kubeyaml, defaultdomain, dhurl, cookies)
    else:
        comp = {'project': project, 'compname': compname, 'compvariant': compvariant, 'compversion': compversion, 'compattr': compattr}
        pprint(comp)
        complist.append(comp)

    print("\n")

    for comp in complist:
        project = comp['project']
        compname = comp['compname']
        compattr = comp['compattr']
        compvariant = comp['compvariant']
        compversion = comp['compversion']
        print("Processing " + compname + ":" + compvariant + "-" + compversion)

        compvariant = comp['compvariant'].replace("-", "_").replace(".", "_")
        compversion = comp['compversion'].replace("-", "_").replace(".", "_")

        compid = dhapi.new_component_version(compname, compvariant, compversion, 'docker', dhurl, cookies)

        # Update the compattrs for the new compid version
        dhapi.update_component_attrs(compid, compattr, dhurl, cookies)

    # dhapi.update_versions(project, compname, compvariant, compversion)
    print("\n")


if __name__ == '__main__':
    main()
