import os
import json
import logging 
import time    
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field, ValidationError 

logger = logging.getLogger("ContentImprover")

# --- Structured Output Schema (Pydantic) ---
class ContentSuggestions(BaseModel):
    """Structured output model for repository content suggestions."""
    new_title: str = Field(description="A short, attention-grabbing title (max 10 words).")
    short_summary: str = Field(description="A compelling, one-paragraph summary (max 80 words).")
    readme_edits: list[str] = Field(description="A list of 3-5 concrete, actionable suggestions.")

class ContentImproverAgent:
    MAX_RETRIES = 3 # Operational Resilience Parameter

    def __init__(self, retriever):
        # Targeting GPT-4o Mini for stability
        # --- CRITICAL ADDITION: EXPLICIT TIMEOUT MANAGEMENT ---
        self.llm = ChatOpenAI(
            model="openai/gpt-4o-mini",  
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.0, 
            request_timeout=30.0 # Ensures compliance with Timeout Management requirement
        )
        self.retriever = retriever

    def generate_improved_content(self, original_content: str, metadata: dict):
        """Generates structured improved content with retry logic."""
        
        # RAG Context retrieval (rest of the logic remains the same)
        retrieved_docs = self.retriever.invoke("summarize the repository and identify missing documentation sections")
        retrieved_context = "\n---\n".join([doc.page_content for doc in retrieved_docs])
        
        prompt_template = PromptTemplate(
            template="""You are an expert GitHub repository analyst. The output must strictly adhere to the provided JSON schema.
            
            REPOSITORY METADATA & CONTEXT: {context}
            ORIGINAL CONTENT: {original_content}
            EXTRACTED METADATA: {metadata}
            
            Based on the information, generate the required structured response.
            """,
            input_variables=["context", "original_content", "metadata"]
        )

        full_prompt = prompt_template.invoke({
            "context": retrieved_context,
            "original_content": original_content,
            "metadata": json.dumps(metadata, indent=2)
        })

        # --- RESILIENCE: Retry Logic with Exponential Backoff ---
        for attempt in range(self.MAX_RETRIES):
            try:
                # Enforce Pydantic Output
                structured_llm = self.llm.with_structured_output(ContentSuggestions)
                
                logger.info(f"Attempt {attempt + 1}/{self.MAX_RETRIES} to invoke LLM.")
                response = structured_llm.invoke(full_prompt.text)
                
                logger.info("LLM invocation successful.")
                return response.dict()
            
            except ValidationError as e:
                # Agent failure due to bad JSON structure
                logger.error(f"Validation failed (Attempt {attempt + 1}): Invalid structured output. Error: {e}")
                raise RuntimeError("LLM provided invalid structured output.") from e
            except Exception as e:
                # Handle API/Network issues (the core resilience logic)
                logger.warning(f"LLM API/Network failure (Attempt {attempt + 1}): {e}")
                
                if attempt + 1 == self.MAX_RETRIES:
                    logger.error("Max retries reached. LLM generation failed permanently.")
                    raise RuntimeError("Max retries reached for LLM generation.") from e
                
                # Exponential Backoff
                wait_time = (2 ** attempt) + 1 
                logger.info(f"Waiting {wait_time} seconds before retry.")
                time.sleep(wait_time)

        return {"error": "LLM generation failed after all retries."}