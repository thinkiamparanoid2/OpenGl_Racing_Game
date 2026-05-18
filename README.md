# Vector Velocity 🏎️💨

An arcade-inspired 3D highway racing game built from scratch using **Python** and **PyOpenGL**. The project features custom procedural generation, multiple gameplay states, an advanced physics engine with manual and automated controls, and a dynamic environment system.

---

## 🎮 Game Modes

Vector Velocity features three distinct gameplay styles selectable from the main menu:

### 1. Race Mode
* **Objective:** Compete against responsive AI opponents across a designated number of laps (fully customizable via settings).
* **Mechanics:** Includes a 3-second countdown timer. Features localized physics calculations for drift/body roll when turning and a dynamic finish placement calculator based on final position checkpoints.

### 2. Free Roam
* **Objective:** Explore the endless procedural highway at your own pace.
* **Mechanics:** Ideal for testing top speeds, handling, or exploring the environment without the pressure of a timer or collisions.

### 3. Arcade Mode (Temple Run Style)
* **Objective:** Survive an increasingly fast obstacle course while collecting spinning gold coins to maximize your score.
* **Mechanics:** * **Auto-Acceleration:** The car automatically speeds off at the "GO!" countdown and constantly pushes toward its target tier velocity.
  * **Tactical Braking:** Holding `S` activates a progressive, realistic brake mechanism to slow down safely and navigate tricky hazard layouts.
  * **Infinite Distance Scaling:** The game's target speed dynamically scales the further you travel:
    * **0m – 1000m:** 30 km/h (Starting tier)
    * **1000m – 1800m:** 45 km/h
    * **1800m+:** 60 km/h (With an additional **+15 km/h** added to top speed for every 1000 meters traveled beyond that point).

---

## 🚀 Key Technical Features

* **Fixed Time Step Execution:** Physics updates are securely decoupled from hardware refresh rates using a delta-time accumulator loop. The logic runs at a consistent 60 FPS across all devices (60Hz, 144Hz, etc.), preventing game-speed anomalies on high-end hardware.
* **Nitrous Oxide (N2O) Boost:** Pressing `Spacebar` activates a massive acceleration multiplier and extends your top speed cap by 40%. Includes a dedicated HUD meter that drains dynamically and slowly regenerates when empty.
* **Dynamic Time of Day:** Players can choose between Day and Night settings. Night mode transforms the environment with custom fog/sky color blending and self-illuminated neon matrix building windows.
* **Procedural Hazard & Asset Spawning:** Obstacles, scenery (cacti, pillars, trees, buildings), and collectibles spawn dynamically ahead of the camera viewport and automatically clear out once they fall behind the car to conserve memory.

---

## ⌨️ Controls

| Key | Action |
| :--- | :--- |
| **`W`** | Accelerate (Race / Free Roam) |
| **`S`**| Brake / Reverse (Race) / Tactical Brake (Arcade Mode) |
| **`A` / `D`** | Steer Left / Right |
| **`Spacebar`** | Activate Nitrous Oxide (N2O) Boost |
| **`P`** | Pause / Resume Game |
| **`M`** | Return to Main Menu (From Pause or Post-Game screens) |
| **`Right Click`** | Toggle Camera View (Chase Cam $\leftrightarrow$ Hood Cam) |
| **`Arrow Keys`** | Adjust Camera Height and Swing Angle (Chase Cam only) |

---

## 🛠️ Installation & Setup

### Prerequisites
Ensure you have Python installed on your computer. You will need to install the required OpenGL bindings.
