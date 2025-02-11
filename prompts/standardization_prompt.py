from langchain.prompts import PromptTemplate

def get_standardization_prompt() -> PromptTemplate:
    """
    Returns the prompt template for standardizing dependency extraction.
    This version uses parentheses instead of braces in the sample, so there are no curly braces.
    """
    return PromptTemplate(
        template="""
        **Task**:
        You are given a list of extracted dependencies from a software project. 
        Your job is to **standardize** the dependencies into a structured JSON format.

        ---

        **Input Data Format (Example)**:
        ```json
        [
            (
                "package_name": "boto3",
                "installed_version": "1.36.17",
                "dependencies": [
                    (
                        "package_name": "botocore",
                        "installed_version": "1.36.17",
                        "dependencies": [
                            ("package_name": "urllib3", "installed_version": "2.3.0")
                        ]
                    )
                ]
            ),
            (
                "package_name": "GitPython",
                "installed_version": "3.1.44",
                "dependencies": []
            )
        ]
        ```

        ---

        **Standardized Output Format (JSON Array)**:
        - Each **dependency** must be a **unique entry** based on:
        - `key`: A **unique identifier** for the package.
        - `package_name`: The **name** of the package.
        - `installed_versions`: A **list** of installed versions, grouped under the same package.
        - `is_transitive`: `true` if the package appears inside any "dependencies" array.

        ---

        **Expected Output Example**:
        ```json
        [
            (
                "key": "boto3",
                "package_name": "boto3",
                "installed_versions": ["1.36.17"],
                "is_transitive": false
            ),
            (
                "key": "botocore",
                "package_name": "botocore",
                "installed_versions": ["1.36.17"],
                "is_transitive": true
            ),
            (
                "key": "urllib3",
                "package_name": "urllib3",
                "installed_versions": ["2.3.0", "1.26.15"],
                "is_transitive": true
            )
        ]
        ```

        ---

        **Rules for Standardization**:
        1. **Ensure Uniqueness**:  
        - A combination of **`key`** and **`package_name`** must be unique.
        - If a package has **multiple versions**, they should be grouped into "installed_versions" as a list.

        2. **Set `is_transitive` Correctly**:  
        - If a package appears in a "dependencies" list, **mark `is_transitive: true`**.
        - If it is a **top-level** dependency, **mark `is_transitive: false`**.

        3. **Output Requirements**:  
        - **MUST** return **only valid JSON** (no markdown, no extra text).  
        - **MUST NOT** include explanations or formatting instructions.  
        - **MUST NOT** include the original "dependencies" list.  
        - Each package **must** have `key`, `package_name`, `installed_versions`, and `is_transitive`.

        ---

        **Important**:  
        - Your response must be **only** a valid JSON array.
        - Do **not** include markdown (` ``` `), explanations, or additional formatting.

        ---

        Here are the extracted dependencies: {dependencies}
        """,
        input_variables=["dependencies"],
        template_format="f-string",
        validate_template=False
    )
