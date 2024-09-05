import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import yaml
from github import Github


@dataclass(frozen=True)
class CWLFile:
    cwl_data: dict
    cwl_inputs: dict
    location: str

    def get_workflow_id(self) -> str:
        return self.cwl_data.get("$graph")[0].get("id")

    def get_workflow_inputs(self) -> dict:
        return self.cwl_inputs


class CWLLoader(ABC):
    @abstractmethod
    def load_cwl(self) -> CWLFile:
        raise NotImplementedError()

    def load_inputs(self) -> dict:
        raise NotImplementedError()

    def get_location(self) -> str:
        raise NotImplementedError()


class FileCWLLoader(CWLLoader):
    def __init__(self, cwl_filename: str, inputs_filename: str):
        self.cwl_filename = cwl_filename
        self.inputs_filename = inputs_filename

    def load_cwl(self) -> CWLFile:
        with open(self.cwl_filename, "r") as workflow_file:
            workflow_file = workflow_file.read()
        cwl_file_dict = yaml.safe_load(workflow_file)
        new_workflow_id = cwl_file_dict["$graph"][0]["id"].split("--")[0]
        cwl_file_dict["$graph"][0]["id"] = (
            new_workflow_id + "--" + time.strftime("%Y-%m-%dT%H-%M-%S")
        )
        # Convert the dictionary back to YAML
        updated_workflow_content = yaml.dump(cwl_file_dict)
        # Write the updated content back to the file
        with open(self.cwl_filename, "w") as workflow_file:
            workflow_file.write(updated_workflow_content)

        return CWLFile(cwl_file_dict, self.load_inputs(), self.get_location())

    def load_inputs(self) -> dict:
        with open(self.inputs_filename, "r") as inputs_file:
            inputs_file = inputs_file.read()
        return json.loads(inputs_file)

    def get_location(self) -> str:
        return self.cwl_filename


class GitCWLLoader(CWLLoader):
    def __init__(
        self, cwl_filename: str, inputs_filename: str, repo_name: str, branch_name: str = "main"
    ):
        self.cwl_filename = cwl_filename
        self.inputs_filename = inputs_filename
        self.repo_name = repo_name
        self.branch_name = branch_name
        self._g = Github()

    def load_cwl(self) -> CWLFile:
        repo = self._g.get_repo(self.repo_name)
        raw_file = repo.get_contents(self.cwl_filename, ref=self.branch_name)
        workflow_file = raw_file.decoded_content
        return CWLFile(yaml.safe_load(workflow_file), self.load_inputs(), self.get_location())

    def load_inputs(self) -> dict:
        repo = self._g.get_repo(self.repo_name)
        raw_file = repo.get_contents(self.inputs_filename, ref=self.branch_name)
        inputs_file = raw_file.decoded_content
        return json.loads(inputs_file)

    def get_location(self) -> str:
        return f"https://raw.githubusercontent.com/{self.repo_name}/{self.branch_name}/{self.cwl_filename}"
