# Multi-Agent Dependency Extractor

## Overview

The Multi-Agent Dependency Extractor is a tool designed to automate the process of detecting, extracting, and documenting open-source dependencies in a software project. It leverages multiple agents to perform tasks such as language detection, dependency extraction, and open-source license research.

## Features

- **Language Detection**: Automatically detects the programming language of the project.
- **Dependency Extraction**: Extracts dependencies using Docker containers.
- **Standardized Output**: Formats the extracted dependencies into a standardized format.
- **Open Source Research**: Researches the open-source status and licenses of dependencies.
- **Document Generation**: Generates a DOCX document detailing the open-source components and their licenses.

## Output Documents

The Multi-Agent Dependency Extractor generates several key output documents during its workflow:

1. **Open Source Declaration Document (DOCX)**:
   - This document provides a detailed overview of the open-source components used in your application.
   - It includes the names of the components, their licenses, and any relevant URLs for obtaining the source code.
   - The document is generated in DOCX format and is saved in the `.shed` directory within your repository.

2. **Open Source Dependencies JSON**:
   - A JSON file named `open_source_dependencies.json` is created, containing detailed information about each dependency.
   - This file includes data such as the package name, installed versions, whether the dependency is transitive, and its open-source status.
   - This JSON file is also stored in the `.shed` directory.

These documents are essential for maintaining compliance with open-source licenses and for providing transparency about the software components used in your project.

## Prerequisites

- Docker must be installed and running on your system.
- Python 3 and pip must be installed.
- Node.js and npm are required for some operations.
- Ensure you have a `.env` file with the following variables:
  - `COMPANY_NAME`: Your company's name.
  - `COMPANY_EMAIL`: Contact email for your company.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Build the Docker image:
   ```bash
   docker build -t multi-agent-runtime -f Dockerfiles/unified.Dockerfile .
   ```

## Usage

Run the application using the following command:

```bash
python main.py <repo_path> <app_name>
```

- `<repo_path>`: Path to the local Git repository.
- `<app_name>`: Name of the application.

## Workflow

1. **Check Docker**: Ensures Docker is running.
2. **Build Docker Image**: Builds the necessary Docker image if not already built.
3. **Language Detection**: Detects the programming language of the repository.
4. **Dependency Extraction**: Extracts dependencies using the detected language.
5. **Standardized Output**: Formats the extracted dependencies.
6. **Open Source Research**: Researches open-source licenses and statuses.
7. **Document Generation**: Generates a DOCX document with the open-source declaration.

