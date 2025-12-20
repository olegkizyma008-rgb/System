# Task Analysis System - User Guide

## 🎯 Overview

This guide explains how to use the Task Analysis System to execute tasks, monitor logs, analyze screenshots, and improve code based on execution results.

## 🚀 Getting Started

### 1. Initialize the Task Analyzer

```python
from task_analysis_system import TaskAnalyzer

# Create analyzer instance
analyzer = TaskAnalyzer()
```

### 2. Start Task Analysis

```python
# Start analyzing a new task
result = analyzer.start_task_analysis(
    task_name="AI Movie Search",
    task_description="Find and play a modern AI movie in fullscreen"
)

print(f"Task started: {result['task_id']}")
```

## 📝 Task Execution with Logging

### Log Task Events

```python
# Log information events
analyzer.log_task_event("info", {"message": "Starting Google search"})

# Log warnings
analyzer.log_task_event("warning", {"message": "Slow network connection"})

# Log errors
analyzer.log_task_event("error", {
    "message": "Element not found",
    "type": "element_error",
    "details": {"selector": "#video-player"}
})
```

### Capture Screenshots

```python
# Capture screenshot at key points
screenshot_result = analyzer.capture_screenshot("Google search results")
print(f"Screenshot captured: {screenshot_result['screenshot_id']}")

# Screenshots are saved in task_screenshots/ directory
# Format: task_ID_screenshot_N.png
```

## 🔍 Analyzing Task Execution

### Complete Task Analysis

```python
# When task is complete, generate analysis report
report = analyzer.analyze_task_execution()

print(f"Task completed in {report['duration_seconds']} seconds")
print(f"Errors encountered: {report['error_count']}")
```

### View Analysis Report

```python
# Get detailed report
print(f"Task: {report['task_name']}")
print(f"Status: {report['status']}")

# View timeline
print("\nTimeline:")
for event in report['timeline']:
    print(f"  {event['time']} - {event['type']}: {event['message']}")

# View error analysis
if 'error_analysis' in report:
    print(f"\nError Analysis:")
    print(f"  Total errors: {report['error_analysis']['total_errors']}")
    print(f"  Error types: {report['error_analysis']['error_types']}")
    print(f"  Common patterns: {report['error_analysis']['common_patterns']}")

# View recommendations
print(f"\nRecommendations:")
for rec in report['recommendations']:
    print(f"  [{rec['priority']}] {rec['type']}: {rec['suggestion']}")
```

## 📊 Viewing Task History

```python
# Get all analyzed tasks
history = analyzer.get_task_history()

print(f"Total tasks analyzed: {len(history)}")

for task in history:
    print(f"\nTask: {task['name']}")
    print(f"  ID: {task['task_id']}")
    print(f"  Status: {task['status']}")
    print(f"  Duration: {task['metrics']['duration_seconds']}s")
    print(f"  Errors: {task['metrics']['error_count']}")
```

## 🔧 Advanced Features

### MCP Integration

The system integrates with MCP (Microservice Communication Protocol) for advanced analysis:

```python
# Check if MCP is available
if analyzer.mcp_available:
    print("✓ MCP integration available for advanced analysis")
    
    # Run system diagnostics
    diagnostics = analyzer.mcp_tool.diagnose_system()
    
    # Get quality gate status
    quality_gate = analyzer.mcp_tool.get_quality_gate_status("current_project")
```

### Custom Analysis

```python
# Add custom analysis to your tasks
def custom_analysis(task_data):
    """Add your custom analysis logic"""
    
    # Example: Check for specific patterns
    logs = task_data['logs']
    
    # Count specific events
    search_events = [log for log in logs if 'search' in log['data']['message'].lower()]
    
    return {
        'search_events': len(search_events),
        'custom_metric': 'your_custom_metric'
    }

# Add to your analysis
custom_results = custom_analysis(analyzer.current_task)
```

## 📁 File Structure

```
task_analysis_system/
├── task_analysis_system.py  # Main analysis system
├── task_analysis.log        # Main log file
├── task_screenshots/        # Screenshots from all tasks
│   ├── task_ID_screenshot_N.png
│   └── ...
└── task_logs/              # Log files and task data
    ├── task_ID.log          # Task-specific logs
    ├── task_ID_data.json    # Complete task data
    └── ...
```

## 🎯 Best Practices

### 1. Log Key Events

```python
# Log at each major step
analyzer.log_task_event("info", {"message": "Starting step 1"})
# ... execute step 1 ...
analyzer.log_task_event("info", {"message": "Step 1 completed"})
```

