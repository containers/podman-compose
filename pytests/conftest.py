import pathlib
import sys

FOLDER_PARAMETER_NAME = "folder"
HERE = pathlib.Path(__file__).parent
ROOT = HERE / ".."
TESTS_FOLDER = ROOT / "tests"

sys.path.append(ROOT)


def pytest_generate_tests(metafunc):
    if FOLDER_PARAMETER_NAME in metafunc.fixturenames:
        metafunc.parametrize(FOLDER_PARAMETER_NAME, get_fixtures_folder())


def get_fixtures_folder():
    for folder in TESTS_FOLDER.glob("*"):
        if not folder.is_dir():
            continue

        if not any(folder.glob("*-compose.y*ml")):
            continue

        yield str(folder.absolute())