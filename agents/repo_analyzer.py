import os
import shutil
import time 
import tempfile 
import logging # NEW
from git import Repo, GitCommandError 
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter 

logger = logging.getLogger("RepoAnalyzer") 

class RepoAnalyzerAgent:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        self.working_dir = "" 
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )

    def _clone_repo(self):
        """Clones the repository into a temporary working directory."""
        # Use OS temp folder for robust permissions
        self.working_dir = tempfile.mkdtemp(prefix="repo_clone_")
        
        logger.info(f"Cloning starting. Target: {self.repo_url}. Temp Dir: {self.working_dir}")
        
        try:
            Repo.clone_from(self.repo_url, self.working_dir)
            logger.info("Cloning successful.")
        except GitCommandError as e:
            logger.error(f"Git Clone Command Failed: {e}")
            # Raise exception with generic error message for security/simplicity
            raise RuntimeError(f"Git Clone Failed (Status: {e.status}).") from e
        except Exception as e:
            logger.error(f"Cloning failed due to unknown error: {e}")
            raise RuntimeError(f"Cloning failed: {e}") from e


    def _load_and_split_files(self):
        """Loads and splits content from README and other key files."""
        docs = []
        file_paths = ["README.md", "main.py", "requirements.txt"]
        
        for file in file_paths:
            full_path = os.path.join(self.working_dir, file)
            if os.path.exists(full_path):
                logger.debug(f"Loading {file}...")
                try:
                    loader = TextLoader(full_path, encoding='utf-8')
                    docs.extend(loader.load())
                except Exception as e:
                    logger.warning(f"Could not load {file}: {e}")
        
        chunks = self.text_splitter.split_documents(docs)
        logger.info(f"Total content split into {len(chunks)} chunks.")
        return chunks

    def process_repo(self):
        """Main method to clone, read, and process the repository, ensuring cleanup."""
        temp_dir = ""
        try:
            self._clone_repo()
            temp_dir = self.working_dir 
            time.sleep(0.5) 
            chunks = self._load_and_split_files()
            
            # --- Cleanup the temporary directory (CRITICAL) ---
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"Cleaned up temporary directory {temp_dir}")
            
            return chunks
        except Exception as e:
            logger.critical(f"REPO ANALYZER FAILED. Cleaning up. Error: {e}")
            if os.path.exists(temp_dir):
                 shutil.rmtree(temp_dir, ignore_errors=True)
            raise e 

    def create_retriever(self, chunks):
        """Creates and returns a FAISS-based retriever from the document chunks."""
        try:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            embeddings_model = HuggingFaceEmbeddings(model_name=model_name)
            
            vectorstore = FAISS.from_documents(chunks, embeddings_model)
            retriever = vectorstore.as_retriever()
            logger.info("Retriever created successfully.")
            return retriever
        except Exception as e:
             logger.error(f"EMBEDDING/RETRIEVER FAILED: {e}")
             raise RuntimeError("Failed to initialize embeddings model or retriever.") from e