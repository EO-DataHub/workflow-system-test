import unittest
from unittest.mock import Mock, patch

from system_tests.cwl_loader import FileCWLLoader, GitCWLLoader


class TestFileCWLLoader(unittest.TestCase):
    def test_init(self):
        cwl_loader = FileCWLLoader("test-filename.cwl", "inputs-filename.json")

        self.assertEqual("test-filename.cwl", cwl_loader.cwl_filename)
        self.assertEqual("inputs-filename.json", cwl_loader.inputs_filename)

    def test_load_inputs(self):
        cwl_loader = FileCWLLoader(
            "examples/convert-url-app.cwl", "examples/convert-url-app-inputs.json"
        )

        inputs = cwl_loader.load_inputs()

        self.assertIsNotNone(inputs)

    @patch("system_tests.cwl_loader.time")  # Mock the time module
    def test_load_cwl(self, mock_time):
        cwl_loader = FileCWLLoader(
            "examples/convert-url-app.cwl", "examples/convert-url-app-inputs.json"
        )

        mock_time.strftime.return_value = "15-00-00"

        cwl_file = cwl_loader.load_cwl()

        self.assertIsNotNone(cwl_file.cwl_data)
        self.assertIsNotNone(cwl_file.cwl_inputs)
        self.assertEqual("examples/convert-url-app.cwl", cwl_file.location)
        self.assertEqual("test-convert-url--15-00-00", cwl_file.get_workflow_id())


class TestGitCWLLoader(unittest.TestCase):
    def test_init(self):
        cwl_loader = GitCWLLoader(
            "test-filename.cwl", "inputs-filename.json", "test-repo", "test-branch"
        )

        self.assertEqual("test-filename.cwl", cwl_loader.cwl_filename)
        self.assertEqual("inputs-filename.json", cwl_loader.inputs_filename)
        self.assertEqual("test-repo", cwl_loader.repo_name)
        self.assertEqual("test-branch", cwl_loader.branch_name)
        self.assertIsNotNone(cwl_loader._g)

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

        self.assertEqual({"inputs": "test"}, inputs)

    @patch("system_tests.cwl_loader.Github")  # Mock the Github class
    @patch("system_tests.cwl_loader.GitCWLLoader.load_inputs")  # Mock the load_inputs method
    def test_load_cwl(self, mock_load_inputs, MockGithub):
        # Mock the Github instance
        mock_github_instance = MockGithub.return_value
        mock_load_inputs.return_value = {"inputs": "test"}

        # Configure mocks
        mock_contents = Mock()
        mock_repo = Mock()
        mock_contents.decoded_content = b'{"$graph": [{"id": "test-convert-url"}]}'
        mock_repo.get_contents.return_value = mock_contents
        mock_github_instance.get_repo.return_value = mock_repo

        cwl_loader = GitCWLLoader(
            "test-filename.cwl", "inputs-filename.json", "test-repo", "test-branch"
        )

        cwl_file = cwl_loader.load_cwl()

        self.assertEqual({"$graph": [{"id": "test-convert-url"}]}, cwl_file.cwl_data)
        self.assertEqual({"inputs": "test"}, cwl_file.cwl_inputs)
        self.assertEqual(
            "https://raw.githubusercontent.com/test-repo/test-branch/test-filename.cwl",
            cwl_file.location,
        )
        self.assertEqual("test-convert-url", cwl_file.get_workflow_id())
