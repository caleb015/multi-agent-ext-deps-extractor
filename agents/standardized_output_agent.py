import os
import json
import logging
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

class StandardizedOutputAgent:
    """
    Takes in extracted dependency data and consolidates it using an LLM.
    Writes output to `.shed/dependencies.json`.
    """

    def __init__(self, repo_path: str, language: str, dependencies: list, use_chat_model=True):
        self.repo_path = repo_path
        self.language = language
        self.dependencies = dependencies
        self.use_chat_model = use_chat_model
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)  # Using correct API

    def run(self) -> None:
        """
        Consolidates and writes dependency data to `.shed/dependencies.json`
        """
        standardized_dependencies = self._process_with_llm()
        self._write_output(standardized_dependencies)

    def _process_with_llm(self) -> list:
        """
        Uses an LLM to consolidate dependencies into a structured format.
        """
        logging.info("🤖 Processing dependencies with LLM for standardization...")
        logging.debug(f"🔍 Raw dependency input: {json.dumps(self.dependencies, indent=2)}")

        input_data = json.dumps(self.dependencies, indent=2)
        prompt_template = PromptTemplate.from_template(
            """
            Given the following extracted dependencies:
            {dependencies}
            
            Consolidate them into a structured JSON format with:
            - Unique (key, package_name, installed_version)
            - 'is_transitive' = True if the package appears inside any 'dependencies': [] list in the hierarchy
            
            Return a valid JSON list only, no extra text.
            """
        )

        chain = LLMChain(llm=self.llm, prompt=prompt_template)
        response = chain.invoke({"dependencies": input_data})
        
        logging.debug(f"📨 LLM raw response: {response}")
        
        if isinstance(response, dict) and "text" in response:
            response_text = response["text"].strip()
            logging.debug(f"📩 Processed LLM output: {response_text}")
        else:
            logging.error("❌ Unexpected LLM response format.")
            return []
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logging.error("❌ Failed to parse LLM response into JSON.")
            return []

    def _write_output(self, data: list) -> None:
        """
        Writes the standardized dependency data to `.shed/dependencies.json`
        """
        shed_dir = os.path.join(self.repo_path, ".shed")
        os.makedirs(shed_dir, exist_ok=True)
        output_path = os.path.join(shed_dir, "dependencies.json")

        logging.info(f"💾 Writing standardized dependencies to {output_path}...")
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logging.info("✅ Dependencies successfully written to file.")
