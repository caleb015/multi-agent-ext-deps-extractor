# agents/standardized_output_agent.py
import os
import json
import logging

class StandardizedOutputAgent:
    """
    Takes in the extracted dependency data and writes it as JSON 
    to a ".shed/dependencies.json" within the repo.
    """

    def __init__(self, repo_path: str, language: str, dependencies: list):
        self.repo_path = repo_path
        self.language = language
        self.dependencies = dependencies

    def run(self) -> None:
        """
        Writes the extracted dependency data to .shed/dependencies.json
        """
        shed_dir = os.path.join(self.repo_path, ".shed")
        os.makedirs(shed_dir, exist_ok=True)

        output_path = os.path.join(shed_dir, "dependencies.json")

        data = {
            "language": self.language,
            "dependencies": self.dependencies
        }

        logging.info(f"💾 Writing extracted dependencies to {output_path}...")

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logging.info(f"✅ Dependencies successfully written to {output_path}.")
