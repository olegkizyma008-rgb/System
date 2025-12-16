"""Clean agent messages display component.

Provides formatted, color-coded display of agent communications
without technical details (Tool Results, JSON, etc).
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class AgentType(Enum):
    """Agent types with color schemes."""
    ATLAS = "atlas"          # 🌐 Strategist (cyan/blue)
    TETYANA = "tetyana"      # 💻 Developer (green)
    GRISHA = "grisha"        # 👁️ Verifier (yellow/orange)
    USER = "user"            # 👤 User (white/default)
    SYSTEM = "system"        # ⚙️ System (gray)


@dataclass
class AgentMessage:
    """Structured agent message."""
    agent: AgentType
    text: str
    timestamp: Optional[float] = None
    is_technical: bool = False  # Hide if True (Tool Results, JSON, etc)


class MessageFilter:
    """Filter out technical messages while preserving clean communication."""
    
    TECHNICAL_PATTERNS = [
        "Tool Results:",
        "Result for ",
        "capture_screen:",
        "write_file:",
        "run_shell:",
        "analyze_screen:",
        "vision_mode:",
        "diff_bbox:",
        "bytes_written:",
        "error_type:",
        "permission_required",
        "{",  # JSON start
        "\"",  # JSON quotes
    ]
    
    @staticmethod
    def is_technical(text: str) -> bool:
        """Check if message contains technical details."""
        lower_text = text.lower()
        return any(pattern.lower() in lower_text for pattern in MessageFilter.TECHNICAL_PATTERNS)
    
    @staticmethod
    def clean_message(text: str) -> str:
        """Remove technical details from message."""
        lines = text.split("\n")
        clean_lines = []
        skip_until_empty = False
        
        for line in lines:
            # Skip Tool Results sections
            if "Tool Results:" in line or "Result for " in line:
                skip_until_empty = True
                continue
            
            # Skip JSON/technical lines
            if skip_until_empty:
                if line.strip() == "":
                    skip_until_empty = False
                continue
            
            # Skip pure JSON lines
            if line.strip().startswith("{") or line.strip().startswith("["):
                continue
            
            clean_lines.append(line)
        
        # Join and clean up extra whitespace
        result = "\n".join(clean_lines).strip()
        return result


class MessageFormatter:
    """Format agent messages with colors and styling."""
    
    AGENT_COLORS = {
        AgentType.ATLAS: "class:agent.atlas",
        AgentType.TETYANA: "class:agent.tetyana",
        AgentType.GRISHA: "class:agent.grisha",
        AgentType.USER: "class:agent.user",
        AgentType.SYSTEM: "class:agent.system",
    }
    
    AGENT_ICONS = {
        AgentType.ATLAS: "🌐",
        AgentType.TETYANA: "💻",
        AgentType.GRISHA: "👁️",
        AgentType.USER: "👤",
        AgentType.SYSTEM: "⚙️",
    }
    
    AGENT_NAMES = {
        AgentType.ATLAS: "Atlas",
        AgentType.TETYANA: "Tetyana",
        AgentType.GRISHA: "Grisha",
        AgentType.USER: "You",
        AgentType.SYSTEM: "System",
    }
    
    @staticmethod
    def format_message(msg: AgentMessage) -> List[Tuple[str, str]]:
        """Format agent message with color and styling.
        
        Returns list of (style, text) tuples for prompt_toolkit.
        """
        result = []
        
        # Skip technical messages
        if msg.is_technical or MessageFilter.is_technical(msg.text):
            return result
        
        # Clean the message
        clean_text = MessageFilter.clean_message(msg.text)
        if not clean_text:
            return result
        
        # Agent header with icon and name
        icon = MessageFormatter.AGENT_ICONS.get(msg.agent, "•")
        name = MessageFormatter.AGENT_NAMES.get(msg.agent, "Unknown")
        color = MessageFormatter.AGENT_COLORS.get(msg.agent, "class:agent.system")
        
        result.append((color, f"{icon} {name}: "))
        result.append(("class:agent.text", f"{clean_text}\n\n"))
        
        return result
    
    @staticmethod
    def format_messages(messages: List[AgentMessage]) -> List[Tuple[str, str]]:
        """Format multiple messages."""
        result = []
        for msg in messages:
            result.extend(MessageFormatter.format_message(msg))
        return result


class MessageBuffer:
    """Buffer for managing agent messages."""
    
    def __init__(self, max_messages: int = 200):
        self.messages: List[AgentMessage] = []
        self.max_messages = max_messages
    
    def add(self, agent: AgentType, text: str, is_technical: bool = False) -> None:
        """Add a message to the buffer."""
        msg = AgentMessage(agent=agent, text=text, is_technical=is_technical)
        self.messages.append(msg)
        
        # Trim if too many
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_formatted(self) -> List[Tuple[str, str]]:
        """Get all messages formatted for display."""
        return MessageFormatter.format_messages(self.messages)
    
    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []
    
    def get_last_n(self, n: int) -> List[AgentMessage]:
        """Get last N messages."""
        return self.messages[-n:] if n > 0 else []
