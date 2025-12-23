"""Context7 Layer

A dedicated context management layer for Trinity Runtime.
Responsible for context preparation, token budgeting, policy injection, and normalization.
Acting as the 'Explicit Context Manager' described in the Project Atlas documentation.

Enhanced with:
- Sliding window for step-aware context management
- Priority weighting for context sections
- Token metrics for monitoring
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ContextMetrics:
    """Metrics for context usage tracking."""
    total_chars: int = 0
    estimated_tokens: int = 0
    sections_included: List[str] = field(default_factory=list)
    truncations: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chars": self.total_chars,
            "estimated_tokens": self.estimated_tokens,
            "sections_included": self.sections_included,
            "truncations": self.truncations,
            "timestamp": self.timestamp.isoformat()
        }


class Context7:
    """Manages context assembly and policy injection for Trinity agents.
    
    Features:
    - Sliding window for message history (keeps last N steps)
    - Priority-based content allocation
    - Token budget tracking with metrics
    - Backward-compatible API
    """

    # Sliding window configuration
    MAX_WINDOW_STEPS = 10  # Keep last N messages/steps in context
    
    # Priority weights for context sections (must sum to 1.0)
    PRIORITY_WEIGHTS = {
        "policy": 0.10,         # Strategic policy (always included)
        "recent_steps": 0.35,   # Recent execution history
        "original_task": 0.15,  # Original user task
        "rag_context": 0.25,    # Retrieved knowledge
        "structure": 0.15       # Project structure
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Token estimation constants
        self.MAX_CONTEXT_TOKENS = 32000  # Conservative adjustment space
        self.CHARS_PER_TOKEN = 4
        # Metrics storage
        self._last_metrics: Optional[ContextMetrics] = None
        self._metrics_history: List[ContextMetrics] = []
        # Simple in-memory document store for optional local Context7 usage
        self._documents: List[Dict[str, Any]] = []

    def add_document(self, title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a document to the local Context7 store and return its metadata."""
        doc = {
            "id": f"doc_{len(self._documents) + 1}",
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self._documents.append(doc)
        if self.verbose:
            print(f"[Context7] Document added: {title} (id={doc['id']})")
        return doc

    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform a simple substring search over stored documents and return matches."""
        q = str(query or "").lower()
        results: List[Dict[str, Any]] = []
        for d in self._documents:
            if q in d.get("title", "").lower() or q in d.get("content", "").lower():
                snippet = d.get("content", "")[:500]
                results.append({"id": d["id"], "title": d["title"], "snippet": snippet, "metadata": d["metadata"]})
                if len(results) >= limit:
                    break
        return results

    def prepare(self, 
                rag_context: str, 
                project_structure: str, 
                meta_config: Dict[str, Any],
                last_msg: str = "") -> str:
        """
        Prepares the final context string for the Atlas planner.
        Priority: Policy > last_msg > Structure > RAG
        
        NOTE: This is the original method, kept for backward compatibility.
        For enhanced features, use prepare_with_window().
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

    def prepare_with_window(
        self,
        messages: List[Any],
        original_task: str,
        rag_context: str,
        project_structure: str,
        meta_config: Dict[str, Any],
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Enhanced context preparation with sliding window for message history.
        
        Args:
            messages: List of LangChain message objects (HumanMessage, AIMessage, etc.)
            original_task: The original user task/goal
            rag_context: Retrieved RAG context
            project_structure: Project structure text
            meta_config: Meta-planner configuration
            max_tokens: Optional token limit override
            
        Returns:
            Assembled context string optimized for token budget
        """
        metrics = ContextMetrics()
        max_tokens = max_tokens or self.MAX_CONTEXT_TOKENS
        char_budget = max_tokens * self.CHARS_PER_TOKEN
        
        # 1. Calculate budget for each section based on priority weights
        budgets = {
            section: int(char_budget * weight)
            for section, weight in self.PRIORITY_WEIGHTS.items()
        }
        
        sections = []
        
        # 2. Policy (always included, minimal truncation)
        policy_block = self._format_policy(meta_config)
        if len(policy_block) > budgets["policy"]:
            metrics.truncations["policy"] = len(policy_block) - budgets["policy"]
            policy_block = policy_block[:budgets["policy"]] + "..."
        sections.append(("policy", f"## 🧠 STRATEGIC POLICY\n{policy_block}"))
        metrics.sections_included.append("policy")
        
        # 3. Original Task (high priority)
        task_section = f"## 🎯 ORIGINAL TASK\n{original_task}"
        if len(task_section) > budgets["original_task"]:
            metrics.truncations["original_task"] = len(task_section) - budgets["original_task"]
            task_section = task_section[:budgets["original_task"]] + "..."
        sections.append(("original_task", task_section))
        metrics.sections_included.append("original_task")
        
        # 4. Recent Steps (sliding window) - highest priority after policy
        recent_steps = self._extract_recent_steps(messages, self.MAX_WINDOW_STEPS)
        if recent_steps:
            steps_text = self._format_recent_steps(recent_steps)
            if len(steps_text) > budgets["recent_steps"]:
                # Truncate from the beginning (keep most recent)
                metrics.truncations["recent_steps"] = len(steps_text) - budgets["recent_steps"]
                steps_text = "...[Earlier steps truncated]...\n" + steps_text[-(budgets["recent_steps"] - 50):]
            sections.append(("recent_steps", f"## 📝 RECENT EXECUTION HISTORY\n{steps_text}"))
            metrics.sections_included.append("recent_steps")
        
        # 5. RAG Context
        if rag_context:
            rag_section = f"## 📚 RETRIEVED KNOWLEDGE (RAG)\n{rag_context}"
            if len(rag_section) > budgets["rag_context"]:
                metrics.truncations["rag_context"] = len(rag_section) - budgets["rag_context"]
                rag_section = rag_section[:budgets["rag_context"]] + "\n...[RAG Truncated]..."
            sections.append(("rag_context", rag_section))
            metrics.sections_included.append("rag_context")
        
        # 6. Project Structure (lowest priority, can be heavily truncated)
        if project_structure:
            struct_section = f"## 📂 PROJECT STRUCTURE\n{project_structure}"
            if len(struct_section) > budgets["structure"]:
                metrics.truncations["structure"] = len(struct_section) - budgets["structure"]
                struct_section = struct_section[:budgets["structure"]] + "\n...[Structure Truncated]..."
            sections.append(("structure", struct_section))
            metrics.sections_included.append("structure")
        
        # 7. Assemble final context (sorted by priority)
        priority_order = ["policy", "original_task", "recent_steps", "rag_context", "structure"]
        sorted_sections = sorted(sections, key=lambda x: priority_order.index(x[0]))
        final_context = "\n\n".join(s[1] for s in sorted_sections)
        
        # 8. Record metrics
        metrics.total_chars = len(final_context)
        metrics.estimated_tokens = metrics.total_chars // self.CHARS_PER_TOKEN
        self._last_metrics = metrics
        self._metrics_history.append(metrics)
        
        # Keep only last 100 metrics entries
        if len(self._metrics_history) > 100:
            self._metrics_history = self._metrics_history[-100:]
        
        if self.verbose:
            print(f"[Context7] Prepared context: {metrics.estimated_tokens} tokens, "
                  f"{len(metrics.sections_included)} sections, "
                  f"{len(metrics.truncations)} truncations")
        
        return final_context

    def _extract_recent_steps(self, messages: List[Any], max_steps: int) -> List[Dict[str, str]]:
        """Extract the most recent steps from message history."""
        recent = []
        for msg in messages[-max_steps:]:
            content = getattr(msg, "content", str(msg))
            msg_type = type(msg).__name__
            
            # Extract meaningful step information
            if "[VOICE]" in content or "Step:" in content or "Result:" in content:
                recent.append({
                    "type": msg_type,
                    "content": content[:500]  # Limit each message
                })
        
        return recent

    def _format_recent_steps(self, steps: List[Dict[str, str]]) -> str:
        """Format recent steps for context injection."""
        lines = []
        for i, step in enumerate(steps, 1):
            step_type = step.get("type", "Message")
            content = step.get("content", "")
            
            # Clean up content for readability
            if "[VOICE]" in content:
                # Extract just the voice message
                voice_match = content.split("[VOICE]")
                if len(voice_match) > 1:
                    content = voice_match[1].strip()[:200]
            
            lines.append(f"**Step {i}** ({step_type}): {content[:200]}...")
        
        return "\n".join(lines)

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
        """Returns stats about context usage including recent metrics."""
        stats = {
            "policy": "sliding_window_priority",
            "max_window_steps": self.MAX_WINDOW_STEPS,
            "priority_weights": self.PRIORITY_WEIGHTS,
            "metrics_history_size": len(self._metrics_history)
        }
        
        if self._last_metrics:
            stats["last_metrics"] = self._last_metrics.to_dict()
        
        # Calculate averages from history
        if self._metrics_history:
            avg_tokens = sum(m.estimated_tokens for m in self._metrics_history) / len(self._metrics_history)
            avg_truncations = sum(len(m.truncations) for m in self._metrics_history) / len(self._metrics_history)
            stats["avg_tokens"] = int(avg_tokens)
            stats["avg_truncations"] = round(avg_truncations, 2)
        
        return stats

    def get_last_metrics(self) -> Optional[ContextMetrics]:
        """Get the most recent context metrics."""
        return self._last_metrics

    def clear_metrics_history(self) -> None:
        """Clear the metrics history."""
        self._metrics_history = []
        self._last_metrics = None

