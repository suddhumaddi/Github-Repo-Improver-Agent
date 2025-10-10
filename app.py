import streamlit as st
import json
import os
import time
import logging # NEW: For operational excellence
import re      # NEW: For input validation
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
# Insert this import line at the top of your file with the other imports
from tools.health_check import check_openrouter_api_health

# Import Agents
from agents.repo_analyzer import RepoAnalyzerAgent
from agents.metadata_recommender import MetadataRecommenderAgent
from agents.content_improver import ContentImproverAgent

# --- LOGGING CONFIGURATION (Module 3 Requirement) ---
# Directs logs to the console where Streamlit is running
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- AGENT AND GRAPH LOGIC ---

class AgentState(TypedDict):
    """Represents the shared state passed between agents."""
    repo_url: str
    original_content: str
    chunks: list
    retriever: object
    metadata: dict
    improved_content: dict

# Define the agent nodes (functions)
def analyze_repo_node(state: AgentState):
    logger.info(f"Starting analyze_repo_node for URL: {state['repo_url']}")
    st.info("Agent 1: Analyzing repository structure and creating RAG index...")
    repo_url = state['repo_url']
    agent = RepoAnalyzerAgent(repo_url)
    
    try:
        chunks = agent.process_repo()
    except Exception as e:
        logger.error(f"Agent 1 FAILED during processing: {e}")
        st.error(f"Cloning/Analysis Error: See terminal logs for details on Git or permissions issues.")
        # Raise an exception to stop the LangGraph workflow immediately
        raise ValueError("RepoAnalyzer failed.") 
        
    if not chunks:
        logger.error("Agent 1 FAILED: No content processed.")
        st.error("RepoAnalyzer failed to process any content. Stopping workflow.")
        raise ValueError("RepoAnalyzer failed.")

    retriever = agent.create_retriever(chunks)
    full_content = "\n\n".join([c.page_content for c in chunks])
    st.success("Analysis Complete. RAG index created.")
    logger.info("Agent 1 completed successfully.")
    
    return {
        "original_content": full_content,
        "chunks": chunks,
        "retriever": retriever,
    }

def recommend_metadata_node(state: AgentState):
    logger.info("Starting recommend_metadata_node.")
    st.info("Agent 2: Extracting keywords and suggesting metadata...")
    
    try:
        original_content = state['original_content']
        agent = MetadataRecommenderAgent()
        metadata = agent.suggest_metadata(original_content)
        st.success("Metadata extraction complete.")
        logger.info("Agent 2 completed successfully.")
        return {"metadata": metadata}
    except Exception as e:
        # Graceful Degradation: Log failure but pass empty metadata to Agent 3
        logger.warning(f"Agent 2 FAILED: Keyword extraction failed. Passing empty metadata. Error: {e}")
        st.warning("Keyword extraction failed, continuing with no metadata (Graceful Degradation).")
        return {"metadata": { "keywords": [], "tags": [], "categories": [], "badges_to_add": []}}


def improve_content_node(state: AgentState):
    logger.info("Starting improve_content_node.")
    st.info("Agent 3: Generating new content and README edits using OpenRouter LLM...")
    
    try:
        original_content = state['original_content']
        metadata = state['metadata']
        retriever = state['retriever']
        
        agent = ContentImproverAgent(retriever)
        improved_content = agent.generate_improved_content(original_content, metadata)
        
        st.success("Content generation complete.")
        logger.info("Agent 3 completed successfully.")
        return {"improved_content": improved_content}
    except Exception as e:
        logger.error(f"Agent 3 FAILED during LLM generation. Error: {e}")
        st.error(f"Content generation failed due to LLM error. See terminal logs for retry attempts.")
        # Return a structured error response for the UI
        return {"improved_content": {"error": f"LLM generation failed after retries. Details: {e}"}}


