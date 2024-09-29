import logging, click
from configops.utils import nacos_client
from configops.utils.exception import ChangeLogException
from configops.changelog.nacos_change import NacosChangeLog, apply_changes

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    __print_banner()
    pass


@cli.command(name="update-nacos", help="Apply nacos config changes")
@click.option("--changelog-file", required=True, help="The changelog file")
@click.option("--contexts", required=False, help="Changeset contexts to match")
@click.option(
    "--var",
    required=False,
    multiple=True,
    help="The vairables used in changelog file. [key]=[value]",
)
@click.option("--url", required=True, help="The nacos connection URL")
@click.option("--username", required=True, help="The nacos username")
@click.option("--password", required=True, help="The nacos password")
def update_nacos(changelog_file, contexts, var, url, username, password):
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


@cli.command(name="check-nacos", help="Check nacos config changes")
@click.option("--changelog-file", required=True, help="The changelog file")
@click.option("--contexts", required=False, help="Changeset contexts to match")
@click.option(
    "--var",
    required=False,
    multiple=True,
    help="The vairables used in changelog file. [key]=[value]",
)
@click.option("--url", required=True, help="The Nacos connection URL")
@click.option("--username", required=True, help="The nacos username")
@click.option("--password", required=True, help="The nacos password")
def check_nacos(changelog_file, contexts, var, url, username, password):
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
