import unittest
from unittest.mock import Mock, patch

from system_tests.cwl_loader import FileCWLLoader, GitCWLLoader


class TestFileCWLLoader(unittest.TestCase):
    def test_init(self):
        cwl_loader = FileCWLLoader("test-filename.cwl", "inputs-filename.json")

        assert cwl_loader.cwl_filename == "test-filename.cwl"
        assert cwl_loader.inputs_filename == "inputs-filename.json"

    def test_load_inputs(self):
        cwl_loader = FileCWLLoader(
            "examples/convert-url-app.cwl", "examples/convert-url-app-inputs.json"
        )

        inputs = cwl_loader.load_inputs()

        assert inputs is not None

    def test_load_cwl(self):
        cwl_loader = FileCWLLoader(
            "examples/convert-url-app.cwl", "examples/convert-url-app-inputs.json"
        )

        cwl_file = cwl_loader.load_cwl()

        assert cwl_file.cwl_data is not None
        assert cwl_file.cwl_inputs is not None
        assert cwl_file.location == "examples/convert-url-app.cwl"


class TestGitCWLLoader(unittest.TestCase):
    def test_init(self):
        cwl_loader = GitCWLLoader(
            "test-filename.cwl", "inputs-filename.json", "test-repo", "test-branch"
        )

        assert cwl_loader.cwl_filename == "test-filename.cwl"
        assert cwl_loader.inputs_filename == "inputs-filename.json"
        assert cwl_loader.repo_name == "test-repo"
        assert cwl_loader.branch_name == "test-branch"
        assert cwl_loader._g is not None

    @patch("system_tests.cwl_loader.Github")  # Mock the Github class
    def test_load_inputs(self, MockGithub):
        # Mock the Github instance
        mock_github_instance = MockGithub.return_value

        # Configure mocks
        mock_contents = Mock()
        mock_repo = Mock()
        mock_contents.decoded_content = b'{"inputs": "test"}'
        mock_repo.get_contents.return_value = mock_contents
        mock_github_instance.get_repo.return_value = mock_repo

        cwl_loader = GitCWLLoader(
            "test-filename.cwl", "inputs-filename.json", "test-repo", "test-branch"
        )

        inputs = cwl_loader.load_inputs()

        assert inputs == {"inputs": "test"}

    @patch("system_tests.cwl_loader.Github")  # Mock the Github class
    @patch("system_tests.cwl_loader.GitCWLLoader.load_inputs")  # Mock the load_inputs method
    def test_git_cwl_loader_initialization(self, mock_load_inputs, MockGithub):
        # Mock the Github instance
        mock_github_instance = MockGithub.return_value
        mock_load_inputs.return_value = {"inputs": "test"}

        # Configure mocks
        mock_contents = Mock()
        mock_repo = Mock()
        mock_contents.decoded_content = b'{"cwl": "test"}'
        mock_repo.get_contents.return_value = mock_contents
        mock_github_instance.get_repo.return_value = mock_repo

        cwl_loader = GitCWLLoader(
            "test-filename.cwl", "inputs-filename.json", "test-repo", "test-branch"
        )

        cwl_file = cwl_loader.load_cwl()

        assert cwl_file.cwl_data == {"cwl": "test"}
        assert cwl_file.cwl_inputs == {"inputs": "test"}
        assert (
            cwl_file.location
            == "https://raw.githubusercontent.com/test-repo/test-branch/test-filename.cwl"
        )
