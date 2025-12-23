import sys
import os
from unittest.mock import MagicMock

# Set up path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

def test_menu_item_structures():
    # Mock necessary state/globals before importing
    from tui.state import state, MenuLevel
    from tui.constants import MAIN_MENU_ITEMS
    
    # Mocking tool reactions
    import tui.cli as cli
    cli.agent_chat_mode = True
    cli.agent_session = MagicMock()
    cli.agent_session.enabled = True
    
    # Check _get_settings_menu_items
    settings_items = cli._get_settings_menu_items()
    for item in settings_items:
        assert isinstance(item, tuple), f"Item {item} is not a tuple"
        assert len(item) == 3, f"Item {item} in settings has length {len(item)}, expected 3"
    
    # Check _get_llm_menu_items
    llm_items = cli._get_llm_menu_items()
    for item in llm_items:
        assert isinstance(item, tuple), f"Item {item} is not a tuple"
        assert len(item) == 3, f"Item {item} in llm_items has length {len(item)}, expected 3"
        
    # Check _get_agent_menu_items
    agent_items = cli._get_agent_menu_items()
    for item in agent_items:
        assert isinstance(item, tuple), f"Item {item} is not a tuple"
        assert len(item) == 3, f"Item {item} in agent_items has length {len(item)}, expected 3"
        
    # Check _get_automation_permissions_menu_items
    auto_items = cli._get_automation_permissions_menu_items()
    for item in auto_items:
        assert isinstance(item, tuple), f"Item {item} is not a tuple"
        assert len(item) == 3, f"Item {item} in auto_items has length {len(item)}, expected 3"
        
    # Check _get_dev_settings_menu_items
    dev_items = cli._get_dev_settings_menu_items()
    for item in dev_items:
        assert isinstance(item, tuple), f"Item {item} is not a tuple"
        assert len(item) == 3, f"Item {item} in dev_items has length {len(item)}, expected 3"

    print("✅ All menu item structures are consistent (tuples of length 3).")

if __name__ == "__main__":
    try:
        test_menu_item_structures()
    except AssertionError as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)
