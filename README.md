# Project Atlas (Kinotavr)

**Vision-Augmented Agentic OS Controller for macOS**

Atlas is a local "neural operator" for macOS that sees the screen, plans actions, and executes them through a strict low-level tool interface. It is designed to act as a high-level cognitive layer over the OS, capable of complex tasks ranging from system management to web automation.

## Core Architecture: The Trinity

The system operates via a graph of specialized agents ("The Trinity"):

1.  **Atlas (Architect):** Strategist and planner. Decomposes user requests into execution plans.
2.  **Tetyana (Executor):** Universal operator. Executes tools for OS control, browser automation, and development.
3.  **Grisha (Visor/Security):** Quality assurance and security. Verifies actions via visual feedback (Vision) and enforces safety rules.

## Capabilities

### 1. System Control
- **Process Management:** Real-time visibility of running processes (`psutil`). Ability to list and terminate applications.
- **System Stats:** Monitoring of CPU, RAM, and Disk usage.
- **Native Automation:** AppleScript and shell integration for low-level OS interaction.

### 2. Desktop Awareness
- **Vision:** "Sees" open windows, their titles, positions, and sizes (`Quartz`).
- **Multi-Monitor:** Understands multi-display layouts.
- **Clipboard:** Bidirectional clipboard access (`NSPasteboard`).

### 3. Browser Automation
- **Playwright engine:** Robust, selector-based web interaction.
- **Features:** Open URLs, click elements, type text, execute JavaScript, and read DOM content.
- **No "Blind Clicks":** Interacts with the web page structure directly for reliability.

### 4. Code & Development
- **Dev Subsystem:** Integration with Windsurf IDE and CLI for coding tasks.
- **RAG Memory:** Learns from past actions and stores successful strategies.

## Installation & Setup

1.  **Environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install
    ```

3.  **Permissions:**
    The terminal/IDE running Atlas must have the following macOS permissions:
    - Accessibility
    - Screen Recording
    - Automation

## Usage

Run the system CLI:

```bash
python3 main.py
```
