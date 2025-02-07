# main.py

import argparse
import os
import sys
import logging
from agents.language_detection_agent import LanguageDetectionAgent
from agents.dependency_extraction_agent import DependencyExtractionAgent
from agents.standardized_output_agent import StandardizedOutputAgent

# Configure logging to print progress messages
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  
)

def orchestrate_workflow(repo_path: str) -> None:
    """
    Orchestrates the dependency extraction workflow with logging.
    """

    logging.info("🔍 Starting language detection...")
    detection_agent = LanguageDetectionAgent(repo_path)

    try:
        detection_output = detection_agent.run()  # => { "language": "xxx", "repoPath": "..." }
        logging.info(f"✅ Language detected: {detection_output['language']}")
    except Exception as e:
        logging.error(f"❌ Language detection failed: {str(e)}")
        sys.exit(1)

    # If no language is detected, stop execution
    if not detection_output.get("language"):
        logging.error("❌ No dominant language found. Exiting.")
        sys.exit(1)

    # Step 2: Dependency extraction
    logging.info(f"📦 Extracting dependencies for {detection_output['language']}...")
    extraction_agent = DependencyExtractionAgent(
        language=detection_output["language"],
        repo_path=detection_output["repoPath"]
    )

    try:
        extraction_output = extraction_agent.run()  # => { "dependencies": [...] }
        logging.info(f"✅ Extracted {len(extraction_output['dependencies'])} dependencies.")
    except Exception as e:
        logging.error(f"❌ Dependency extraction failed: {str(e)}")
        sys.exit(1)

    # Step 3: Standardized output
    logging.info("💾 Writing dependencies to JSON file...")
    output_agent = StandardizedOutputAgent(
        repo_path=detection_output["repoPath"],
        language=detection_output["language"],
        dependencies=extraction_output["dependencies"]
    )

    try:
        output_agent.run()
        logging.info("✅ Dependency extraction workflow completed successfully! 🎉")
    except Exception as e:
        logging.error(f"❌ Failed to write dependencies: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Dependency Extractor")
    parser.add_argument("repo_path", help="Path to the local Git repository.")
    args = parser.parse_args()

    repo_path = args.repo_path
    if not os.path.isdir(repo_path):
        logging.error(f"❌ Error: {repo_path} is not a valid directory.")
        sys.exit(1)

    try:
        logging.info(f"🚀 Running Dependency Extractor on {repo_path}...")
        orchestrate_workflow(repo_path)
    except Exception as e:
        logging.error(f"❌ Process halted due to error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
