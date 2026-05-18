# AgenticOS: Ultimate PC Control and Operating System Orchestration Roadmap

This document outlines the high-fidelity technical roadmap and architectural specifications for upgrading AgenticOS to achieve absolute, unrestricted control over the host operating system, GUI software, and physical execution environments.

---

## 1. Multi-Modal Visual Coordinate Mapping (Florence-2 / Local Vision)

Text-based accessibility APIs and optical character recognition (OCR) are insufficient when dealing with highly dense, graphic-heavy, or proprietary applications that do not expose structural labels (e.g., Adobe Photoshop, AutoCAD, Blender, or video game engines).

### Technical Solution:
Implement a local vision pipeline that feeds desktop screenshots into a specialized, low-latency vision-language model (e.g., Florence-2 or a customized MobileNet) to calculate precise click boundaries.

```text
+-----------------------+      +------------------------+      +-----------------------+
|  High-Res Desktop     | ---> |  Local Vision Model    | ---> |  Coordinate Mapping   |
|  Screenshot Capture   |      |  ( Florence-2-base )   |      |  "Click Button [OK]"  |
+-----------------------+      +------------------------+      +-----------------------+
                                                                           |
                                                                           v
                                                               +-----------------------+
                                                               |  Hardware Injection   |
                                                               |  Mouse Click (X, Y)   |
                                                               +-----------------------+
```

### Proposed Changes:
#### [NEW] [vision_coordinator.py](../tools/plugins/vision_coordinator.py)
- **`click_element_by_name(label)`**: Captures the screen, feeds it to the local VLM with the prompt `<CAPTION_TO_LOCALIZATION>`, extracts bounding boxes matching the label, computes the center coordinate, and commands the mouse to click.
- **`drag_and_drop_visual(source, destination)`**: Computes visual paths between two desktop components and performs a smooth mouse drag.

---

## 2. Low-Level OS-Native Input Daemons

