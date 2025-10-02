# 🚀 GitHub Repo Improver Agent: Production-Ready Capstone

## Project Overview

The **GitHub Repo Improver Agent** application automatically analyzes a public GitHub repository and generates structured, actionable suggestions for improving documentation, discoverability, and project clarity.

---

## 🛠️ Module 3 Professional Enhancements

This system is enhanced with features required for operational excellence, security, and quality assurance:

| Feature | Implementation | Module 3 Requirement |
| :--- | :--- | :--- |
| **Resilience** | **Retry Logic with Exponential Backoff** (in `ContentImproverAgent`) to prevent failure from transient LLM API network errors. | **Operational Excellence** |
| **Guardrails** | **Input Validation** (regex check on URL format in `app.py`) and **Secure Environment Handling** (`.gitignore`). | **Security & Safety** |
| **Quality Assurance** | **Comprehensive Testing Suite** (`tests/test_agents.py`) including Unit and Integration Tests for core functionality. | **Test Coverage (70%+)** |
| **UX Improvement** | Streamlit UI (`app.py`) enhanced with clear logging and graceful handling of agent failures. | **User Interface** |

---

## 🧠 System Architecture and Agent Flow

The system utilizes a sequential **LangGraph** pipeline for controlled collaboration.

| Agent | Core Task | Required Tools |
| :--- | :--- | :--- |
| **1. RepoAnalyzerAgent** | **Repository Preparation.** Clones the public target repo (using OS temporary directory to avoid permissions issues), performs **Text Chunking**, and initializes the RAG Retriever. | **Repo Reader** (`gitpython`), **RAG Retriever** (`FAISS`). |
| **2. MetadataRecommenderAgent** | **Keyword & Tag Extraction.** Identifies key topics and technical terms. | **Keyword Extractor** (`nltk`). |
| **3. ContentImproverAgent** | **Structured Generation.** Synthesizes suggestions, enforcing a Pydantic structure, with built-in **Retry Logic** for API stability. | **LLM API** (OpenRouter/GPT-4o Mini). |

---

## ⚙️ Technical Specifications

### I. Setup and Installation Instructions

1.  **Prerequisites:** Ensure **Python 3.10+** and the **Git Command-Line Tool** are installed.

2.  **Clone the Repository** and install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Secure Configuration:** Create a **`.env`** file for your `OPENROUTER_API_KEY`. (The repository's `.gitignore` automatically prevents this file from being pushed.)

4.  **NLTK Data:** Download required NLP resources:

    ```bash
    python -c "import nltk; nltk.download('stopwords')"
    ```

### II. RAG and Quality Assurance

| Setting | Value | Rationale |
| :--- | :--- | :--- |
| **Test Coverage** | **70%+** | Achieved via Unit and Integration tests in the `tests/` directory. |
| **Text Chunk Size** | `1000` | Maintains contextual integrity for code and documentation. |
| **Text Chunk Overlap** | `200` | Ensures semantic continuity for RAG retrieval. |
| **Embedding Model** | `HuggingFaceEmbeddings(all-MiniLM-L6-v2)` | Fast, local embedding for efficient RAG index creation. |

### III. Running the System

1.  **Launch the App:** Run the Streamlit UI (use Administrator mode for best results):

    ```bash
    python -m streamlit run app.py
    ```

2.  **Run Tests (Verification):** To verify core functionality and resilience:

    ```bash
    python -m unittest tests.test_agents
    ```
