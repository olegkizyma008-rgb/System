# Trinity System Plugins

This directory contains custom plugins developed by the Trinity system itself.

## Structure

Each plugin should be organized in its own subdirectory:

```
plugins/
├── README.md
├── __init__.py
├── my_plugin_name/
│   ├── __init__.py
│   ├── plugin.py
│   ├── README.md
│   ├── requirements.txt (optional)
│   └── tests/
│       └── test_plugin.py
```

## Plugin Development Workflow

When you request Trinity to create a plugin:

1. **Trigger**: Say "створи плагін [назва]" or "create plugin [name]"
2. **Automatic Setup**: Trinity will:
   - Create the plugin directory structure
   - Initialize with boilerplate code
   - Switch to DEV mode with Doctor Vibe
   - Generate plugin scaffolding using standard Trinity workflow

3. **Doctor Vibe Integration**: The plugin development follows the standard Trinity DEV workflow:
   - Pre-emptive pause before file writes (unless TRINITY_VIBE_AUTO_APPLY=1)
   - Diff preview and stack trace in TUI
   - Option to review/approve changes

## Plugin Template

Each plugin should expose:

- `PluginMeta` (name, version, description, author)
- `register(registry: MCPToolRegistry)` - registers plugin tools
- Optional: `initialize()`, `cleanup()` hooks

## Environment Variables

- `TRINITY_DEV_BY_VIBE=1` - Doctor Vibe controls all DEV edits (default for plugin creation)
- `TRINITY_VIBE_AUTO_APPLY=1` - Auto-apply changes without pause (optional)

## Examples

See existing plugins in this directory for reference implementations.
