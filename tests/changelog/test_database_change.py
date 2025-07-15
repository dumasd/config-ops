import unittest, logging, secrets, secrets, re
from configops.changelog.changelog_utils import (
    pack_changes,
    unpack_changes,
)

logger = logging.getLogger(__name__)


class TestDatabaseChangelogUtils(unittest.TestCase):
    def setUp(self):
        # Set up any necessary test data or state
        pass

    def test_read_stdout_sql(self):
        stdout = """
--  Lock Database
UPDATE test.databasechangeloglock SET `LOCKED` = 1, LOCKEDBY = 'wukaideMacBook-Pro.local (192.168.88.115)', LOCKGRANTED = NOW() WHERE ID = 1 AND `LOCKED` = 0;

--  *********************************************************************
--  Update Database Script
--  *********************************************************************
--  Change Log: changelog-1.0.yaml
--  Ran at: 2025/4/21 下午4:12
--  Against: root@localhost@jdbc:mysql://localhost:3306/test
--  Liquibase version: 4.31.1
--  *********************************************************************

--  Changeset changelog-1.0.yaml::maven-example-1.0.1-release::bruce.wu
--  example-comment
CREATE TABLE test.person (id INT AUTO_INCREMENT NOT NULL, name VARCHAR(50) NOT NULL, address1 VARCHAR(50) NULL, address2 VARCHAR(50) NULL, city VARCHAR(30) NULL, CONSTRAINT PK_PERSON PRIMARY KEY (id));

CREATE TABLE IF NOT EXISTS `company` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) COLLATE utf8mb4_bin NOT NULL,
  `address1` varchar(50) COLLATE utf8mb4_bin DEFAULT NULL,
  `address2` varchar(50) COLLATE utf8mb4_bin DEFAULT NULL,
  `city` varchar(30) COLLATE utf8mb4_bin DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

INSERT INTO test.databasechangelog (ID, AUTHOR, FILENAME, DATEEXECUTED, ORDEREXECUTED, MD5SUM, `DESCRIPTION`, COMMENTS, EXECTYPE, CONTEXTS, LABELS, LIQUIBASE, DEPLOYMENT_ID) VALUES ('maven-example-1.0.1-release', 'bruce.wu', 'changelog-1.0.yaml', NOW(), 1, '9:4b7f5de5d7d28f1fdd98d84a25dabf81', 'createTable tableName=person; sql', 'example-comment', 'EXECUTED', 'gradle-example', 'gradle-example', '4.31.1', '5223130811');

--  Changeset changelog-1.0.yaml::gradle-example-1.0.2-release::bruce.wu
--  example-comment
ALTER TABLE test.person ADD zip_code VARCHAR(70) NULL;

ALTER TABLE company ADD COLUMN zip_code varchar(70) NULL COMMENT '邮编';

INSERT INTO test.databasechangelog (ID, AUTHOR, FILENAME, DATEEXECUTED, ORDEREXECUTED, MD5SUM, `DESCRIPTION`, COMMENTS, EXECTYPE, CONTEXTS, LABELS, LIQUIBASE, DEPLOYMENT_ID) VALUES ('gradle-example-1.0.2-release', 'bruce.wu', 'changelog-1.0.yaml', NOW(), 2, '9:7b7bac1a976e78629b3afff0f1970ecd', 'addColumn tableName=person; sql', 'example-comment', 'EXECUTED', 'gradle-example', 'gradle-example', '4.31.1', '5223130811');

--  Release Database Lock
UPDATE test.databasechangeloglock SET `LOCKED` = 0, LOCKEDBY = NULL, LOCKGRANTED = NULL WHERE ID = 1;


"""
        lines = stdout.split("\n")
        change_set_changes = {}
        start_change_set = False
        change_set_id = None
        for line in lines:
            end_match = re.search(r"^--\s+Release\sDatabase\sLock", line)
            if end_match:
                break
            databasechangelog_match = re.search(r"databasechangelog", line, re.IGNORECASE)
            if databasechangelog_match:
                continue
            match = re.search(r"^--\s+Changeset\s+(\S+)::(\S+)::(\S+)", line)
            if match:
                start_change_set = True
                change_set_id = match.group(2)
                #author = match.group(2)
            elif start_change_set and not line.startswith("--"):
                changes = change_set_changes.get(change_set_id, "")
                changes = f"{changes}\n{line}"
                change_set_changes[change_set_id] = changes

        logger.info("change_set_changes: %s", change_set_changes)

    def test_read_stdout_history(self):
        stdout = """Liquibase History for jdbc:mysql://localhost:3306

- Database updated at 2025/4/22 下午2:43. Applied 2 changeset(s) in 0.0s, DeploymentId: 5304189396
  changelog-1.0.yaml::maven-example-1.0.1-release::bruce.wu
  changelog-1.0.yaml::gradle-example-1.0.2-release::bruce.wu

- Database updated at 2025/4/22 下午2:43. Applied 1 changeset(s), DeploymentId: 5304189399
  changelog-1.1.yaml::maven-example-1.1.1-release::henry.hua
    """    
        lines = stdout.split("\n")
        for line in lines:
            match = re.search(r"^\s+(\S+)::(\S+)::(\S+)", line)
            if match:
                filename = match.group(1)
                change_set_id = match.group(2)
                author = match.group(3)
                logger.info("filename:%s, change_set_id:%s, author:%s", filename, change_set_id, author)