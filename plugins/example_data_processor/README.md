# Example Data Processor

Example plugin demonstrating Trinity plugin development workflow

## Installation

This plugin is automatically discovered by Trinity.

## Usage

Use the `example_process_json` tool to process JSON data:

```python
# Example usage in Trinity
result = tools.example_process_json('{"key": "value", "count": 42}')
# Returns: {"status": "success", "keys": ["key", "count"], "length": 2}
```

## Development

Created by Trinity System using Doctor Vibe workflow.

This serves as a template for creating custom plugins with:
- Automatic discovery
- Tool registration
- Test coverage
- Documentation

## License

Part of Trinity System