def create_graph():
    """Defines and compiles the sequential LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze_repo", analyze_repo_node)
    workflow.add_node("recommend_metadata", recommend_metadata_node)
    workflow.add_node("improve_content", improve_content_node)

    workflow.add_edge(START, "analyze_repo")
    workflow.add_edge("analyze_repo", "recommend_metadata")
    workflow.add_edge("recommend_metadata", "improve_content")
    workflow.add_edge("improve_content", END)

    return workflow.compile()
# --- END AGENT AND GRAPH LOGIC ---


# --- STREAMLIT UI DEFINITION ---
def main():
    st.set_page_config(page_title="Gen-Authoring: Repo Improver", layout="wide")
    
    st.title("📚 Gen-Authoring: AI-Powered Repo Improvement (Production-Ready)")
    st.markdown("An automated multi-agent system enhanced with **resilience and logging** for real-world use.")
    st.markdown("---")

    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        st.error("FATAL ERROR: OPENROUTER_API_KEY is not set in the .env file.")
        logger.critical("API Key not found. System terminated.")
        return

    st.sidebar.title("System Configuration")
    st.sidebar.markdown(f"**LLM Provider:** OpenRouter (GPT-4o-Mini)")
    st.sidebar.markdown(f"**Embedding Model:** HuggingFace MiniLM")
    st.sidebar.markdown(f"**Orchestration:** LangGraph (3 Agents)")
    
    st.header("1. Project Setup")
    
    repo_url = st.text_input(
        "GitHub Repository URL", 
        value="https://github.com/justin-hu/micro-repo-for-testing",
        placeholder="https://github.com/username/repository-name",
        help="Paste a public GitHub URL here. Ensure Git is installed and the URL is valid."
    )
    
    if st.button("🚀 Start Analysis", type="primary"):
        # --- INPUT VALIDATION (NEW GUARDRAIL) ---
        github_url_pattern = r"^https?://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$"
        if not re.match(github_url_pattern, repo_url):
            st.error("Input Error: Please enter a valid GitHub repository URL format.")
            logger.warning(f"Input validation failed for URL: {repo_url}")
            return
        
        st.subheader("2. Agent Workflow Execution")
        
        app = create_graph()
        inputs = {"repo_url": repo_url}
        
        start_time = time.time()
        status_container = st.container()
        
        try:
            final_state = app.invoke(inputs)

            status_container.success("All Agents Completed Successfully!")
            st.markdown("---")
            st.subheader("3. Final Suggestions (UX Improvement)")
            
            results = final_state.get('improved_content', {})
            metadata = final_state.get('metadata', {})
            
            # --- OUTPUT RENDERING WITH GRACEFUL ERROR DISPLAY ---
            
            if 'error' in results:
                st.error(f"Final generation failed: {results['error']}")
                logger.error("Final output rendering failed due to generation error.")
            else:
                with st.expander("Suggested Metadata & Tags"):
                    st.json(metadata)

                st.markdown("### 🌟 Repository Core Content")
                st.markdown(f"**New Title Suggestion:**")
                st.code(results.get('new_title', 'N/A'), language='markdown')
                
                st.markdown(f"**Short Summary (Repo Description):**")
                st.markdown(f"> *{results.get('short_summary', 'N/A')}*")

                st.markdown("### 📝 Actionable README Edits")
                edits = results.get('readme_edits', [])
                
                if isinstance(edits, list) and edits:
                    st.success("Improvements suggested:")
                    for i, edit in enumerate(edits):
                        st.markdown(f"**{i+1}.** {edit}")
                else:
                    st.warning("Could not retrieve actionable edit list. Check LLM output in logs.")
            
            logger.info(f"Total workflow completed in {time.time() - start_time:.2f} seconds.")

        except ValueError as e:
            status_container.error("Workflow failed due to critical agent error. See above statuses.")
        except Exception as e:
            status_container.error(f"An unexpected critical system error occurred: {e}")
            logger.critical(f"Unexpected system failure: {e}")


if __name__ == "__main__":
    main()