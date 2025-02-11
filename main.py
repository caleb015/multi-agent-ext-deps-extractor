import argparse
import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

from agents.language_detection_agent import LanguageDetectionAgent
from agents.dependency_extraction_agent import DependencyExtractionAgent
from agents.standardized_output_agent import StandardizedOutputAgent
from agents.web_researcher_agent import WebResearcherAgent  

# Load environment variables from .env
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "Dockerfiles", "unified.Dockerfile")
IMAGE_NAME = "multi-agent-runtime"


def check_docker_running():
    """Check if Docker is running; if not, prompt user and exit."""
    try:
        subprocess.run(
            ["docker", "info"], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            check=True
        )
        logging.info("✅ Docker is running.")
    except subprocess.CalledProcessError:
        logging.error("❌ Docker is not running. Please start Docker and try again.")
        sys.exit(1)


def check_and_build_docker_image():
    """Check if the Docker image exists; build it if not."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", IMAGE_NAME],
            capture_output=True,
            text=True,
            check=True
        )

        if not result.stdout.strip():
            logging.info(f"🔎 Docker image '{IMAGE_NAME}' not found. Building...")
            build_docker_image()
        else:
            logging.info(f"✅ Docker image '{IMAGE_NAME}' found.")

    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Error checking Docker images: {e}")
        sys.exit(1)


def build_docker_image():
    """Build the Docker image from the provided Dockerfile."""
    if not os.path.exists(DOCKERFILE_PATH):
        logging.error(f"❌ Dockerfile not found at {DOCKERFILE_PATH}. Please check your setup.")
        sys.exit(1)

    try:
        subprocess.run(
            ["docker", "build", "-t", IMAGE_NAME, "-f", DOCKERFILE_PATH, PROJECT_ROOT],
            check=True
        )
        logging.info(f"✅ Successfully built Docker image '{IMAGE_NAME}'.")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Failed to build Docker image: {e}")
        sys.exit(1)


def orchestrate_workflow(repo_path: str) -> None:
    """Orchestrates the multi-agent dependency extraction workflow."""
    logging.info("🚀 Starting Dependency Extraction...")

    # 1️⃣ Check Docker is running
    check_docker_running()

    # 2️⃣ Ensure Docker image is built
    check_and_build_docker_image()

    # 3️⃣ Detect language
    logging.info("🔍 Detecting language...")
    try:
        detection_agent = LanguageDetectionAgent(repo_path)
        detection_output = detection_agent.run()
        language = detection_output["language"]
        logging.info(f"✅ Detected language: {language}")
    except Exception as e:
        logging.error(f"❌ Language detection failed: {e}")
        sys.exit(1)

    # 4️⃣ Dependency extraction
    logging.info(f"📦 Extracting dependencies for {language} using Docker...")
    try:
        extraction_agent = DependencyExtractionAgent(language, repo_path, docker_image=IMAGE_NAME)
        extraction_result = extraction_agent.run()
        # logging.debug(f"⚙️ Extraction result object: {extraction_result}")
    except Exception as e:
        logging.error(f"❌ Dependency extraction error: {e}")
        sys.exit(1)

    # 5️⃣ Standardized Output Agent
    logging.info("📑 Standardizing extracted dependencies with LLM...")
    try:
        output_agent = StandardizedOutputAgent(repo_path, language, extraction_result["dependencies"])
        output_agent.run()
    except Exception as e:
        logging.error(f"❌ Standardization failed: {e}")
        sys.exit(1)

    # 6️⃣ Web Researcher Agent
    logging.info("🌎 Researching open-source status and licenses...")
    try:
        researcher_agent = WebResearcherAgent(extraction_result["dependencies"])
        researched_dependencies = researcher_agent.run()
        output_path = os.path.join(repo_path, ".shed", "open_source_dependencies.json")
        researcher_agent.save_output(researched_dependencies, output_path)
    except Exception as e:
        logging.error(f"❌ Web Researcher Agent failed: {e}")
        sys.exit(1)

    logging.info("✅ Workflow complete.")


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Dependency Extractor")
    parser.add_argument("repo_path", help="Path to the local Git repository.")
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(repo_path):
        logging.error(f"❌ Error: {repo_path} is not a valid directory.")
        sys.exit(1)

    try:
        orchestrate_workflow(repo_path)
    except Exception as e:
        logging.error(f"❌ Process halted due to error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
