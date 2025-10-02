import unittest
import os
import shutil
from unittest.mock import patch, MagicMock
from collections import Counter

# Import the agent classes
from agents.repo_analyzer import RepoAnalyzerAgent
from agents.metadata_recommender import MetadataRecommenderAgent
# We assume the LangGraph setup is available to import from app.py
from app import create_graph 
from agents.content_improver import ContentSuggestions # For Pydantic check

# --- Mock Data and Setup ---

# Simple mock content simulating a single README chunk
MOCK_FILE_CONTENT = """
# Project Alpha: Multi-Agent RAG System

This project demonstrates agent orchestration using LangGraph.
It is essential for documentation, stability, and reliable testing.
The system uses the RAG pattern for reliable context grounding. RAG stability is critical.
"""

class TestAgentCoreLogic(unittest.TestCase):
    
    def setUp(self):
        """Set up objects needed for testing."""
        self.test_repo_url = "https://github.com/test/test-repo"
        self.analyzer = RepoAnalyzerAgent(self.test_repo_url)
        self.metadata_recommender = MetadataRecommenderAgent()

    # --- Unit Tests (Module 3 Requirement) ---

    @patch('os.path.exists', return_value=True)
    @patch('agents.repo_analyzer.TextLoader')
    @patch('agents.repo_analyzer.Repo')
    @patch('agents.repo_analyzer.shutil')
    def test_repo_analyzer_process_success(self, MockShutil, MockRepo, MockLoader, mock_exists):
        """Tests Agent 1's ability to mock clone, load files, and clean up."""
        
        # Configure the mock loader to return mock documents
        mock_doc = MagicMock()
        mock_doc.load.return_value = [MagicMock(page_content=MOCK_FILE_CONTENT)]
        MockLoader.return_value = mock_doc
        
        with patch.object(self.analyzer, '_clone_repo') as mock_clone, \
             patch.object(self.analyzer, 'create_retriever'):
            
            # Since we mock cloning and cleanup, this runs fast
            chunks = self.analyzer.process_repo()
            
            mock_clone.assert_called_once()
            # Assert cleanup was attempted (even if mocked)
            MockShutil.rmtree.assert_called_with(self.analyzer.working_dir, ignore_errors=True)
            self.assertGreater(len(chunks), 0) 
            self.assertIn('# Project Alpha:', chunks[0].page_content)

    def test_metadata_extractor(self):
        """Tests Agent 2's keyword extraction tool (Unit Test for Tool)."""
        
        test_content = "LangGraph orchestration uses agents for RAG. RAG stability is critical."
        metadata = self.metadata_recommender.suggest_metadata(test_content)
        
        # Keywords should be extracted and filtered
        self.assertIn('rag', metadata['keywords'])
        self.assertIn('langgraph', metadata['keywords'])
        self.assertNotIn('is', metadata['keywords'])
        self.assertIn('LLM/Generative AI', metadata['categories'])

    # --- Integration Test (Module 3 Requirement) ---

    @patch('os.path.exists', return_value=True)
    @patch('agents.repo_analyzer.TextLoader')
    @patch('agents.repo_analyzer.Repo')
    def test_langgraph_flow_integrity(self, MockRepo, MockLoader, mock_exists):
        """Tests Agent 1 and Agent 2 data flow integrity (Integration Test)."""
        
        # 1. Setup Mock Data
        mock_doc = MagicMock()
        mock_doc.load.return_value = [MagicMock(page_content=MOCK_FILE_CONTENT)]
        MockLoader.return_value = mock_doc
        
        # 2. Mock Agent 3 (ContentImprover) to avoid external API/network calls
        @patch('agents.content_improver.ContentImproverAgent.generate_improved_content', return_value=ContentSuggestions(new_title="Test Title", short_summary="Test summary.", readme_edits=["a"]).dict())
        @patch('agents.repo_analyzer.RepoAnalyzerAgent.create_retriever', return_value=MagicMock())
        @patch('agents.repo_analyzer.shutil')
        def inner_test(MockShutil, MockRetriever, MockImprovementNode):
            
            # 3. Create Graph
            app = create_graph()
            
            # 4. Run the entire workflow (E2E simulation)
            inputs = {"repo_url": self.test_repo_url}
            final_state = app.invoke(inputs)
            
            # 5. Assertions: Check data handoff and final output structure
            
            # Check Agent 2 received Agent 1's output and produced metadata
            self.assertTrue(final_state['metadata'])
            
            # Check Agent 3 ran and successfully parsed the mock dictionary
            self.assertEqual(final_state['improved_content']['new_title'], 'Test Title')
            self.assertIsInstance(final_state['improved_content'], dict)
            
        inner_test()

if __name__ == '__main__':
    unittest.main()