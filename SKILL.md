---
name: petchat-standard
description: Comprehensive guidelines for PetChat (PyQt6 + Socket) development, enforcing architecture, protocol, clean code, and testing standards.
---

# PetChat Development Standards

## 1. Architectural Overview
The project follows a **Client-Server Architecture** using Python `socket` for networking and `PyQt6` for the GUI.

### 1.1 Core Components
* **Server (`server.py`)**:
    * Manages TCP connections using `ServerThread`.
    * Routes messages (Private P2P or Public Broadcast).
    * Centralizes AI processing via `AIService` + `QThreadPool`.
* **Client (`main.py`)**:
    * `PetChatApp`: Main controller, initializes `QApplication`, `Database`, `NetworkManager`.
    * **Architecture Constraint**: Heavy logic (AI, heavy DB ops) stays on Server; UI stays dumb.
* **Data Layer (`core/database.py`)**:
    * SQLite database (`petchat.db`). Access **only** via `Database` class methods.

### 1.2 Network Protocol (`core/protocol.py`)
* **Header**: Fixed 8 bytes (`>II`: 4-byte Length, 4-byte CRC32). **DO NOT MODIFY.**
* **Payload**: JSON.
* **Workflow**: When adding features, update `MessageType` Enum -> `server.py` routing -> `network.py` handling -> UI signals.

## 2. Coding Style & Habits

### 2.1 General Python Patterns
* **Type Hinting**: Mandatory for all function signatures.
* **No Comments**: 
    * **STRICTLY FORBIDDEN**: Inline comments explaining "what" the code does.
    * **ALLOWED**: Docstrings for complex class/method interfaces.
    * *Reason*: Keep code clean and readable via variable naming.
* **Dependencies**: Use only libs in `requirements.txt`. Do not add new deps without asking.

### 2.2 PyQt6 Patterns
* **Threading Safety**:
    * Network/DB I/O -> Background Thread.
    * UI Updates -> **MUST** use `pyqtSignal` to Main Thread.
    * Never call `self.widget.setText()` from a socket thread.
* **Styling**: Use `ui.theme.Theme` constants. No hardcoded hex colors.

## 3. Testing & Verification (CRITICAL)
Before finishing a task, verify changes:
* **Network/Protocol**: Run `python tests/network_test.py`.
* **Server Logic**: Run `python tests/verify_cs_server.py`.
* **Stress Checks**: Run `python tests/stress_test.py` for concurrency changes.

## 4. File Organization
(Keep your existing tree structure here, it is perfect)