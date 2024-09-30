import logging, click
from configops.utils import nacos_client
from configops.utils.exception import ChangeLogException
from configops.changelog.nacos_change import NacosChangeLog, apply_changes

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    __print_banner()
    pass


@cli.command(
    name="update-nacos", help="Update nacos config changes in the changelog file"
)
@click.option("--changelog-file", required=True, help="The changelog file")
@click.option("--url", required=True, help="The nacos connection URL")
@click.option("--username", required=True, help="The nacos username")
@click.option("--password", required=True, help="The nacos password")
@click.option(
    "--changesets",
    required=False,
    help="The specific changeset id to match. Use commas for multiple values",
)
@click.option(
    "--contexts",
    required=False,
    help="The specific contexts to match. Use commas for multiple values",
)
@click.option(
    "--var",
    required=False,
    multiple=True,
    help="The vairable used in changelog file. This parameter can be used multiple times for multiple vairable. [key]=[value]",
)
def update_nacos(changelog_file, url, username, password, changesets, contexts, var):
    vars = dict(item.split("=") for item in var)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=url,
        username=username,
        password=password,
    )

    try:
        spec_changesets = []
        if changesets:
            spec_changesets = [item for item in changesets.split(",") if item]

        nacosChangeLog = NacosChangeLog(changelogFile=changelog_file)
        result = nacosChangeLog.fetch_multi(
            client, "", 0, contexts, vars, False, spec_changesets
        )
        click.echo(f"Change set ids:{result[0]}")
        nacosConfigs = result[1]
        for nacosConfig in nacosConfigs:
            namespace = nacosConfig["namespace"]
            group = nacosConfig["group"]
            dataId = nacosConfig["dataId"]

            client.namespace = namespace
            suc = client.publish_config_post(
                dataId,
                group,
                nacosConfig["nextContent"],
                config_type=nacosConfig["format"],
            )
            if suc:
                click.echo(
                    f"Update nacos config success. namespace:{namespace}, group:{group}, dataId:{dataId}"
                )
            else:
                click.echo(
                    f"Update nacos config fail. namespace:{namespace}, group:{group}, dataId:{dataId}"
                )
    except ChangeLogException as err:
        click.echo(f"Nacos changelog invalid. {err}", err=True)
    except KeyError as err:
        click.echo(f"Vars missing key: {err}", err=True)


@cli.command(
    name="update-nacos-check",
    help="Generate nacos config changes in the changelog file",
)
@click.option("--changelog-file", required=True, help="The changelog file")
@click.option("--url", required=True, help="The Nacos connection URL")
@click.option("--username", required=True, help="The nacos username")
@click.option("--password", required=True, help="The nacos password")
@click.option(
    "--contexts",
    required=False,
    help="The specific contexts to match. Use commas for multiple values",
)
@click.option(
    "--var",
    required=False,
    multiple=True,
    help="The vairable used in changelog file. This parameter can be used multiple times for multiple vairable. [key]=[value]",
)
def update_nacos_check(changelog_file, url, username, password, contexts, var):
    vars = dict(item.split("=") for item in var)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=url,
        username=username,
        password=password,
    )
    try:
        nacosChangeLog = NacosChangeLog(changelogFile=changelog_file)
        result = nacosChangeLog.fetch_multi(client, "", 0, contexts, vars, False)
        click.echo(f"Change set ids:{result[0]}")
        click.echo(f"Affected nacos config list:")
        nacosConfigs = result[1]
        for nacosConfig in nacosConfigs:
            namespace = nacosConfig["namespace"]
            group = nacosConfig["group"]
            dataId = nacosConfig["dataId"]
            click.echo(f"-- namespace:{namespace}, group:{group}, dataId:{dataId}")
    except ChangeLogException as err:
        click.echo(f"Nacos changelog invalid. {err}", err=True)
    except KeyError as err:
        click.echo(f"Vars missing key: {err}", err=True)


def __print_banner():
    click.echo(
        """
#####################################################              
##   ____             __ _        ___              ##
##  / ___|___  _ __  / _(_) __ _ / _ \ _ __  ___   ##
## | |   / _ \| '_ \| |_| |/ _` | | | | '_ \/ __|  ##
## | |__| (_) | | | |  _| | (_| | |_| | |_) \__ \  ##
##  \____\___/|_| |_|_| |_|\__, |\___/| .__/|___/  ##
##                         |___/      |_|          ##
##                                                 ##
#####################################################
"""
    )


if __name__ == "__main__":
    cli()
