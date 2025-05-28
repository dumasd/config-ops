# empty

import logging, os, string, platform, random, shlex, subprocess, re
from configops.changelog import changelog_utils
from configops.utils import secret_util
from configops.utils.constants import SystemType, extract_version
from configops.database.db import db, ConfigOpsChangeLogChanges
from configops.utils.exception import ChangeLogException
from configops.config import (
    get_config,
    get_database_cfg,
    get_liquibase_cfg,
    get_java_home_dir,
)

logger = logging.getLogger(__name__)

LIQUIBASE_CMD_UPDATE = "update"
LIQUIBASE_CMD_UPDATE_SQL = "update-sql"
LIQUIBASE_CMD_HISTORY = "history"


class DatabaseChangeLog:
    def __init__(self, changelog_file=None, app=None):
        self.changelog_file = changelog_file
        self.is_temp_changelog_file = False
        self.app = app
        self.__init_changelog()

    def __init_changelog(self):
        changelog_file = self.changelog_file
        if not changelog_file:
            return
        if not os.path.exists(changelog_file):
            raise ChangeLogException(
                f"Changelog file or folder does not exists: {changelog_file}"
            )
        if not os.path.isdir(changelog_file):
            return

        # 文件夹下面的changelog文件，聚合成一个change-root.yaml
        changelogfiles = []
        for _, _, filenames in os.walk(changelog_file):
            for filename in filenames:
                if filename.endswith((".yaml", ".yml", ".xml")):
                    changelogfiles.append(filename)
        changelogfiles = sorted(changelogfiles, key=extract_version)
        if len(changelogfiles) > 0:
            suffix = "".join(random.sample(string.ascii_lowercase + string.digits, 10))
            root_file_name = f"changelog_root_{suffix}.yaml"
            root_file_content = "databaseChangeLog:"
            for file in changelogfiles:
                root_file_content = (
                    root_file_content + f"\n  - include:\n      file: {file}"
                )
            tmp_change_log_root_file = os.path.join(changelog_file, root_file_name)
            with open(tmp_change_log_root_file, "w", encoding="utf-8") as file:
                file.write(root_file_content)
            self.changelog_file = tmp_change_log_root_file
            self.is_temp_changelog_file = True

    def run_liquibase_cmd(self, command: str, cwd=None, args=None, db_id=None):
        command = command.strip()
        command_args_str = ""
        history_command_args_str = ""
        if db_id:
            db_config = get_database_cfg(self.app, db_id)
            if db_config == None:
                raise ChangeLogException(f"Database not found. databaseId:{db_id}")

            dialect = db_config.get("dialect", "mysql")
            host = db_config["url"]
            port = db_config["port"]
            username = db_config["username"]
            changelog_schema = db_config.get("changelogschema", "liquibase")

            secret_data = secret_util.get_secret_data(db_config)
            password = secret_data.password

            # jdbc:database_type://hostname:port/database_name
            command_database_args_str = f" --url jdbc:{dialect}://{host}:{port} --username {username} --password {password}"
            command_args_str = (
                command_args_str
                + command_database_args_str
                + f" --liquibase-schema-name {changelog_schema}"
            )
            history_command_args_str = (
                command_database_args_str
                + f" --default-schema-name {changelog_schema} --format TEXT"
            )

        # 设置classpath 和 defaultsFile
        liquibase_cfg = get_liquibase_cfg(self.app)
        if liquibase_cfg:
            defaultsFile = liquibase_cfg.get("defaults-file")
            jdbcDriverDir = liquibase_cfg.get("jdbc-drivers-dir")
            defaultsFileOpt = (
                command_args_str.find("--defaults-file") < 0
                or command_args_str.find("--defaultsFile") < 0
            )
            if defaultsFile and os.path.exists(defaultsFile) and defaultsFileOpt:
                command_args_str = (
                    command_args_str
                    + " --defaults-file "
                    + os.path.abspath(defaultsFile)
                )

            classpathOpt = command_args_str.find("--classpath") < 0
            if jdbcDriverDir and os.path.exists(jdbcDriverDir) and classpathOpt:
                separator = ";" if platform.system() == "Windows" else ":"
                base = os.path.abspath(jdbcDriverDir)
                jar_files = [f for f in os.listdir(jdbcDriverDir) if f.endswith(".jar")]
                classpath = separator.join(os.path.join(base, jar) for jar in jar_files)
                command_args_str = command_args_str + " --classpath " + classpath

        if args:
            command_args_str = command_args_str + " " + args

        # 解析changelogFile
        working_dir = cwd if cwd else os.getcwd()
        if self.changelog_file:
            cmd_changelog_file = os.path.relpath(self.changelog_file, working_dir)
            command_args_str = (
                command_args_str + " --changelog-file " + cmd_changelog_file
            )

        try:
            custom_env = os.environ.copy()
            # 设置JavaHome
            java_home = get_java_home_dir(self.app)
            if java_home:
                custom_env["JAVA_HOME"] = java_home

            if command == LIQUIBASE_CMD_UPDATE:
                # 先跑一遍update-sql找出执行的sql，并保存起来
                logger.info(
                    f"Liquibase command: liquibase update-sql {command_args_str}"
                )
                liquibase_update_sql_sh = shlex.split(
                    f"liquibase {LIQUIBASE_CMD_UPDATE_SQL} {command_args_str.strip()}"
                )
                update_sql_completed_process = subprocess.run(
                    liquibase_update_sql_sh,
                    cwd=working_dir,
                    capture_output=True,
                    env=custom_env,
                )
                change_sets = self.__get_change_sets__(
                    update_sql_completed_process.stdout.decode()
                )

                # 跑一遍history找到已经执行记录，校验changesetId和filename
                if len(change_sets) > 0:
                    logger.info(
                        f"Liquibase command: liquibase history {history_command_args_str}"
                    )
                    liquibase_history_sh = shlex.split(
                        f"liquibase {LIQUIBASE_CMD_HISTORY} {history_command_args_str.strip()}"
                    )
                    history_completed_process = subprocess.run(
                        liquibase_history_sh,
                        cwd=working_dir,
                        capture_output=True,
                        env=custom_env,
                    )
                    self.__check_changelog__(
                        change_sets, history_completed_process.stdout.decode()
                    )

                self.__save_changelog_changes__(db_id, change_sets)

            liquibase_cmd_sh = shlex.split(
                f"liquibase {command} {command_args_str.strip()}"
            )
            completed_process = subprocess.run(
                liquibase_cmd_sh,
                cwd=working_dir,
                capture_output=True,
                env=custom_env,
            )
            stdout = completed_process.stdout.decode()
            stderr = completed_process.stderr.decode()
            if stderr:
                logger.info(f"Liqubase run stderr. \n{stderr}")
            if stdout:
                logger.info(f"Liqubase run stdout. \n{stdout}")
            return {
                "stdout": stdout,
                "stderr": stderr,
                "retcode": completed_process.returncode,
            }
        finally:
            if self.is_temp_changelog_file:
                os.remove(self.changelog_file)

    def __save_changelog_changes__(self, db_id, change_sets):
        _secret = None
        if self.app:
            _secret = get_config(self.app, "config.node.secret")
        if _secret and len(change_sets) > 0:
            for change_set_id, change_set in change_sets.items():
                log_changes = (
                    db.session.query(ConfigOpsChangeLogChanges)
                    .filter_by(
                        change_set_id=change_set_id,
                        system_id=db_id,
                        system_type=SystemType.DATABASE.value,
                    )
                    .first()
                )
                if log_changes is None:
                    log_changes = ConfigOpsChangeLogChanges(
                        change_set_id=change_set_id,
                        system_type=SystemType.DATABASE.value,
                        system_id=db_id,
                        changes=changelog_utils.pack_encrypt_changes(
                            change_set["changes"], _secret
                        ),
                    )
                    db.session.add(log_changes)
                else:
                    log_changes.changes = changelog_utils.pack_encrypt_changes(
                        change_set["changes"], _secret
                    )
            db.session.commit()

    def __get_change_sets__(self, stdout):
        change_sets = {}
        if not stdout:
            return change_sets
        lines = stdout.split("\n")
        start_change_set = False
        change_set_id = None
        for line in lines:
            end_match = re.search(r"^--\s+Release\sDatabase\sLock", line)
            if end_match:
                break
            is_databasechangelog_match = re.search(
                r"databasechangelog", line, re.IGNORECASE
            )
            if is_databasechangelog_match:
                continue
            match = re.search(r"^--\s+Changeset\s+(\S+)::(\S+)::(\S+)", line)
            if match:
                start_change_set = True
                filename = match.group(1)
                change_set_id = match.group(2)
            elif start_change_set and not line.startswith("--"):
                changes = change_sets.get(change_set_id, "")
                changes = f"{changes}\n{line}"
                change_sets[change_set_id] = {
                    "filename": filename,
                    "changes": changes,
                }
        return change_sets

    def __check_changelog__(self, change_sets, stdout):
        if not stdout:
            return
        lines = stdout.split("\n")
        for line in lines:
            match = re.search(r"^\s+(\S+)::(\S+)::(\S+)", line)
            if match:
                filename = match.group(1)
                change_set_id = match.group(2)
                if (
                    change_set_id in change_sets
                    and change_sets[change_set_id]["filename"] != filename
                ):
                    raise ChangeLogException(
                        f"ChangeSetId is already defined in an earlier changelog file. ChangeSetId:{change_set_id}, Current file:{change_sets[change_set_id]["filename"]}, previous file:{filename}"
                    )
