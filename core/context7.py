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
        Priority: Policy > last_msg > Structure > RAG
        """
        
        # 1. Apply Policy (High Priority)
        policy_block = self._format_policy(meta_config)
        
        # 2. Budget Characters
        # Conservative token count: 16k tokens -> ~48k chars (using 3 chars/token for safety)
        TOTAL_BUDGET = 16000 * 3 
        
        policy_len = len(policy_block)
        msg_len = len(last_msg)
        
        # Remaining budget for Structure and RAG
        remaining = TOTAL_BUDGET - (policy_len + msg_len + 500) # 500 for headers/overhead
        
        # Budget for structure (max 50% of remaining or 20k chars)
        structure_budget = min(int(remaining * 0.5), 20000)
        final_structure = project_structure
        if len(project_structure) > structure_budget:
            if self.verbose:
                 print(f"[Context7] Truncating structure: {len(project_structure)} -> {structure_budget}")
            final_structure = project_structure[:structure_budget] + "\n...[Structure Truncated]..."
            
        remaining -= len(final_structure)
        
        # Final budget for RAG
        final_rag = rag_context
        if len(rag_context) > remaining:
            if self.verbose:
                print(f"[Context7] Budgeting RAG context: {len(rag_context)} -> {max(0, remaining)} chars")
            final_rag = rag_context[:max(0, remaining)] + "\n...[Context Truncated by Context7]..."
            
        # 3. Assemble
        sections = []
        sections.append(f"## 🧠 STRATEGIC POLICY (Meta-Planner)\n{policy_block}")
        
        if final_structure:
            sections.append(f"## 📂 PROJECT STRUCTURE\n{final_structure}")
            
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
