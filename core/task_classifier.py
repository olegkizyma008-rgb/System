#!/usr/bin/env python3
"""
Advanced task classification system for MCP tool selection.
Classifies tasks by analyzing context and requirements.
"""

from typing import Dict, List
import re


class TaskClassifier:
    """Classify tasks by analyzing context and requirements."""
    
    def __init__(self):
        # Task type patterns
        self.patterns = {
            "browser_automation": r"browser|google|search|navigate|url|page|website",
            "system_command": r"system|command|terminal|shell|execute|run|script",
            "gui_interaction": r"gui|click|button|element|window|interface|control",
            "file_operation": r"file|copy|move|delete|read|write|save|download|upload",
            "ai_analysis": r"ai|analyze|decision|intelligence|machine learning|predict",
            "default": r".*"  # Catch-all
        }
        
        # Task examples for each type
        self.examples = {
            "browser_automation": ["open google", "search web", "navigate to url"],
            "system_command": ["run command", "execute script", "system operation"],
            "gui_interaction": ["click button", "interact with gui", "control window"],
            "file_operation": ["copy file", "move document", "save data"],
            "ai_analysis": ["analyze data", "make decision", "predict outcome"]
        }
    
    def classify_task(self, task_context: str) -> str:
        """Classify task based on context analysis."""
        context_lower = task_context.lower()
        
        for task_type, pattern in self.patterns.items():
            if re.search(pattern, context_lower):
                return task_type
        
        return "default"
    
    def get_task_examples(self, task_type: str) -> List[str]:
        """Get examples for task type."""
        return self.examples.get(task_type, [])


class RAGToolSelector:
    """Select tools using RAG from large example database."""
    
    def __init__(self):
        # Initialize vector database
        from chromadb import Client
        self.vector_db = Client()
        self.collection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize vector database with tool examples."""
        # Load tool examples from repository
        import glob
        import json
        
        examples = []
        for file_path in glob.glob("repository/tool_examples/*.json"):
            with open(file_path, 'r') as f:
                examples.extend(json.load(f))
        
        # Create collection
        if examples:
            self.collection = self.vector_db.create_collection("tool_examples")
            self.collection.add(
                documents=[e["description"] for e in examples],
                metadatas=[{"tool": e["tool"], "category": e["category"]} for e in examples],
                ids=[str(i) for i in range(len(examples))]
            )
    
    def find_similar_examples(self, task_query: str, top_k: int = 5) -> List[Dict]:
        """Find similar tool examples using vector search."""
        if not self.collection:
            return []
        
        results = self.collection.query(
            query_texts=[task_query],
            n_results=top_k
        )
        
        return [
            {
                "tool": r["metadatas"][0]["tool"],
                "description": r["documents"][0],
                "category": r["metadatas"][0]["category"],
                "similarity": r["distances"][0]
            }
            for r in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]


class MCPTaskHandler:
    """Handle MCP tasks with intelligent tool selection."""
    
    def __init__(self):
        self.classifier = TaskClassifier()
        self.selector = RAGToolSelector()
    
    def handle_task(self, task_context: str) -> Dict:
        """Handle task with intelligent tool selection."""
        # Step 1: Classify task
        task_type = self.classifier.classify_task(task_context)
        
        # Step 2: Find similar examples
        examples = self.selector.find_similar_examples(task_context)
        
        # Step 3: Select best tool
        best_tool = self._select_best_tool(examples, task_type)
        
        # Step 4: Generate execution plan
        plan = self._generate_execution_plan(best_tool, examples)
        
        return {
            "task_type": task_type,
            "selected_tool": best_tool,
            "examples": examples,
            "execution_plan": plan
        }
    
    def _select_best_tool(self, examples: List[Dict], task_type: str) -> str:
        """Select best tool from examples."""
        if not examples:
            return self._get_default_tool(task_type)
        
        # Simple: Select tool with highest similarity
        return max(examples, key=lambda x: x["similarity"])["tool"]
    
    def _generate_execution_plan(self, tool: str, examples: List[Dict]) -> Dict:
        """Generate execution plan."""
        return {
            "tool": tool,
            "parameters": self._extract_parameters(examples[0] if examples else None),
            "confidence": self._calculate_confidence(examples)
        }
    
    def _get_default_tool(self, task_type: str) -> str:
        """Get default tool for task type."""
        defaults = {
            "browser_automation": "browser_navigate",
            "system_command": "run_shell",
            "gui_interaction": "gui_click",
            "file_operation": "file_read",
            "default": "browser_navigate"
        }
        return defaults.get(task_type, "browser_navigate")
    
    def _extract_parameters(self, example: Dict) -> Dict:
        """Extract parameters from example."""
        if not example:
            return {}
        
        # Simple parameter extraction
        return {"example": example["description"]}
    
    def _calculate_confidence(self, examples: List[Dict]) -> float:
        """Calculate confidence score."""
        if not examples:
            return 0.5
        return 1.0 - (min(e["similarity"] for e in examples) * 0.5)


if __name__ == "__main__":
    # Example usage
    handler = MCPTaskHandler()
    
    # Test task
    task = "Open Google and search for AI news"
    result = handler.handle_task(task)
    
    print(f"Task: {task}")
    print(f"Result: {result}")
