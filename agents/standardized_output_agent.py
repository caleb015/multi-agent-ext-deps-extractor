import os
import json
import logging
import re
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from prompts.standardization_prompt import get_standardization_prompt  # ✅ Make sure it has input_variables=["dependencies"]

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
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0)

        # ✅ Load the prompt template (with input_variables=["dependencies"] in its definition)
        self.prompt_template = get_standardization_prompt()

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
        # logging.debug(f"🔍 Raw dependency input: {json.dumps(self.dependencies, indent=2)}")

        # Convert dependency data to JSON
        input_data = json.dumps(self.dependencies, indent=2)

        # ✅ Run LLM using the structured prompt
        chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
        response = chain.invoke({"dependencies": input_data})  # Pass the JSON string as 'dependencies'

        logging.debug(f"📨 LLM raw response before processing: {response}")

        try:
            # ✅ Strip markdown artifacts from LLM output (```json ... ```), if any
            response_text = response.get("text", "").strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()

            # logging.debug(f"📩 Cleaned LLM output: {response_text}")

            # ✅ Extract JSON array by locating first '[' and last ']'
            json_start = response_text.find("[")
            json_end = response_text.rfind("]")
            if json_start != -1 and json_end != -1:
                response_text = response_text[json_start : json_end + 1]

            # ✅ Ensure valid JSON structure before loading
            response_text = self._fix_json_issues(response_text)

            standardized_data = json.loads(response_text)

        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"❌ JSON Parsing Error: {e}")
            logging.error(f"🚨 Failed JSON Response: {response_text}")
            standardized_data = []

        return standardized_data

    def _fix_json_issues(self, json_text: str) -> str:
        """
        Fixes common JSON formatting issues from LLM responses.
        - Ensures lists are properly enclosed.
        - Removes unescaped quotes or misplaced commas.
        - Ensures "installed_versions" is always a list.
        """

        # ✅ Remove trailing commas before closing JSON lists or objects
        json_text = re.sub(r",\s*([\]}])", r"\\1", json_text)

        # ✅ Ensure `"installed_versions"` is always a list, not a string
        json_text = re.sub(
            r'"installed_versions":\s*"([^"]+)"',
            r'"installed_versions": ["\\1"]',
            json_text
        )

        return json_text

    def _write_output(self, data: list) -> None:
        """
        Writes the standardized dependency data to `.shed/dependencies.json`
        """
        shed_dir = os.path.join(self.repo_path, ".shed")
        os.makedirs(shed_dir, exist_ok=True)
        output_path = os.path.join(shed_dir, "dependencies.json")

        logging.info(f"💾 Writing standardized dependencies to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logging.info("✅ Dependencies successfully written to file.")
