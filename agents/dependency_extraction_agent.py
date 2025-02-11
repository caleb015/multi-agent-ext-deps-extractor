# agents/dependency_extraction_agent.py
import subprocess
import os
import json
import logging

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)

SUPPORTED_LANGUAGES = ["python", "javascript", "java"]  # Expand as needed

class DependencyExtractionAgent:
    """
    Executes dependency extraction commands in a Docker container that
    has all necessary tools installed (e.g., multi-agent-runtime image).
    
    This agent does not rely on the host having pip/npm/maven; everything
    is done inside Docker.
    """

    def __init__(self, language: str, repo_path: str, docker_image: str = "multi-agent-runtime"):
        """
        :param language: The detected language (e.g., 'python', 'javascript')
        :param repo_path: Absolute path to the local repository on the host
        :param docker_image: The Docker image name that has all the tools installed
        """
        self.language = language.lower()
        self.repo_path = os.path.abspath(repo_path)
        self.docker_image = docker_image

        # Ensure .shed directory exists
        self.shed_dir = os.path.join(self.repo_path, ".shed")
        os.makedirs(self.shed_dir, exist_ok=True)

        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"❌ Unsupported language {self.language}")

    def run(self):
        """
        Executes language-specific commands in a fresh Docker container.
        """
        logging.info(f"🐳 Running dependency extraction for {self.language} in Docker image '{self.docker_image}'...")

        if self.language == "python":
            return self._extract_python()
        elif self.language == "javascript":
            return self._extract_javascript()
        elif self.language == "java":
            return self._extract_java()
        else:
            # Should never happen if SUPPORTED_LANGUAGES is correct
            return {"dependencies": []}

    def _extract_python(self) -> dict:
        """
        Extract Python dependencies by mounting the repo at /app in a container 
        that has Python + pipdeptree.
        """
        logging.info("📦 Running Python dependency extraction with Docker...")

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            self.docker_image,
            "bash", "-c",
            (
                # Ensure pipdeptree is installed in the container
                "pip install --quiet pipdeptree && "
                # Attempt installing dependencies from requirements.txt if present
                "pip install --quiet -r requirements.txt || true && "
                # Then run pipdeptree, output JSON to .shed/deps.json
                "pipdeptree --json-tree > .shed/deps.json"
            )
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Log anything that came from the container
        if result.stdout:
            logging.info(f"[Docker STDOUT]\n{result.stdout}")
        if result.stderr:
            logging.warning(f"[Docker STDERR]\n{result.stderr}")

        if result.returncode != 0:
            logging.error("❌ Python dependency extraction command failed.")
            return {"dependencies": []}

        # Attempt to parse the newly created .shed/deps.json
        return self._parse_python_deps()


    def _parse_python_deps(self) -> dict:
        deps_json_path = os.path.join(self.shed_dir, "deps.json")
        if not os.path.exists(deps_json_path):
            logging.error("❌ deps.json file not found after Python extraction.")
            return {"dependencies": []}

        with open(deps_json_path, "r") as f:
            deps_raw = f.read()

        return {"dependencies": self._parse_pipdeptree(deps_raw)}

    def _parse_pipdeptree(self, deps_json: str):
        """
        Parses the JSON output from `pipdeptree` and extracts dependencies.
        Ensures correct transitivity marking and handles duplicate versions.
        """
        try:
            logging.debug(f"🔍 Raw pipdeptree JSON (first 500 chars): {deps_json[:500]}")
            data = json.loads(deps_json)

            if not isinstance(data, list):
                logging.error("❌ Unexpected JSON format from pipdeptree: expected a list.")
                return []

            # Flattened dependency list with unique keys
            dependency_map = {}

            def traverse_deps(dep_obj, is_transitive):
                """Recursively extract dependencies while tracking transitivity."""
                package_name = dep_obj.get("package_name") or dep_obj.get("key", "unknown")
                installed_version = dep_obj.get("installed_version", "unknown")
                key = package_name.lower()  # Normalize case

                # Ensure package is uniquely stored
                if key in dependency_map:
                    if installed_version not in dependency_map[key]["installed_versions"]:
                        dependency_map[key]["installed_versions"].append(installed_version)
                else:
                    dependency_map[key] = {
                        "key": key,
                        "package_name": package_name,
                        "installed_versions": [installed_version],
                        "is_transitive": is_transitive  # Set transitivity correctly
                    }

                # Process child dependencies
                for sub_dep in dep_obj.get("dependencies", []):
                    traverse_deps(sub_dep, is_transitive=True)  # Children are always transitive

            # Traverse each top-level dependency (non-transitive)
            for dep in data:
                traverse_deps(dep, is_transitive=False)

            # Convert map to sorted list
            result = sorted(dependency_map.values(), key=lambda x: x["package_name"])
            logging.info(f"✅ Extracted {len(result)} unique dependencies.")
            return result

        except json.JSONDecodeError:
            logging.error("❌ Failed to parse pipdeptree JSON output. Not valid JSON.")
            return []

    def _extract_javascript(self) -> dict:
        """
        Extract JavaScript dependencies in a container that has Node.js installed.
        """
        logging.info("📦 Running JavaScript dependency extraction with Docker...")

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            self.docker_image,
            "sh", "-c",
            (
                "npm install --quiet || true && "
                "npm list --json --all > .shed/npm-list.json"
            )
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"❌ JavaScript dependency extraction failed:\n{result.stderr}")
            return {"dependencies": []}

        return self._parse_js_deps()

    def _parse_js_deps(self) -> dict:
        npm_list_path = os.path.join(self.shed_dir, "npm-list.json")
        if not os.path.exists(npm_list_path):
            logging.error("❌ npm-list.json file not found after JS extraction.")
            return {"dependencies": []}

        with open(npm_list_path, "r") as f:
            npm_data = f.read()

        return {"dependencies": self._parse_npm_list(npm_data)}

    def _parse_npm_list(self, stdout: str) -> list:
        """
        Flatten the structure returned by 'npm list --json --all'.
        """
        try:
            data = json.loads(stdout)
            flattened = []

            def traverse(deps):
                for name, info in deps.items():
                    version = info.get("version", "unknown")
                    flattened.append({"name": name, "version": version})
                    if "dependencies" in info:
                        traverse(info["dependencies"])

            if "dependencies" in data:
                traverse(data["dependencies"])

            logging.info(f"✅ Extracted {len(flattened)} JavaScript dependencies.")
            return flattened
        except json.JSONDecodeError:
            logging.error("❌ Failed to parse npm JSON output.")
            return []

    def _extract_java(self) -> dict:
        """
        Extract Java dependencies in a container that has Maven installed.
        """
        logging.info("📦 Running Java dependency extraction with Docker...")

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.repo_path}:/app",
            "-w", "/app",
            self.docker_image,
            "mvn", "dependency:tree", "-DoutputType=tgf", "-DoutputFile=.shed/maven-deps.tgf"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"❌ Java dependency extraction failed:\n{result.stderr}")
            return {"dependencies": []}

        return self._parse_maven_deps()

    def _parse_maven_deps(self) -> dict:
        maven_output_path = os.path.join(self.shed_dir, "maven-deps.tgf")
        if not os.path.exists(maven_output_path):
            logging.error("❌ maven-deps.tgf not found after Java extraction.")
            return {"dependencies": []}

        with open(maven_output_path, "r") as f:
            maven_data = f.read()
        return {"dependencies": self._parse_maven_tree(maven_data)}

    def _parse_maven_tree(self, stdout: str) -> list:
        """
        The TGF output from Maven can be parsed or flattened here.
        """
        lines = stdout.strip().split("\n")
        flattened = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                flattened.append({"name": parts[1], "version": "unknown"})

        logging.info(f"✅ Extracted {len(flattened)} Java dependencies.")
        return flattened
