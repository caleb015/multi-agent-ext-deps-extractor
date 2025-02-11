import os
import logging
from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound

EXCLUDED_FOLDERS = {".venv", "venv", "node_modules", "target", "build", "__pycache__", "dist"}

class LanguageDetectionAgent:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def run(self):
        logging.info(f"🔎 Scanning repository: {self.repo_path}")

        file_extensions = []
        for root, _, files in os.walk(self.repo_path):
            # ✅ Skip excluded directories
            if any(excluded in root for excluded in EXCLUDED_FOLDERS):
                continue

            for file in files:
                ext = os.path.splitext(file)[-1].lower()
                if ext and ext not in {".sample", ".dockerfile"}:  # Exclude unrecognized extensions
                    file_extensions.append(ext)

        if not file_extensions:
            logging.error("❌ No source code files found in the repository.")
            raise ValueError("No code files found.")

        logging.info(f"📂 Found {len(file_extensions)} files, trying to determine language...")

        language_guesses = []
        for ext in file_extensions:
            try:
                lexer = get_lexer_for_filename(f"dummy{ext}")
                language_guesses.append(lexer.name)
            except ClassNotFound:
                logging.warning(f"⚠️ No lexer found for extension {ext}")

        if not language_guesses:
            logging.error("❌ Could not determine language.")
            raise ValueError("Language detection failed.")

        dominant_language = max(set(language_guesses), key=language_guesses.count)
        logging.info(f"✅ Detected language: {dominant_language}")

        return {"language": dominant_language.lower(), "repoPath": self.repo_path}