### 2. Capture Screenshots at Critical Points

```python
# Before important actions
analyzer.capture_screenshot("Before clicking button")
# ... perform action ...
analyzer.capture_screenshot("After clicking button")
```

### 3. Handle Errors Gracefully

```python
try:
    # Risky operation
    result = risky_operation()
    analyzer.log_task_event("info", {"message": "Operation successful"})
except Exception as e:
    analyzer.log_task_event("error", {
        "message": str(e),
        "type": "operation_error",
        "details": {"operation": "risky_operation"}
    })
    # Continue with fallback
```

### 4. Review Analysis Reports

```python
# After each task, review:
# 1. Timeline - Understand the flow
# 2. Error Analysis - Identify patterns
# 3. Recommendations - Implement improvements
```

## 📈 Example: Complete Task Analysis

```python
# Initialize
analyzer = TaskAnalyzer()

# Start task
analyzer.start_task_analysis("Web Automation", "Automate website interaction")

# Execute task with logging
try:
    # Step 1: Open browser
    analyzer.log_task_event("info", {"message": "Opening browser"})
    browser_result = open_browser("https://example.com")
    analyzer.capture_screenshot("Browser opened")
    
    # Step 2: Find element
    analyzer.log_task_event("info", {"message": "Finding login button"})
    element = find_element("#login-button")
    analyzer.capture_screenshot("Login button found")
    
    # Step 3: Click element
    analyzer.log_task_event("info", {"message": "Clicking login button"})
    click_result = click_element(element)
    analyzer.capture_screenshot("Login button clicked")
    
    # Complete successfully
    analyzer.log_task_event("info", {"message": "Task completed successfully"})
    
except Exception as e:
    analyzer.log_task_event("error", {
        "message": str(e),
        "type": "automation_error"
    })

# Generate report
report = analyzer.analyze_task_execution()

# Review and improve
print(f"Task completed with {report['error_count']} errors")
for rec in report['recommendations']:
    print(f"Recommendation: {rec['suggestion']}")
```

## 🎉 Benefits

1. **Comprehensive Logging** - Complete record of task execution
2. **Visual Debugging** - Screenshots at each step
3. **Error Analysis** - Automatic pattern detection
4. **Improvement Recommendations** - Actionable suggestions
5. **MCP Integration** - Advanced system diagnostics
6. **Task History** - Learn from past executions

## 🔧 Troubleshooting

### No Screenshots Captured

**Issue**: `screenshot_count` is 0

**Solution**:
- Check if `take_screenshot` function is available
- Verify screenshot directory permissions
- Add explicit screenshot calls at key points

### High Error Count

**Issue**: Many errors in task execution

**Solution**:
- Review error analysis for patterns
- Add specific error handling for common issues
- Improve element selectors and wait times

### Long Task Duration

**Issue**: Task takes too long

**Solution**:
- Review timeline to identify slow steps
- Add parallel execution where possible
- Optimize element finding strategies

## 📚 Advanced Usage

### Integrate with SonarQube

```python
# After task completion, run SonarQube analysis
if analyzer.mcp_available:
    sonarqube_result = analyzer.mcp_tool.run_sonarqube_analysis("project_id")
    
    # Get quality gate status
    quality_gate = analyzer.mcp_tool.get_quality_gate_status("project_id")
    
    # Add to your analysis
    report['sonarqube'] = {
        'analysis': sonarqube_result,
        'quality_gate': quality_gate
    }
```

### Custom Metrics

```python
# Add custom metrics to your analysis
def calculate_custom_metrics(task_data):
    """Calculate additional metrics"""
    
    # Example: Calculate efficiency
    duration = task_data['metrics']['duration_seconds']
    steps = len([log for log in task_data['logs'] if log['type'] == 'info'])
    
    if steps > 0:
        efficiency = duration / steps
        return {'steps_per_second': 1/efficiency}
    
    return {'steps_per_second': 0}

# Add to report
custom_metrics = calculate_custom_metrics(analyzer.current_task)
report['custom_metrics'] = custom_metrics
```

## 🎯 Summary

The Task Analysis System provides a comprehensive framework for:

1. **Executing tasks** with full logging and monitoring
2. **Capturing screenshots** at key execution points
3. **Analyzing results** with error detection and pattern recognition
4. **Generating recommendations** for code improvement
5. **Integrating with MCP** for advanced system diagnostics

Use this system to systematically improve your automation tasks and achieve better reliability and performance! 🚀