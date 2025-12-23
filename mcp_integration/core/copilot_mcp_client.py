#!/usr/bin/env python3

"""
Copilot MCP Client - Alternative to Anthropic MCP for AI analysis
Uses the CopilotLLM provider instead of Anthropic API
"""

import json
import logging
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage

# Import CopilotLLM
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from providers.copilot import CopilotLLM
except ImportError:
    raise ImportError("Could not import CopilotLLM. Make sure providers/copilot.py is available")

logger = logging.getLogger(__name__)


class CopilotMCPClient:
    """
    MCP Client that uses Copilot LLM for AI analysis tasks
    Compatible with Anthropic MCP interface
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 60000)
        self.retry_attempts = config.get('retryAttempts', 3)
        
        # Initialize Copilot LLM
        try:
            self.llm = CopilotLLM()
            logger.info("CopilotMCP initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CopilotLLM: {e}")
            raise
    
    def connect(self) -> bool:
        """Test connection by making a simple call"""
        try:
            test_message = [HumanMessage(content="Test connection. Reply with 'OK'.")]
            response = self.llm.invoke(test_message)
            logger.info("CopilotMCP connection test successful")
            return True
        except Exception as e:
            logger.error(f"CopilotMCP connection test failed: {e}")
            return False
    
    def execute_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Execute AI command using Copilot
        
        Supported commands:
        - ai_analyze: Analyze data for a specific purpose
        - ai_summarize: Summarize content
        - ai_generate: Generate content about a topic
        - ai_translate: Translate text to another language
        - ai_extract: Extract entities from text
        - ai_classify: Classify content into categories
        - ai_compare: Compare two items
        - ai_evaluate: Evaluate content against criteria
        - ai_predict: Predict outcomes based on data
        - ai_recommend: Recommend items based on preferences
        - ai_explain: Explain a concept
        - ai_rewrite: Rewrite text in a specific style
        - ai_code_review: Review code
        - ai_debug: Debug errors
        - ai_optimize: Optimize content for a goal
        - ai_validate: Validate data against schema
        - ai_convert: Convert data between formats
        - ai_sentiment: Analyze sentiment
        - ai_keywords: Extract keywords
        - ai_answer: Answer questions
        """
        try:
            # Map command to appropriate prompt
            prompt = self._build_prompt(command, **kwargs)
            
            # Create messages
            messages = [
                SystemMessage(content="You are a helpful AI assistant powered by GitHub Copilot. Provide clear, accurate, and concise responses."),
                HumanMessage(content=prompt)
            ]
            
            # Invoke LLM
            response = self.llm.invoke(messages)
            
            # Extract content
            content = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "success": True,
                "command": command,
                "data": content,
                "raw_output": content,
                "provider": "copilot"
            }
            
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            return {
                "success": False,
                "command": command,
                "error": str(e),
                "provider": "copilot"
            }
    
    def _build_prompt(self, command: str, **kwargs) -> str:
        """Build appropriate prompt based on command and arguments"""
        
        handlers = {
            "ai_analyze": lambda: f"Analyze the following data for {kwargs.get('purpose', 'general analysis')}:\n\n{kwargs.get('data', '')}",
            "ai_summarize": lambda: f"Summarize the following content:\n\n{kwargs.get('content', '')}",
            "ai_generate": lambda: f"Generate {kwargs.get('content_type', 'text')} about {kwargs.get('topic', '')}",
            "ai_translate": lambda: f"Translate the following text to {kwargs.get('language', 'English')}:\n\n{kwargs.get('text', '')}",
            "ai_extract": lambda: f"Extract {kwargs.get('entities', 'entities')} from the following text:\n\n{kwargs.get('text', '')}",
            "ai_classify": lambda: f"Classify the following content into these categories: {kwargs.get('categories', '')}\n\nContent:\n{kwargs.get('content', '')}",
            "ai_compare": lambda: f"Compare the following:\n\nItem 1: {kwargs.get('item1', '')}\n\nItem 2: {kwargs.get('item2', '')}",
            "ai_evaluate": lambda: f"Evaluate the following content against these criteria: {kwargs.get('criteria', '')}\n\nContent:\n{kwargs.get('content', '')}",
            "ai_predict": lambda: f"Predict {kwargs.get('outcome', '')} based on the following data:\n\n{kwargs.get('data', '')}",
            "ai_recommend": lambda: f"Recommend {kwargs.get('items', '')} based on these preferences: {kwargs.get('preferences', '')}",
            "ai_explain": lambda: f"Explain the following concept in {kwargs.get('style', 'simple')} style:\n\n{kwargs.get('concept', '')}",
            "ai_rewrite": lambda: f"Rewrite the following text in {kwargs.get('style', '')} style:\n\n{kwargs.get('text', '')}",
            "ai_code_review": lambda: f"Review the following code:\n\n```\n{kwargs.get('code', '')}\n```",
            "ai_debug": lambda: f"Debug the following error:\n\nError: {kwargs.get('error', '')}\n\nContext: {kwargs.get('context', '')}",
            "ai_optimize": lambda: f"Optimize the following content for {kwargs.get('goal', '')}:\n\n{kwargs.get('content', '')}",
            "ai_validate": lambda: f"Validate the following data against this schema:\n\nSchema: {kwargs.get('schema', '')}\n\nData: {kwargs.get('data', '')}",
            "ai_convert": lambda: f"Convert the following data from {kwargs.get('format1', '')} to {kwargs.get('format2', '')}:\n\n{kwargs.get('data', '')}",
            "ai_sentiment": lambda: f"Analyze the sentiment of the following text:\n\n{kwargs.get('text', '')}",
            "ai_keywords": lambda: f"Extract keywords from the following text:\n\n{kwargs.get('text', '')}",
            "ai_answer": lambda: f"Answer the following question:\n\n{kwargs.get('question', '')}",
        }
        
        if command in handlers:
            return handlers[command]()
            
        # Generic command fallback
        prompt_parts = [f"Command: {command}"]
        for key, value in kwargs.items():
            prompt_parts.append(f"{key}: {value}")
        return "\n".join(prompt_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "server": "copilot_mcp",
            "status": "connected",
            "provider": "GitHub Copilot",
            "model": self.llm.model_name if hasattr(self, 'llm') else "unknown"
        }
