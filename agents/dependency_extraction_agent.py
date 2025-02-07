import subprocess
import shutil
import os
import json
import logging

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)

SUPPORTED_LANGUAGES = ["python", "javascript", "java"]  # Expand as needed

EXCLUDED_FOLDERS = {".venv", "venv", "node_modules", "target", "build", "__pycache__", "dist"}

class DependencyExtractionAgent:
    """
    Spins up a Docker container based on the detected language
    and retrieves all (including transitive) dependencies.
    """

    def __init__(self, language: str, repo_path: str):
        self.language = language.lower()
        self.repo_path = os.path.abspath(repo_path)

        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"❌ Unsupported language {self.language}")

    def run(self):
        """
        Executes language-specific Docker commands, returning a dict
        containing a list of dependencies and versions.
        """

        # ✅ Ensure we are NOT running inside an excluded directory
        for excluded in EXCLUDED_FOLDERS:
            if excluded in self.repo_path:
                logging.warning(f"⚠️ Skipping {self.repo_path} (excluded folder: {excluded})")
                return {"dependencies": []}

        logging.info(f"🐳 Running dependency extraction for {self.language}...")

        try:
            if self.language == "python":
                return self._extract_python()
            elif self.language == "javascript":
                return self._extract_javascript()
            elif self.language == "java":
                return self._extract_java()
            else:
                raise ValueError(f"❌ Unsupported language: {self.language}")
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Docker command failed: {e.stderr}")
            return {"dependencies": []}

    def _extract_python(self) -> dict:
        """
        Extracts Python dependencies using a Docker container.
        Reads dependencies from deps.json and ensures valid JSON output.
        """
        logging.info("📦 Running Python dependency extraction using pipdeptree...")

        # Set up the correct path for deps.json inside the mounted container
        deps_json_path = os.path.join(self.repo_path, "deps.json")

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            "python:3.9-slim",
            "bash", "-c",
            (
                "pip install --quiet pipdeptree && "
                "pip install --quiet -r requirements.txt || true && "
                "pipdeptree --json-tree > deps.json"
            )
        ]

        logging.info(f"🔹 Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        logging.debug(f"📝 Docker stdout: {result.stdout}")
        logging.debug(f"📝 Docker stderr: {result.stderr}")

        if result.returncode != 0:
            logging.error(f"❌ Python dependency extraction failed: {result.stderr}")
            return {"dependencies": []}

        # Read the deps.json file that was created in the repo
        try:
            with open(deps_json_path, "r") as f:
                deps_json = f.read()

            logging.info("✅ Successfully read deps.json file.")
            return {"dependencies": self._parse_pipdeptree(deps_json)}

        except FileNotFoundError:
            logging.error("❌ deps.json file not found.")
            return {"dependencies": []}

    def _parse_pipdeptree(self, deps_json: str):
        """
        Parses the JSON output from pipdeptree (version 2.25.0+) which has
        top-level 'key', 'package_name', 'installed_version', etc.

        Example structure:
        [
        {
            "key": "boto3",
            "package_name": "boto3",
            "installed_version": "1.36.15",
            "dependencies": [
            {
                "key": "...",
                "package_name": "...",
                "installed_version": "...",
                "dependencies": [...]
            }
            ]
        },
        ...
        ]
        """
        try:
            logging.debug(f"🔍 Raw pipdeptree output (first 500 chars): {deps_json[:500]}")
            data = json.loads(deps_json)

            if not isinstance(data, list):
                logging.error("❌ Unexpected JSON format from pipdeptree: expected a list of objects.")
                return []

            flattened = []

            def traverse_deps(dep_obj):
                """
                Recursively extract { name, version } from each dependency object.
                We rely on 'package_name' (fallback to 'key' if absent).
                """
                name = dep_obj.get("package_name") or dep_obj.get("key", "unknown")
                version = dep_obj.get("installed_version", "unknown")

                flattened.append({"name": name, "version": version})

                for sub_dep in dep_obj.get("dependencies", []):
                    traverse_deps(sub_dep)

            # Process top-level array
            for item in data:
                traverse_deps(item)

            logging.info(f"✅ Extracted {len(flattened)} dependencies.")
            return flattened

        except json.JSONDecodeError:
            logging.error("❌ Failed to parse pipdeptree JSON output. Not valid JSON.")
            return []


    def _extract_javascript(self) -> dict:
        """
        Extracts JavaScript dependencies using npm inside a Docker container.
        """
        logging.info("📦 Running JavaScript dependency extraction using npm list...")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            "node:16-alpine",
            "sh", "-c",
            (
                "npm install --quiet || true && "
                "npm list --json --all"
            )
        ]

        logging.info(f"🔹 Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        logging.debug(f"📝 Docker stdout: {result.stdout}")
        logging.debug(f"📝 Docker stderr: {result.stderr}")

        if result.returncode != 0:
            logging.error(f"❌ JavaScript dependency extraction failed: {result.stderr}")
            return {"dependencies": []}

        logging.info("✅ Successfully extracted JavaScript dependencies.")
        return {"dependencies": self._parse_npm_list(result.stdout)}

    def _parse_npm_list(self, stdout: str):
        """
        Parses JSON output from npm list.
        """
        try:
            data = json.loads(stdout)
            flattened = []

            def traverse_deps(deps):
                for name, info in deps.items():
                    version = info.get("version", "N/A")
                    flattened.append({"name": name, "version": version})
                    if "dependencies" in info:
                        traverse_deps(info["dependencies"])

            if "dependencies" in data:
                traverse_deps(data["dependencies"])

            return flattened
        except json.JSONDecodeError:
            logging.error("❌ Failed to parse npm JSON output.")
            return []

    def _extract_java(self) -> dict:
        """
        Extracts Java dependencies using Maven inside a Docker container.
        """
        logging.info("📦 Running Java dependency extraction using mvn dependency:tree...")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            "maven:3.8.5-openjdk-17",
            "mvn", "dependency:tree", "-DoutputType=tgf"
        ]

        logging.info(f"🔹 Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        logging.debug(f"📝 Docker stdout: {result.stdout}")
        logging.debug(f"📝 Docker stderr: {result.stderr}")

        if result.returncode != 0:
            logging.error(f"❌ Java dependency extraction failed: {result.stderr}")
            return {"dependencies": []}

        logging.info("✅ Successfully extracted Java dependencies.")
        return {"dependencies": self._parse_maven_tree(result.stdout)}

    def _parse_maven_tree(self, stdout: str):
        """
        Parses TGF output from Maven dependency tree.
        """
        lines = stdout.strip().split("\n")
        flattened = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                flattened.append({"name": parts[1], "version": "unknown"})

        return flattened
