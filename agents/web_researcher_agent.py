import os
import json
import logging
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables
load_dotenv()

class WebResearcherAgent:
    """
    An agent that verifies if dependencies are open-source and retrieves their license information.
    """

    def __init__(self, dependencies: list):
        self.dependencies = dependencies
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)
        self.web_search = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    def run(self) -> list:
        """
        Processes dependencies, checks if they are open-source, and fetches license information.
        """
        logging.info("🔍 Researching dependencies...")
        processed_dependencies = []

        for dep in self.dependencies:
            is_open_source = self._check_open_source(dep["package_name"])
            license_info = self._fetch_license_info(dep["package_name"]) if is_open_source else None

            processed_dependencies.append({
                "key": dep["key"],
                "package_name": dep["package_name"],
                "installed_version": dep["installed_version"],
                "is_transitive": dep["is_transitive"],
                "is_open_source": is_open_source,
                "license": license_info if license_info else {"name": "Unknown", "version": "Unknown", "url": None}
            })
        
        return processed_dependencies

    def _check_open_source(self, package_name: str) -> bool:
        """
        Checks if the given package is open-source by querying an LLM.
        """
        prompt = PromptTemplate.from_template(
            """
            Is the package "{package_name}" an open-source software library? 
            Respond with only 'true' or 'false'.
            """
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)
        raw_response = chain.invoke({"package_name": package_name})
        
        # 'raw_response' is a dict, so extract the text
        response_text = raw_response.get("text", "")
        response_text = response_text.strip().lower()

        # Return True if model output was literally 'true'
        return response_text == "true"


    def _fetch_license_info(self, package_name: str) -> dict:
        """
        Fetches license details using Tavily web search API.
        """
        logging.info(f"🌎 Searching for license info: {package_name}")
        search_query = f"{package_name} software license"
        search_results = self.web_search.search(query=search_query, num_results=3)
        
        # Extract license info from search results
        for result in search_results:
            if "license" in result["snippet"].lower():
                return {
                    "name": result.get("title", "Unknown"),
                    "version": "Unknown",  # Further processing needed
                    "url": result.get("url", None)
                }
        
        return {"name": "Unknown", "version": "Unknown", "url": None}

    def save_output(self, data: list, output_path: str) -> None:
        """
        Saves the processed dependency data as a JSON file.
        """
        logging.info(f"💾 Saving research results to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logging.info("✅ Research results saved.")
