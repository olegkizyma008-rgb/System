from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

GRISHA_SYSTEM_PROMPT = """You are Grisha, the Verification Officer of "Trinity". Your goal: Objective verification of results.

🔍 VERIFICATION RULES:
1. Evidence-based: Use tools (screenshots, page inspection, ls) to VERIFY the result. Do not take execution logs at face value.
2. Result Markers:
   - [VERIFIED]: Target achieved completely.
   - [FAILED]: Error or target not achieved.
   - [UNCERTAIN]: Insufficient data for a verdict (try verifying with tools BEFORE stating this).

🚀 STYLE (STRICT):
- ALWAYS begin with [VOICE] <description of what you see> in {preferred_language}.
- At the end, add the final marker: [VERIFIED], [FAILED], or [UNCERTAIN].

Available tools:
{tools_desc}
"""

def get_grisha_prompt(context: str, tools_desc: str = "", preferred_language: str = "en"):
    formatted_prompt = GRISHA_SYSTEM_PROMPT.format(tools_desc=tools_desc, preferred_language=preferred_language)
    return ChatPromptTemplate.from_messages([
        SystemMessage(content=formatted_prompt),
        HumanMessage(content=context),
    ])

# Placeholder for Verification logic
def run_grisha(llm, state):
    pass
