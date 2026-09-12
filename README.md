# ☄️ Meteor Space Dodge

**Meteor Space Dodge** is a 2D arcade survival game built with **Python and Pygame**. Take control of a spaceship, survive incoming meteors, and try to achieve the highest score possible.

The game focuses on fast reactions, movement, collision detection, increasing difficulty, and classic arcade-style gameplay.

## 🎮 Game Overview

You are piloting a spaceship through a dangerous meteor field.

Your objective is simple:

> **Survive the meteor crash for as long as possible!**

Avoid incoming meteors, stay alive, and improve your high score with every attempt.

## ✨ Features

- 🚀 Player-controlled spaceship
- ☄️ Falling/incoming meteors
- 💥 Collision detection
- ❤️ Multiple lives
- 🏆 Score and high-score system
- 📈 Increasing gameplay difficulty
- 🔊 Sound effects and game audio
- 🎨 Custom game assets
- 💾 High-score persistence
- 🖥️ Smooth 60 FPS gameplay
- 🔄 Game-over and restart functionality

## 🕹️ Controls

| Key | Action |
|---|---|
| `W` / `↑` | Move Up |
| `S` / `↓` | Move Down |
| `A` / `←` | Move Left |
| `D` / `→` | Move Right |
| `Space` | Start / Restart |
| `Esc` | Quit Game |

> Controls may vary depending on the current implementation.

## 🛠️ Technologies Used

- **Python 3**
- **Pygame** — 2D game engine
- **Flask & Flask-CORS** — Cloud backend REST API service & Web Dashboard
- **Neon PostgreSQL** — Serverless cloud database for global leaderboards & user profiles
- **Firebase Authentication** — Secure pilot identity management (Google OAuth & Email/Password)
- **JSON** — Local fallback and session cache

## 📂 Project Structure

```text
Meteor-Space-Dodge/
│
├── Assets/
│   ├── audio/                     # Sound effects & music
│   ├── images/                    # Spaceship & background textures
│   ├── main.py                    # Pygame desktop game client
│   ├── db_manager.py              # Neon PostgreSQL integration layer
│   ├── auth_manager.py            # Firebase Authentication integration
│   └── space_dodge_high_score.json # Local scores and backup
│
├── server.py                      # Flask REST API & Web Dashboard
├── requirements.txt               # Dependencies
└── README.md
```

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Desktop Game

```bash
python Assets/main.py
```

### 3. (Optional) Run the Flask Backend & Web Dashboard

```bash
python server.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser to view the live Neon DB leaderboard and API service health.


## 🎯 Gameplay

The game is designed around an endless survival loop:

```text
Start Game
    ↓
Control Spaceship
    ↓
Avoid Meteors
    ↓
Survive & Earn Score
    ↓
Difficulty Increases
    ↓
Collision
    ↓
Game Over
    ↓
Try Again
```

The longer you survive, the more challenging the game becomes.

## 🧠 Concepts Practiced

This project helped reinforce several Python and game-development concepts:

- Object-oriented programming
- Game loops
- Event handling
- Keyboard input
- Sprite/image handling
- Collision detection
- Randomized object spawning
- Timers and frame-rate management
- Game states
- Score management
- File handling
- JSON data storage
- Asset management
- Basic game architecture

## 🔊 Assets

Game visuals and audio are stored separately inside the `Assets` directory to keep the project organized.

If you replace or add assets, make sure the file paths used by the Python program match the actual asset locations.

## 📸 Screenshots

Screenshots can be added here as the project develops.

```markdown
![Gameplay Screenshot](Assets/screenshots/gameplay.png)
```

## 🔮 Future Improvements

Possible future upgrades include:

- 🌌 Animated space background
- ☄️ Multiple meteor types
- 🚀 Different playable spaceships
- 💥 Explosion animations
- 🛡️ Power-ups
- ❤️ Health system
- ⚡ Temporary speed boosts
- 🏆 Improved leaderboard system
- 🎚️ Difficulty selection
- ⏸️ Pause menu
- ⚙️ Settings menu
- 🎵 Background music
- 🖥️ Full-screen support
- 🎮 Controller support
- 📊 More detailed statistics
- 🎨 Improved UI and visual effects

## 📚 Learning Project

This project is part of my **Python Game Development Portfolio**, where I am building games to improve my programming, problem-solving, software design, and game-development skills.

More projects will be added as I continue learning and improving.

## 📜 License

This project is licensed under the **MIT License**.

See the [`LICENSE`](LICENSE) file for more information.

## 👨‍💻 Author

**Ghostofzenin08**

GitHub:  
https://github.com/Ghostofzenin08

---

⭐ If you find this project interesting, consider giving the repository a star!