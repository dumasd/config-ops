import re, logging, os, shlex

logger = logging.getLogger(__name__)


class TestPath:
    def test_walk_dir(self):

        all_files = []
        for dirpath, dirnames, filenames in os.walk(
            "/Users/wukai/IdeaProjects/Opensource/config-ops/tests"
        ):
            for filename in filenames:
                if filename.endswith((".py")):
                    all_files.append(os.path.join(dirpath, filename))
        logger.info(f"all_files: {all_files}")


class TestString:
    """
    python  string test
    """

    def test_blank(self):
        a = None

        # logger.info(len(a))
        b = "    "
        assert len(b.strip()) == 0
        logger.info(len(b.strip()))

    def test_file(self):
        f = "/Users/wukai/IdeaProjects/Opensource/config-ops/tests/changelog/changelog-root.yaml"
        logger.info(os.path.isfile(f))

    def test_shlex(self):
        def split_with_quotes(input_string):
            lexer = shlex.shlex(input_string, posix=True)
            lexer.whitespace_split = True
            lexer.quotes = '"'
            result = []
            for token in lexer:
                # 如果 token 是双引号括起来的内容，重新加上双引号
                if " " in token and not token.startswith('"'):
                    result.append(f'"{token}"')
                else:
                    result.append(token)
            return result

        result = split_with_quotes(
            '--changelog-file=changelog-root.yaml --label-filter="before and api"'
        )
        logger.info(f"split_with_quotes: {result}")

        result = shlex.split(
            '--changelog-file=changelog-root.yaml --label-filter="before and api"'
        )
        logger.info(f"shlex split: {result}")


class TestRegex:
    """
    python regex test
    """

    def __extract_version(self, name):
        match = re.search(r"(\d+\.\d+(?:\.\d+){0,2})(?:-([a-zA-Z0-9]+))?", name)
        if match:
            # 将版本号分割为整数元组，例如 '1.2.3' -> (1, 2, 3)
            version_numbers = tuple(map(int, match.group(1).split(".")))
            suffix = match.group(2) or ""
            return version_numbers, suffix
        return (0,), ""  # 默认返回最小版本

    def test_version(self):
        filenames = [
            "faf/project-1.2.tar.gz",
            "project-1.2.3-01.tar.gz",
            "project-1.2.3-02.tar.gz",
            "project-2.0.0.zip",
            "project-1.10.1.5.tar.gz",
            "project-1.3.tar.gz",
            "goose/project-1.2.10.tar.gz",
        ]
        for item in filenames:
            ver, suffix = self.__extract_version(item)
            logger.info(f"find version tuple {ver}, suffix {suffix}")

        sorted_filenames = sorted(filenames, key=self.__extract_version)
        logger.info(f"sort files {sorted_filenames}")
        pass

    def test_arguments(self):
        input_string = (
            ' --changelog-file=changelog-root.yaml    --label-filter="before and api" '
        )
        result = re.findall(
            r'"[^"]*"|\S+',
            input_string,
        )
        logger.info(f"regex list: {result}")

        def parse_args_with_quotes(input_string):
            result = []
            buffer = []
            inside_quotes = False

            for char in input_string:
                if char == '"':  # 切换双引号状态
                    inside_quotes = not inside_quotes
                    buffer.append(char)  # 保留双引号
                elif char == " " and not inside_quotes:  # 遇到空格且不在双引号内
                    if buffer:
                        result.append("".join(buffer))
                        buffer = []
                else:
                    buffer.append(char)

            if buffer:
                result.append("".join(buffer))

            return result

        result = parse_args_with_quotes(input_string)
        logger.info(f"parse_args_with_quotes: {result}")
