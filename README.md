# Vector Velocity

A real-time 3D arcade highway racing game built from scratch using **Python** and **PyOpenGL**. The project implements fixed-function OpenGL rendering, procedural track generation, numerical physics integration with collision detection, and finite-state agent behavior.

---

## Game Modes

Vector Velocity features three distinct gameplay modes selectable from the interactive main menu:

### 1. Race Mode
* **Objective:** Compete against autonomous AI opponents across a designated number of laps (configurable via game settings).
* **Mechanics:** Features a pre-race countdown timer, localized vehicle physics calculating drift and body roll during cornering, and real-time checkpoint-based placement tracking.

### 2. Free Roam
* **Objective:** Explore an endless procedurally generated highway at your own pace.
* **Mechanics:** Designed for benchmarking vehicle handling, top speeds, and rendering performance without timers or collision penalties.

### 3. Arcade Survival Mode
* **Objective:** Navigate an increasingly fast obstacle course while collecting spinning coins to maximize score.
* **Mechanics:**
  * **Auto-Acceleration:** The vehicle accelerates automatically after the countdown and continually pushes toward target tier velocities.
  * **Tactical Braking:** Engaging the brake progressively slows the vehicle to negotiate dense hazard clusters.
  * **Dynamic Speed Scaling:** Target speed scales progressively with distance traveled:
    * **0 m – 1,000 m:** 30 km/h (Base tier)
    * **1,000 m – 1,800 m:** 45 km/h
    * **1,800 m+:** 60 km/h (+15 km/h added to top speed per additional 1,000 meters).

---

## Controls

| Key / Input | Action |
| :--- | :--- |
| **`W`** | Accelerate (Race / Free Roam) |
| **`S`** | Brake / Reverse (Race) / Tactical Brake (Arcade Mode) |
| **`A` / `D`** | Steer Left / Right |
| **`Spacebar`** | Nitrous Oxide (N2O) Boost |
| **`P`** | Pause / Resume Game |
| **`M`** | Return to Main Menu (Pause / Post-Game) |
| **`Right Click`** | Toggle Camera View (Chase Cam $\leftrightarrow$ Hood Cam) |
| **`Arrow Keys`** | Adjust Camera Elevation and Swing Angle (Chase Cam) |

---

## Technical Implementation

### 1. OpenGL Rendering Pipeline (Immediate Mode)
* **Primitive Rendering & Transformations:** Implemented using PyOpenGL immediate mode primitives (`GL_QUADS`, `GL_TRIANGLES`, `GL_LINES`) organized via hierarchical matrix stack transformations (`glPushMatrix`, `glPopMatrix`).
* **Projection & Viewport:** Employs `gluPerspective` for 3D projection alongside `gluLookAt` camera management supporting both third-person chase perspective (with spherical coordinate adjustments) and first-person hood perspective.
* **Lighting, Fog, & Atmosphere:** Implements depth testing (`GL_DEPTH_TEST`), dynamic double-buffering (`glutSwapBuffers`), atmospheric fog attenuation (`GL_FOG`) for visual depth, and a dynamic day/night cycle with illuminated window matrix geometry.

### 2. Custom Physics Engine & Numerical Integration
* **Fixed Time-Step Accumulator:** Physics calculations are decoupled from hardware display refresh rates using a fixed delta-time accumulator pattern running at a deterministic 60 Hz. This guarantees consistent simulation behavior across different hardware configurations and variable refresh rates (60 Hz, 144 Hz+).
* **Vehicle Dynamics:** Simulates longitudinal acceleration curves, progressive braking friction, top-speed governors with N2O multipliers, lateral steering responsiveness, and centrifugal body roll and drift angles.
* **Collision Detection:** Utilizes bounding volume and Axis-Aligned Bounding Box (AABB) intersection testing for vehicle-to-obstacle, track boundary, and collectible coin collisions.

### 3. Finite State Machine (FSM)
* **Game State Management:** Structured using a finite state machine pattern cleanly governing state transitions across `MAIN_MENU`, `RACING`, `FREE_ROAM`, `ARCADE`, `PAUSED`, and `GAME_OVER`.
* **State Encapsulation:** Ensures input routing, simulation updates, and HUD rendering are decoupled and handled per active state.

### 4. Procedural Content Generation (PCG)
* **Infinite Highway Streaming:** Road segments, environmental scenery (buildings, pillars, vegetation), and randomized hazard obstacles spawn dynamically ahead of the camera view frustum.
* **Resource Optimization:** Assets falling behind the camera viewport are automatically culled and reclaimed, maintaining a constant $O(1)$ memory footprint throughout extended play sessions.

### 5. AI Opponent Dynamics
* **Autonomous Driving Agents:** Multi-car competition driven by AI agents utilizing waypoint tracking, dynamic velocity adjustment, and lane-selection heuristics.
* **Checkpoint Evaluation:** Evaluates race placements and lap completion dynamically through checkpoint gating.

---

## Built With

* **Python 3** (Python 3.8+)
* **PyOpenGL** & **PyOpenGL_accelerate** - Python bindings for OpenGL graphics
* **GLUT / FreeGLUT** - Window management, I/O event dispatch, and frame timing

---

## Installation & Setup

### Prerequisites
* **Python 3.8+** installed on your system. Verify with:
  ```bash
  python --version
  ```

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thinkiamparanoid2/OpenGl_Racing_Game.git
   cd OpenGl_Racing_Game
   ```

2. **Install required dependencies:**
   ```bash
   pip install PyOpenGL PyOpenGL_accelerate
   ```

   > **Note for Windows Users:** If GLUT binaries are missing or you encounter `OpenGL.error.NullFunctionError`, ensure FreeGLUT binaries are available or install the appropriate pre-compiled wheels for PyOpenGL.

### Running the Application

Execute the main game script from the root directory:
```bash
python RACE_RACER.py
```

---

## License

This project is licensed under the MIT License.
