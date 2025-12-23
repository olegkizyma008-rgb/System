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
    VIBE = "vibe"            # ⚕️ Doctor Vibe (magenta)
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
        "tool_calls",
        '"tool_calls":',
        "final_answer",
        "\"final_answer\":",
    ]
    
    @staticmethod
    def is_technical(text: str) -> bool:
        """Check if message contains technical details."""
        lower_text = text.lower()
        return any(pattern.lower() in lower_text for pattern in MessageFilter.TECHNICAL_PATTERNS)
    
    @staticmethod
    def clean_technical_markers(text: str) -> str:
        """Remove technical markers like [STEP_COMPLETED], [VERIFIED], etc."""
        import re
        patterns = [
            r'\[(?:STEP_COMPLETED|VERIFIED|FAILED|UNCERTAIN|NOT VERIFIED)\]',
            r'\[VOICE\]',  # Also remove [VOICE] here if we want absolute cleanliness
        ]
        result = text
        for p in patterns:
            result = re.sub(p, '', result)
        return result.strip()

    @staticmethod
    def clean_message(text: str) -> str:
        """Remove technical details from message while prioritizing [VOICE] content."""
        # 1. Prioritize [VOICE] content if present
        if "[VOICE]" in text:
            import re
            match = re.search(r"\[VOICE\]\s*(.*)", text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                return MessageFilter.clean_technical_markers(content)
        
        # 2. Fallback cleaning (remove technical lines/JSON)
        lines = text.split("\n")
        clean_lines = []
        skip_until_empty = False
        
        for line in lines:
            if any(pattern.lower() in line.lower() for pattern in MessageFilter.TECHNICAL_PATTERNS):
                skip_until_empty = True
                continue
            
            if skip_until_empty:
                if line.strip() == "":
                    skip_until_empty = False
                continue
            
            if line.strip().startswith(("{", "[", '"')) or line.strip() in ("}", "]", "},", "],"):
                continue
            
            clean_lines.append(line)
        
        result = "\n".join(clean_lines).strip()
        
        # If result looks like JSON, take the first non-JSON line
        if "{" in result and "}" in result:
             first_line = result.split("\n")[0]
             if not first_line.startswith(("{", "[")):
                 result = first_line.strip()
        
        return MessageFilter.clean_technical_markers(result)


class MessageFormatter:
    """Format agent messages with colors and styling for direct communication."""
    
    AGENT_COLORS = {
        AgentType.ATLAS: "class:agent.atlas",
        AgentType.TETYANA: "class:agent.tetyana",
        AgentType.GRISHA: "class:agent.grisha",
        AgentType.VIBE: "class:agent.vibe",
        AgentType.USER: "class:agent.user",
        AgentType.SYSTEM: "class:agent.system",
    }
    
    AGENT_NAMES = {
        AgentType.ATLAS: "ATLAS",
        AgentType.TETYANA: "TETYANA",
        AgentType.GRISHA: "GRISHA",
        AgentType.VIBE: "VIBE",
        AgentType.USER: "USER",
        AgentType.SYSTEM: "SYSTEM",
    }
    
    AGENT_EMOJIS = {
        AgentType.ATLAS: "🌐",
        AgentType.TETYANA: "💻",
        AgentType.GRISHA: "👁️",
        AgentType.VIBE: "⚕️",
        AgentType.USER: "👤",
        AgentType.SYSTEM: "⚙️",
    }
    
    # Patterns for highlighting @mentions
    MENTION_PATTERNS = {
        "tetyana": AgentType.TETYANA,
        "тетяна": AgentType.TETYANA,
        "тетяно": AgentType.TETYANA,
        "тетяну": AgentType.TETYANA,
        "grisha": AgentType.GRISHA,
        "гріша": AgentType.GRISHA,
        "грішо": AgentType.GRISHA,
        "atlas": AgentType.ATLAS,
        "атлас": AgentType.ATLAS,
        "атласе": AgentType.ATLAS,
    }
    
    @staticmethod
    def highlight_mentions(text: str) -> List[Tuple[str, str]]:
        """Parse text and highlight agent @mentions with their colors."""
        import re
        
        result: List[Tuple[str, str]] = []
        
        # Build pattern for all mentions (case insensitive)
        mention_words = list(MessageFormatter.MENTION_PATTERNS.keys())
        pattern = r'(@?)(' + '|'.join(re.escape(w) for w in mention_words) + r')'
        
        last_end = 0
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Add text before the match
            if match.start() > last_end:
                result.append(("class:agent.text", text[last_end:match.start()]))
            
            # Find the agent type for this mention
            mention_key = match.group(2).lower()
            agent_type = MessageFormatter.MENTION_PATTERNS.get(mention_key)
            if agent_type:
                color = MessageFormatter.AGENT_COLORS.get(agent_type, "class:agent.text")
                result.append((color, match.group(0)))
            else:
                result.append(("class:agent.text", match.group(0)))
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            result.append(("class:agent.text", text[last_end:]))
        
        return result if result else [("class:agent.text", text)]
    
    @staticmethod
    def format_message(msg: AgentMessage) -> List[Tuple[str, str]]:
        """Format agent message with compact direct communication style for TTS.
        
        STRICT: Only [VOICE] messages are displayed in agent panel.
        This panel is for verbal communication between agents that will be
        spoken via TTS - short, natural dialogue.
        
        Returns list of (style, text) tuples for prompt_toolkit.
        """
        result: List[Tuple[str, str]] = []
        
        # STRICT TTS FILTER: Only show [VOICE] messages
        # Agent panel is for verbal communication only, not technical logs
        # Allow Vibe messages to be shown even without explicit [VOICE]
        if "[VOICE]" not in msg.text and msg.agent != AgentType.VIBE:
            return result  # Skip ALL non-voice messages unless from Vibe

        if msg.agent not in {AgentType.ATLAS, AgentType.TETYANA, AgentType.GRISHA, AgentType.VIBE}:
            return result
        
        # Clean the message - remove unnecessary tags and make it more natural
        display_text = MessageFilter.clean_message(msg.text)
        if not display_text:
            return result
        
        # Format: [EMOJI NAME] Message (compact, single line for short messages)
        name = MessageFormatter.AGENT_NAMES.get(msg.agent, "UNKNOWN")
        emoji = MessageFormatter.AGENT_EMOJIS.get(msg.agent, "")
        color = MessageFormatter.AGENT_COLORS.get(msg.agent, "class:agent.system")

        # Compact layout - single line for short messages, minimal spacing
        # [EMOJI NAME] Message text...
        result.append((color, f"[{emoji} {name}]")) # Compact header
        result.append((" ", " ")) # Single space separator
        
        # Message text with @mentions highlighted - optimized for TTS
        # Keep text clean and natural for voice synthesis
        highlighted = MessageFormatter.highlight_mentions(display_text)
        for style, text in highlighted:
            # For TTS compatibility, use cleaner styles
            final_style = style
            if "agent.text" in style:
                final_style = final_style.replace(" dim", "")  # Remove dim for better TTS
            result.append((final_style, text))
        
        # Minimal spacing after message - single newline
        result.append(("class:agent.text", "\n"))
        
        return result
    
    @staticmethod
    def format_message_compact(msg: AgentMessage) -> List[Tuple[str, str]]:
        """Format agent message in ultra-compact style for TTS and streaming.
        
        Format: EMOJI Message text (no brackets, minimal formatting)
        
        Returns list of (style, text) tuples for prompt_toolkit.
        """
        result: List[Tuple[str, str]] = []
        
        # Skip technical messages unless they contain [VOICE]
        if "[VOICE]" not in msg.text:
            if msg.is_technical or MessageFilter.is_technical(msg.text):
                return result

        if msg.agent not in {AgentType.ATLAS, AgentType.TETYANA, AgentType.GRISHA}:
            return result
        
        # Clean the message - remove unnecessary tags and make it more natural
        display_text = MessageFilter.clean_message(msg.text)
        
        if not display_text:
            return result
        
        # TTS-optimized format: EMOJI Message (natural speech)
        emoji = MessageFormatter.AGENT_EMOJIS.get(msg.agent, "")
        color = MessageFormatter.AGENT_COLORS.get(msg.agent, "class:agent.system")

        # Format: EMOJI Message text (single line, clean for TTS)
        result.append((color, f"{emoji} ")) # Just emoji as prefix
        
        # Message text with @mentions highlighted - optimized for TTS
        highlighted = MessageFormatter.highlight_mentions(display_text)
        for style, text in highlighted:
            # For TTS compatibility, use cleaner styles
            final_style = style
            if "agent.text" in style:
                final_style = final_style.replace(" dim", "")  # Remove dim for better TTS
            result.append((final_style, text))
        
        # Minimal spacing after message - single space
        result.append(("class:agent.text", " "))
        
        return result
    
    @staticmethod
    def format_messages(messages: List[AgentMessage], compact: bool = False) -> List[Tuple[str, str]]:
        """Format multiple messages.
        
        Args:
            messages: List of agent messages
            compact: If True, use ultra-compact format for TTS streaming
        """
        result: List[Tuple[str, str]] = []
        last_verbal_agent = None
        last_verbal_text = None
        
        # Deduplicate consecutive identical verbal messages from same agent
        deduplicated = []
        for msg in messages:
            is_verbal = "[VOICE]" in msg.text
            if not is_verbal:
                deduplicated.append(msg)
                continue
                
            clean_text = MessageFilter.clean_message(msg.text)
            if msg.agent == last_verbal_agent and clean_text == last_verbal_text:
                continue # Skip visual duplicate
            
            deduplicated.append(msg)
            last_verbal_agent = msg.agent
            last_verbal_text = clean_text

        for msg in deduplicated:
            if compact:
                result.extend(MessageFormatter.format_message_compact(msg))
            else:
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

    def upsert_stream(self, agent: AgentType, text: str, is_technical: bool = False) -> None:
        """Add or update a streaming message.
        
        If the last verbal message in the buffer belongs to the same agent,
        update it instead of appending, even if there are technical messages
        in between. This prevents visual duplication in the AGENTS panel.
        """
        is_verbal = "[VOICE]" in text
        msg = AgentMessage(agent=agent, text=text, is_technical=is_technical)
        
        if is_verbal:
            # Look for the last verbal message
            idx = len(self.messages) - 1
            while idx >= 0:
                m = self.messages[idx]
                if "[VOICE]" in m.text:
                    if m.agent == agent:
                        self.messages[idx] = msg
                        return
                    else:
                        # Found a verbal message from a DIFFERENT agent, so must append
                        break
                idx -= 1
        
        # Default: check literal last message (for technical/non-voice updates)
        if self.messages and self.messages[-1].agent == agent and (self.messages[-1].is_technical == is_technical):
             self.messages[-1] = msg
        else:
            self.messages.append(msg)
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]
    
    def get_formatted(self) -> List[Tuple[str, str]]:
        """Get all messages formatted for display."""
        try:
            msgs_copy = list(self.messages)
            return MessageFormatter.format_messages(msgs_copy)
        except Exception:
            return []
    
    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []
    
    def get_last_n(self, n: int) -> List[AgentMessage]:
        """Get last N messages."""
        return self.messages[-n:] if n > 0 else []
