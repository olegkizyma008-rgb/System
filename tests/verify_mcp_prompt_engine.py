#!/usr/bin/env python3
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_integration.prompt_engine import prompt_engine
from mcp_integration.core.mcp_client_manager import get_mcp_client_manager

def test_prompt_engine():
    print("Testing MCP Prompt Engine Initialization...")
    if not prompt_engine.prompts_collection:
        print("❌ Prompts collection not initialized.")
        return

    print("✅ Prompt Engine Initialized.")
    
    # Test retrieval 1: General Pattern
    query = "extract patterns from text"
    print(f"\nQuerying prompts for: '{query}'")
    prompts = prompt_engine.get_relevant_prompts(query)
    
    if prompts:
        print(f"✅ Found {len(prompts)} relevant prompts.")
        for p in prompts:
            print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("⚠️ No prompts found for pattern extraction.")

    # Test retrieval 2: Filesystem specific
    query_fs = "read a configuration file safely"
    print(f"\nQuerying prompts for: '{query_fs}'")
    prompts_fs = prompt_engine.get_relevant_prompts(query_fs)
    
    if prompts_fs:
        print(f"✅ Found {len(prompts_fs)} relevant filesystem prompts.")
    else:
        print("❌ No prompts found for filesystem query.")

    # Test retrieval 3: Playwright/Browser
    query_pw = "find a movie online and watch it"
    print(f"\nQuerying prompts for: '{query_pw}'")
    prompts_pw = prompt_engine.get_relevant_prompts(query_pw)
    
    if prompts_pw:
        print(f"✅ Found {len(prompts_pw)} relevant browser prompts.")
        for p in prompts_pw:
             print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for browser query.")

    # Test retrieval 4: Desktop Control
    query_dc = "make video fullscreen"
    print(f"\nQuerying prompts for: '{query_dc}'")
    prompts_dc = prompt_engine.get_relevant_prompts(query_dc)
    
    if prompts_dc:
        print(f"✅ Found {len(prompts_dc)} relevant desktop control prompts.")
        for p in prompts_dc:
             print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for desktop control query.")

    # Test retrieval 5: AppleScript
    query_as = "automate system settings on mac"
    print(f"\nQuerying prompts for: '{query_as}'")
    prompts_as = prompt_engine.get_relevant_prompts(query_as)
    if prompts_as:
        print(f"✅ Found {len(prompts_as)} relevant AppleScript prompts.")
        for p in prompts_as: print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for AppleScript query.")

    # Test retrieval 6: Anthropic
    query_ant = "ask llm to write a poem"
    print(f"\nQuerying prompts for: '{query_ant}'")
    prompts_ant = prompt_engine.get_relevant_prompts(query_ant)
    if prompts_ant:
        print(f"✅ Found {len(prompts_ant)} relevant Anthropic prompts.")
        for p in prompts_ant: print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for Anthropic query.")

    # Test retrieval 7: SonarQube
    query_sq = "check code quality issues"
    print(f"\nQuerying prompts for: '{query_sq}'")
    prompts_sq = prompt_engine.get_relevant_prompts(query_sq)
    if prompts_sq:
        print(f"✅ Found {len(prompts_sq)} relevant SonarQube prompts.")
        for p in prompts_sq: print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for SonarQube query.")

    # Test retrieval 8: Context7
    query_c7 = "find documentation for react"
    print(f"\nQuerying prompts for: '{query_c7}'")
    prompts_c7 = prompt_engine.get_relevant_prompts(query_c7)
    if prompts_c7:
        print(f"✅ Found {len(prompts_c7)} relevant Context7 prompts.")
        for p in prompts_c7: print(f"   - [{p['score']:.2f}] {p['source']}: {p['content'][:60]}...")
    else:
        print("❌ No prompts found for Context7 query.")

    # Test Integration with Client Manager (Mock)
    print("\nTesting Context Injection...")
    context = prompt_engine.construct_context(query)
    if context:
        print(f"✅ Context constructed ({len(context)} chars).")
        print("--- Context Preview ---")
        print(context[:200] + "...")
    else:
        print("⚠️ No context constructed.")

if __name__ == "__main__":
    test_prompt_engine()
