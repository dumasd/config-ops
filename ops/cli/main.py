import logging, click
from ops.utils import nacos_client
from ops.changelog.nacos_change import NacosChangeLog, apply_changes

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
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
    click.echo("Nacos config update")
    vars = dict(item.split("=") for item in var)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=url,
        username=username,
        password=password,
    )
    nacosChangeLog = NacosChangeLog(changelogFile=changelog_file)
    result = nacosChangeLog.fetch_multi(client, "", 0, contexts, vars, False)


@cli.command(name="check-nacos", help="Check nacos config changes")
@click.option("--changelog-file", required=True, help="The changelog file")
@click.option("--url", required=False, help="The Nacos connection URL")
@click.option("--username", required=False, help="The nacos username")
@click.option("--password", required=False, help="The nacos password")
def check_nacos(changelog_file, url, username, password):
    click.echo("Nacos config check")


if __name__ == "__main__":
    cli()
