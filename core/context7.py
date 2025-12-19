"""Context7 Layer

A dedicated context management layer for Trinity Runtime.
Responsible for context preparation, token budgeting, policy injection, and normalization.
Acting as the 'Explicit Context Manager' described in the Project Atlas documentation.
"""

from typing import Dict, Any, List, Optional
import json

class Context7:
    """Manages context assembly and policy injection for Trinity agents."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Simple heuristic token limit safeguards (soft limits)
        self.MAX_CONTEXT_TOKENS = 32000  # Conservative adjustment space
        self.CHARS_PER_TOKEN = 4

    def prepare(self, 
                rag_context: str, 
                project_structure: str, 
                meta_config: Dict[str, Any],
                last_msg: str = "") -> str:
        """
        Prepares the final context string for the Atlas planner.
        
        Args:
            rag_context: Raw context retrieved from RAG/Memory.
            project_structure: Current file structure representation.
            meta_config: Meta-Planner configuration (strategy, limits, etc).
            last_msg: The specific user task or trigger message.
            
        Returns:
            Formatted, budgeted, and policy-injected context string.
        """
        
        # 1. Apply Policy (High Priority)
        policy_block = self._format_policy(meta_config)
        
        # 2. Budget Tokens
        # Priority: Policy > Structure > RAG
        # We assume Policy is small (~500 chars)
        # Structure can be large (~5k-10k chars)
        # RAG acts as the filler up to limit
        
        available_chars = self.MAX_CONTEXT_TOKENS * self.CHARS_PER_TOKEN
        
        used_chars = len(policy_block) + len(project_structure) + len(last_msg)
        remaining_chars = available_chars - used_chars
        
        final_rag = rag_context
        if remaining_chars < len(rag_context):
            if self.verbose:
                print(f"[Context7] Budgeting RAG context: {len(rag_context)} -> {remaining_chars} chars")
            final_rag = rag_context[:max(0, remaining_chars)] + "\n...[Context Truncated by Context7]..."
            
        # 3. Assemble
        sections = []
        
        # Section: Policy / Strategy
        sections.append(f"## 🧠 STRATEGIC POLICY (Meta-Planner)\n{policy_block}")
        
        # Section: Structural Context
        if project_structure:
            sections.append(f"## 📂 PROJECT STRUCTURE\n{project_structure}")
            
        # Section: Retrieved Memory / RAG
        if final_rag:
            sections.append(f"## 📚 RETRIEVED KNOWLEDGE (RAG)\n{final_rag}")
            
        return "\n\n".join(sections)

    def _format_policy(self, config: Dict[str, Any]) -> str:
        """Formats the meta_config into a readable policy block."""
        strategy = config.get('strategy', 'linear')
        rigor = config.get('verification_rigor', 'medium')
        tool_pref = config.get('tool_preference', 'hybrid')
        
        lines = [
            f"- Strategy Mode: **{strategy.upper()}**",
            f"- Verification Rigor: **{rigor.upper()}**",
            f"- Tool Preference: **{tool_pref.upper()}**",
        ]
        
        if config.get("anti_patterns"):
             lines.append(f"- AVOID PATTERNS: {config['anti_patterns']}")
             
        if config.get("focus"):
            lines.append(f"- FOCUS: {config['focus']}")
            
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        """Returns stats about context usage (placeholder for future metrics)."""
        return {"policy": "local_heuristic"}
