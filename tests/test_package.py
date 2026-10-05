from importlib.metadata import version

import khmer_engine


def test_version_matches_installed_metadata():
    assert khmer_engine.__version__ == version("khmer-engine")