Executing inputs using basic user-space libraries (like Python's default `pyautogui`) can cause silent failures when running in privileged environments, such as security prompts, lock screens, or administrative terminals (User Account Control / UAC on Windows).

### Technical Solution:
Implement platform-specific elevated daemons running with system privileges that communicate with AgenticOS via local inter-process communication (IPC / Named Pipes).

```text
[ Windows ] ---> Dyn-compiled C# via PowerShell utilizing Win32 SendInput API
[ macOS ]   ---> CoreGraphics event taps and AXUIElement references via PyObjC
[ Linux ]   ---> Low-level evdev device injection bypassing display server limitations
```

### Proposed Changes:
#### [MODIFY] [keyboard.py](../tools/terminal/keyboard.py)
- Refactor the input emulations to channel all keystrokes and button clicks directly through the high-privilege IPC daemon, guaranteeing that the agent remains functional even when administrative prompts are displayed on the screen.

---

## 3. Dynamic User-Profile Software Adapters

Traditional browser tools operate within fresh, sandboxed browser profiles. This prevents the agent from leveraging the operator's active, logged-in browser cookies, session histories, or locally active development workspaces.

### Technical Solution:
Implement dynamic connectors that attach programmatically to the user's running applications using standard remote debugging interfaces.

```text
+---------------------------+       Attach via DevTools       +---------------------------+
|  User's Live Chrome App   | <============================== |  AgenticOS Browser Tool   |
|  ( Port 9222 / Logged-in )|       Protocol ( WebSockets )   |  ( Remote Tab Control )   |
+---------------------------+                                 +---------------------------+
```

### Proposed API Hooks:
1. **Google Chrome & Edge**: Start the user's browser with `--remote-debugging-port=9222`. The agent connects to this port using a WebSocket client, allowing it to navigate, read, and write on tabs where the user is already authenticated (e.g. Gmail, GitHub, corporate portals).
2. **VS Code Extension Host**: Inject commands directly into the active VS Code window via standard CLI execution pathways or an embedded extension listener.

---

## 4. Dynamic Self-Provisioning and Auto-Compiler

When a user issues an arbitrary request that requires software not currently installed on the host machine (e.g., *"Convert this WAV file to a 320kbps MP3"*), standard agent pipelines crash due to missing binaries (e.g., FFmpeg).

### Technical Solution:
Create an autonomous **Self-Provisioning Compiler Engine** that identifies, downloads, compiles, and registers missing software runtimes dynamically without operator intervention.

```text
User Command ---> Detect Missing Dependency ---> Query System Package Managers (winget/brew/apt)
                                                                   |
                                                                   v
Inject Hot-Reloaded @tool class <--- Compile Wrapper <--- Silent-Install CLI Tool Programmatically
```

### Proposed Changes:
#### [NEW] [self_provisioner.py](../core/self_provisioner.py)
- Detects standard CLI errors (e.g. `FileNotFoundError` or command not in path).
- Automatically queries the correct platform package manager:
  - **Windows**: `winget install <package> --silent` or `choco install <package> -y`
  - **macOS**: `brew install <package>`
  - **Linux**: `apt-get install <package> -y` or `yum install <package> -y`
- Validates binary installation, writes a clean `@tool` Python class inside `tools/plugins/`, and calls the dynamic registry hot-reload sequence.

---

## 5. Asynchronous OS Event Bus

AgenticOS operates strictly on a synchronous, request-response execution cycle. It has no way to respond dynamically to asynchronous, system-level hardware events that occur during idle periods.

### Technical Solution:
Introduce an **Asynchronous Hardware Event Bus** that listens to background operating system signals and updates the active context.

```text
+---------------------------------------------------------------------------------+
|                          ASYNCHRONOUS OS EVENT BUS                              |
+---------------------------------------------------------------------------------+
   |                             |                             |
   v                             v                             v
[ Battery < 10% ]        [ Network Drop ]             [ CPU Spike > 90% ]
   |                             |                             |
   +-----------------------------+-----------------------------+
                                 |
                                 v
                     [ Autonomic Action Loop ]
         "Battery critical. Switching to power-save profiles."
```

### Proposed Changes:
#### [NEW] [event_bus.py](../core/event_bus.py)
- Runs a background thread monitoring battery status, network connectivity, process counts, and CPU temperatures.
- Dispatches autonomic interrupt events into the agent's short-term reasoning chain, prompting the agent to launch stabilizing procedures before a system crash occurs.

---

*Last Updated: 2026-05-18*
*Status: Ultimate PC Control Blueprint Approved*

---

# Phase 2: Native Accessibility Tree Integration (Proposed)

Following the successful realization of all five Module structures in Phase 1, we propose the architectural blueprint for **Phase 2: Native Accessibility Tree Crawler**.

## 6. Native Accessibility Tree Crawler

Visual OCR-based coordinate mapping (`vision_coordinator.py`) is exceptionally robust for graphical elements but carries rendering overhead. Accessibility tree inspections provide instant, structural window bounds.

### Technical Solution:
Create a dual-engine visual coordinator. It first inspects the OS structural accessibility tree to locate the target label's exact pixel boundary:
* **Windows**: Query the `UI Automation` framework via a C# assembly compiled on-the-fly.
* **macOS**: Crawl application `AXUIElement` references via PyObjC.
* **Linux**: Query `at-spi2` dbus interfaces.

If the structural crawler fails (e.g., in Blender or a graphic game engine), the coordinator falls back to high-fidelity visual OCR coordinate mapping!

```text
               [ Search for Element "File" ]
                             |
              +--------------+--------------+
              |                             |
              v (Try First)                 v (Fallback)
      [ Accessibility Tree ]         [ Visual OCR Mapping ]
      - Windows UI Automation        - WinRT / Tesseract OCR
      - macOS AXUIElement            - Phrase Match & Center Map
              |                             |
              +--------------+--------------+
                             |
                             v
                 [ Return Click Coordinates ]
```
