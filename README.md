# DrawGuess
This is a project for Macao University of Science And Technology CS374 course

**DrawGuess** is a Local Area Network (LAN) multiplayer "Draw & Guess" game (similar to Pictionary) developed with Python 3 and PyQt5.

It features real-time drawing synchronization, a chat/guessing system, automatic scoring, and a round-based game loop.

## 📂 Project Structure

```text
DrawGuess/
├── Client/
│   ├── main.py          # Entry point for the Client
│   ├── ui_main.py       # Main GUI logic
│   ├── draw_widget.py   # Custom drawing canvas widget
│   └── network.py       # Networking thread (Client-side)
├── Server/
│   └── server.py        # Entry point for the Server
├── Shared/
│   └── protocol.py      # Communication protocol definition
├── words.txt            # Vocabulary list for the game
└── README.md
```

## 🛠️ Prerequisites & Installation

### 1. System Requirements
- **Python 3.10** or higher is required.

### 2. Install Dependencies
The project relies on **PyQt5** for the Graphical User Interface.

Open your terminal or command prompt and run:

```bash
pip install PyQt5
```
*(Note: If you are using a virtual environment, make sure it is activated before installing.)*

---

## 🚀 How to Run

To play the game, you need to run **one Server** instance and **multiple Client** instances (at least two players are required to start a game).

### Step 1: Start the Server
The server manages the game state and communication. It must be started first.

1. Open a terminal in the project root directory.
2. Run the server script:
   ```bash
   python Server/server.py
   ```
   *You should see a message indicating the server is listening (e.g., `[SERVER] Listening on 0.0.0.0:9000`).*

### Step 2: Start the Clients
Open new terminal windows for each player.

1. Open a new terminal.
2. Run the client script:
   ```bash
   python Client/main.py
   ```
3. A window will appear. Enter a unique **Nickname** when prompted.
4. Repeat this step for other players.

---

## 🎮 How to Play

1. **Connect & Ready Up:**
   - After entering your nickname, you will see the game lobby.
   - Click the **"Ready"** button at the bottom right.
   - The game will start automatically once **all** connected players are "Ready".

2. **The Game Loop:**
   - **The Drawer:** One player is randomly selected to draw. A popup will show the secret word (e.g., "Apple"). You must draw it on the canvas. *Note: You cannot chat while drawing.*
   - **The Guessers:** Other players must guess the word by typing into the chat box and pressing "Send" (or Enter).
   
3. **Winning the Round:**
   - The first player to type the correct word wins the round.
   - Points are awarded, and the round ends.
   - All players must click **"Ready"** again to start the next round.

---

## ⚙️ Configuration (LAN Play)

By default, the Client connects to `127.0.0.1` (localhost). To play with friends on different computers within the same Wi-Fi/LAN:

1. **Server:**
   - Ensure the server computer's firewall allows traffic on port `9000`.
   - Find the server's local IP address (e.g., `192.168.1.5`).

2. **Client:**
   - Open `Client/main.py`.
   - Change the `host` variable to the server's IP address:
     ```python
     # In Client/main.py
     host = "192.168.1.5"  # Replace with your Server's IP
     port = 9000
     ```

---

## 📝 Features

- **Real-time Synchronization:** Drawing strokes are broadcasted instantly to all players.
- **Drawing Tools:** Select from multiple colors and brush sizes (Thin/Mid/Thick).
- **Game Logic:** Automatic word selection, role assignment (Drawer/Guesser), and score tracking.
- **Robust Networking:** Handles player disconnections gracefully.
- **Modern UI:** Clean PyQt5 interface with styled components.