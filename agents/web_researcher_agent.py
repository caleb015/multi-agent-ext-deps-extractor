import json
import logging
import re
from langchain_community.chat_models import ChatOpenAI
from dotenv import load_dotenv
from langchain.agents import initialize_agent
from langchain.tools import TavilySearchResults
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Configure logging to store logs in a file
LOG_FILE = "web_researcher_agent.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)

def _clean_llm_response(response_text: str) -> str:
    """Cleans LLM response by stripping markdown artifacts and extracting JSON content."""
    response_text = response_text.strip()
    
    # Remove markdown formatting (```json ... ```)
    response_text = re.sub(r"```json\s*", "", response_text)
    response_text = re.sub(r"```", "", response_text)
    
    return response_text

class WebResearcherAgent:
    """
    An agent that verifies if dependencies are open-source and retrieves their license information.
    """

    def __init__(self, dependencies: list):
        self.dependencies = dependencies
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)
        self.search_tool = TavilySearchResults()
        
        # Initialize agent with Tavily as a tool
        self.agent = initialize_agent(
            tools=[self.search_tool],
            llm=self.llm,
            agent="zero-shot-react-description",
            verbose=True
        )

    def run(self) -> list:
        """
        Processes dependencies in batches, checks if they are open-source, and fetches license information.
        """
        logging.info("🔍 Researching dependencies...")
        logging.info(f"Total number of dependencies to be researched: {len(self.dependencies)}")
        processed_dependencies = []

        # Define batch size
        batch_size = 10  # Adjust this number based on your needs and system capabilities

        # Process dependencies in batches
        with ThreadPoolExecutor() as executor:
            for i in range(0, len(self.dependencies), batch_size):
                batch = self.dependencies[i:i + batch_size]
                results = list(executor.map(self._research_dependency, [dep["package_name"] for dep in batch]))
                
                for dep, research_data in zip(batch, results):
                    processed_dependencies.append({
                        "key": dep["key"],
                        "package_name": dep["package_name"],
                        "installed_versions": dep["installed_versions"],
                        "is_transitive": dep["is_transitive"],
                        "is_open_source": research_data.get("is_open_source", False),
                        "license": research_data.get("license", {"name": "Unknown", "version": "Unknown", "url": None})
                    })

        return processed_dependencies

    def _research_dependency(self, package_name: str) -> dict:
        """
        Uses LLM with Tavily as a tool to determine if a package is open-source and extract its license.
        """
        logging.info(f"🌎 Researching: {package_name}")
        
        research_prompt = (
            "Analyze the given package name and determine:"
            "\n- Whether it is open-source (respond with true or false)."
            "\n- The software license (SPDX identifier if available, else a recognized name)."
            "\n- A URL to the official license page if available."
            "\n\nUse the WebSearch tool to search for relevant information about the package."
            "\nRespond in JSON format:"
            "```json"
            "{"
            "  \"is_open_source\": <true/false>,"
            "  \"license\": {"
            "    \"name\": \"<Extracted License Name or SPDX>\","
            "    \"url\": \"<License URL if available>\""
            "  }"
            "}"
            "```"
        )
        
        response = self.agent.run(f"{research_prompt}\nPackage Name: {package_name}")
        logging.debug(f"LLM Research Response ({package_name}): {response}")
        
        try:
            cleaned_response = _clean_llm_response(response)
            parsed_response = json.loads(cleaned_response)
            return parsed_response
        except json.JSONDecodeError:
            logging.error(f"❌ Failed to parse LLM response for {package_name}: {cleaned_response}")
            return {
                "is_open_source": False,
                "license": {
                    "name": "AI failed to find the license",
                    "url": None
                }
            }

    def save_output(self, data: list, output_path: str) -> None:
        """
        Saves the processed dependency data as a JSON file.
        """
        logging.info(f"💾 Saving research results to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logging.info("✅ Research results saved.")
