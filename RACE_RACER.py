import math
import random
import time
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
class GameState:
    pass

config = GameState()
config.last_time = time.time()  # Tracks real-world time
config.accumulator = 0.0        # Stores leftover time between frames

# State Constants
config.STATE_MENU     = 0
config.STATE_RACE     = 1
config.STATE_FREE_ROAM = 2
config.STATE_PAUSED   = 3
config.STATE_ARCADE   = 5       # NEW: Arcade coin-collect mode
config.current_state  = config.STATE_MENU
config.resume_state   = config.STATE_RACE  # remembers which state to resume on unpause

# Menu & Settings
config.current_menu_selection = 0
config.setting_laps        = 3
config.setting_opponents   = 2
config.setting_difficulty  = "Normal"
config.setting_collisions  = True
config.setting_sensitivity = 2.0

def get_menu_options():
    return [
        "Start Race",
        "Free Roam",
        "Arcade Mode",                              # NEW index 2
        f"Laps: {config.setting_laps}",             # index 3
        f"Difficulty: {config.setting_difficulty}", # index 4
        f"Collisions: {'ON' if config.setting_collisions else 'OFF'}",  # index 5
        f"Sensitivity: {round(config.setting_sensitivity, 1)}"          # index 6
    ]

# Camera Configuration
config.CAM_CHASE        = 0
config.CAM_HOOD         = 1
config.current_camera   = config.CAM_CHASE
config.cam_height_offset = 50.0
config.cam_swing_angle  = 0.0

# Physics & Player Car
config.MAX_SPEED      = 15.0
config.FRICTION       = 0.96          # applied EVERY frame -- was missing before!
config.THRUST         = 0.45
config.BRAKE_FORCE    = 0.40
config.MAX_WHEEL_ANGLE = 30.0

config.car_pos           = [0.0, 0.0, 0.0]
config.car_velocity      = [0.0, 0.0, 0.0]
config.car_facing_angle  = 0.0          # degrees, 0 = moving along +Z axis
config.current_wheel_angle = 0.0

config.keys_pressed = {b'w': False, b's': False, b'a': False, b'd': False, b' ': False}

config.boost_amount = 100.0
config.boost_max = 100.0

# Race Progress
config.current_lap      = 1
config.race_start_time  = 0.0
config.current_race_time = 0.0
config.race_finished    = False
config.score            = 0            # distance-based score for endless mode
config.player_waypoint  = 0

# AI Opponents
config.ai_cars = []

def init_ai(num_opponents, difficulty):
    config.ai_cars = []
    num_opponents = 2 # Force exactly 2 AI opponents for the race (total 3 cars)
    
    # Calculate player's TRUE top speed due to friction equilibrium
    # Formula: terminal_velocity = thrust / (1 - friction)
    player_true_top_speed = config.THRUST / (1.0 - config.FRICTION)

    if difficulty == "Easy":
        # Roughly 84% of player's actual top speed
        speed_min = player_true_top_speed * 0.82
        speed_max = player_true_top_speed * 0.84
    elif difficulty == "Hard":
        # Exact same top speed as player
        speed_min = player_true_top_speed * 0.98
        speed_max = player_true_top_speed * 1.00
    else: # Normal
        # Roughly 89-92% of player's actual top speed
        speed_min = player_true_top_speed * 0.89
        speed_max = player_true_top_speed * 0.92

    # Ensure AI acceleration is much lower than player acceleration 
    # (Player thrust is 0.25, we give AI 0.03 so you can easily catch up)
    ai_acceleration = 0.03

    # Place them behind the player at the start line
    lanes = [-LANE_OFFSET, LANE_OFFSET] 
    for i in range(num_opponents):
        lane = lanes[i % 2]
        config.ai_cars.append({
            "pos": [lane, 0.0, -40.0],   # Start 40 units behind the player
            "max_speed": random.uniform(speed_min, speed_max),
            "accel": ai_acceleration,    # New variable for slower acceleration
            "lane": lane,
            "lane_change_timer": random.uniform(3.0, 7.0),
            "facing_angle": 0.0,
            "velocity_z": 0.0
        })
# ==========================================
# ARCADE MODE - Variables & Constants
# ==========================================
config.arcade_lives         = 3
config.arcade_score         = 0       # coins collected
config.arcade_distance      = 0       # metres driven
config.arcade_speed         = 6.0     # starts slow, ramps up
config.arcade_game_over     = False
config.arcade_coin_rotation = 0.0     # shared spin angle for all coins
config.arcade_next_spawn_z  = 200.0   # Z where next batch will be placed
config.arcade_coins         = []      # each entry: [x, y, z, collected_bool]
config.arcade_obstacles     = []      # each entry: [x, y, z, hit_bool]

ARCADE_SPAWN_DIST  = 500.0   # how far ahead to pre-spawn objects
ARCADE_COIN_RADIUS = 18.0    # collect distance
ARCADE_HIT_RADIUS  = 16.0    # obstacle collision distance


def reset_arcade():
    """Reset all arcade state for a fresh run."""
    config.car_pos            = [0.0, 0.0, 0.0]
    config.car_velocity       = [0.0, 0.0, 0.0]
    config.car_facing_angle   = 0.0
    config.current_wheel_angle= 0.0
    config.cam_swing_angle    = 0.0
    config.cam_height_offset  = 50.0
    config.current_camera     = config.CAM_CHASE
    config.race_start_time    = time.time()
    config.last_time          = time.time()
    config.accumulator        = 0.0
    config.race_finished      = False
    config.ai_cars            = []          # no AI in arcade
    # Arcade-specific reset
    config.arcade_lives         = 3
    config.arcade_score         = 0
    config.arcade_distance      = 0
    config.arcade_speed         = 3.33
    config.arcade_game_over     = False
    config.arcade_coin_rotation = 0.0
    config.arcade_next_spawn_z  = 200.0
    config.arcade_coins         = []
    config.arcade_obstacles     = []


def _generate_arcade_batch(z_start):
    """
    Spawn one 'wave' of coins + optional obstacles starting at z_start.
    Patterns:
      coins_line   – 5 coins in a straight lane (easy collect)
      coins_zigzag – 6 coins weaving across all 3 lanes
      obstacle_one – 1 barrier, coins in the other 2 lanes
      obstacle_two – 2 barriers, coins only in the 1 free lane
    """
    lanes = [-LANE_OFFSET, 0.0, LANE_OFFSET]

    # Difficulty scales with distance: more obstacles as you go further
    dist_km = config.car_pos[2] / 1000.0
    obs_chance = min(0.7, 0.2 + dist_km * 0.08)  # 20% at start, up to 70%

    if random.random() > obs_chance:
        # Pure coin pattern
        pattern = random.choice(['coins_line', 'coins_zigzag'])
    else:
        pattern = random.choice(['obstacle_one', 'obstacle_two'])

    if pattern == 'coins_line':
        lane = random.choice(lanes)
        for i in range(5):
            config.arcade_coins.append([lane, 8.0, z_start + i * 25.0, False])

    elif pattern == 'coins_zigzag':
        for i in range(6):
            lane = lanes[i % 3]
            config.arcade_coins.append([lane, 8.0, z_start + i * 28.0, False])

    elif pattern == 'obstacle_one':
        blocked = random.choice(lanes)
        config.arcade_obstacles.append([blocked, 0.0, z_start, False])
        # Put coins in the two clear lanes to guide the player
        for l in lanes:
            if l != blocked:
                config.arcade_coins.append([l, 8.0, z_start + 15.0, False])

    elif pattern == 'obstacle_two':
        blocked = random.sample(lanes, 2)
        free = [l for l in lanes if l not in blocked][0]
        for bl in blocked:
            config.arcade_obstacles.append([bl, 0.0, z_start, False])
        # Coins only in the one free lane
        for i in range(4):
            config.arcade_coins.append([free, 8.0, z_start + i * 20.0, False])


def update_arcade_objects():
    """Spawn new batches ahead of player, remove objects far behind."""
    pz = config.car_pos[2]

    # Keep spawning batches until we have objects far enough ahead
    while config.arcade_next_spawn_z < pz + ARCADE_SPAWN_DIST:
        _generate_arcade_batch(config.arcade_next_spawn_z)
        # Gap between batches shrinks as speed increases (harder)
        gap = max(90.0, 160.0 - config.arcade_speed * 2.0)
        config.arcade_next_spawn_z += gap + random.uniform(-20.0, 20.0)

    # Clean up objects more than 150 units behind
    config.arcade_coins     = [c for c in config.arcade_coins     if c[2] > pz - 150]
    config.arcade_obstacles = [o for o in config.arcade_obstacles if o[2] > pz - 150]


def update_arcade_physics():
    """
    Arcade physics: car speed is tied to distance driven (score-based tiers).
    S key brakes naturally over time; releasing S recovers speed back to the
    current tier target automatically.
    """
    if config.arcade_game_over:
        return

    # --- Distance-based target speed (km/h) ---
    # FIXED: Swapped 'config.arcade_score' (coins) to 'config.arcade_distance' (meters)
    distance = config.arcade_distance
    
    if distance < 1000:
        target_kmh = 30.0
    elif distance < 1800:
        target_kmh = 45.0
    else:
        # For every 1000 meters from 1800 onwards, add 15 km/h to the top speed
        bonus_tiers = (distance - 1800) // 1000
        target_kmh = 60.0 + (bonus_tiers * 15.0)

    # Convert the target km/h into the engine's internal speed unit
    target_speed = target_kmh / 9.0

    # --- S key = Natural Brake ---
    if config.keys_pressed[b's']:
        # Gentle, gradual deceleration instead of instantly slamming to 0
        config.arcade_speed -= 0.08  
        if config.arcade_speed < 0.0:
            config.arcade_speed = 0.0
    else:
        # Ramp smoothly back toward the tier target
        if config.arcade_speed < target_speed:
            config.arcade_speed += 0.03  # Smooth acceleration
        elif config.arcade_speed > target_speed:
            config.arcade_speed -= 0.02  # Bleed off tiny overshoots or brake momentum

    # --- STEERING ---
    target_wheel = 0.0
    if config.keys_pressed[b'a']:
        target_wheel =  config.MAX_WHEEL_ANGLE * 0.85
    elif config.keys_pressed[b'd']:
        target_wheel = -config.MAX_WHEEL_ANGLE * 0.85

    step = config.setting_sensitivity
    if config.current_wheel_angle < target_wheel:
        config.current_wheel_angle = min(config.current_wheel_angle + step, target_wheel)
    elif config.current_wheel_angle > target_wheel:
        config.current_wheel_angle = max(config.current_wheel_angle - step, target_wheel)

    # Lateral shift from wheel angle
    lateral = config.current_wheel_angle * 0.14
    config.car_pos[0] += lateral

    # Road boundary clamp
    config.car_pos[0] = max(-ROAD_HALF + 12, min(ROAD_HALF - 12, config.car_pos[0]))

    # Forward movement
    config.car_pos[2] += config.arcade_speed

    # Set velocity so the car model tilts correctly
    config.car_velocity[2] = config.arcade_speed
    config.car_velocity[0] = lateral * 5.0

    config.arcade_distance = int(config.car_pos[2] / 10)

def check_arcade_collisions():
    """Coin pickup and obstacle hit detection."""
    if config.arcade_game_over:
        return

    px = config.car_pos[0]
    pz = config.car_pos[2]

    # Coin collection
    for coin in config.arcade_coins:
        if not coin[3]:
            dx = px - coin[0]
            dz = pz - coin[2]
            if math.sqrt(dx*dx + dz*dz) < ARCADE_COIN_RADIUS:
                coin[3] = True           # mark collected
                config.arcade_score += 1

    # Obstacle collision
    for obs in config.arcade_obstacles:
        if not obs[3]:
            dx = px - obs[0]
            dz = pz - obs[2]
            if math.sqrt(dx*dx + dz*dz) < ARCADE_HIT_RADIUS:
                obs[3] = True            # mark hit so we don't double-count
                config.arcade_lives -= 1
                # Push the car sideways away from the barrier
                push = 1.0 if dx >= 0 else -1.0
                config.car_pos[0] += push * 5.0
                if config.arcade_lives <= 0:
                    config.arcade_game_over = True


# ---- Arcade Rendering ----

def draw_arcade_sky():
    """Sunset gradient: dark purple at top → bright orange at horizon."""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glBegin(GL_QUADS)
    glColor3f(0.15, 0.02, 0.25)   # deep purple top
    glVertex2f(-1,  1)
    glVertex2f( 1,  1)
    glColor3f(1.0, 0.38, 0.05)    # orange horizon
    glVertex2f( 1, -1)
    glVertex2f(-1, -1)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_arcade_ground():
    """Sandy desert floor on either side of the road."""
    GROUND_HALF = 800.0
    pz = config.car_pos[2]
    Z_NEAR = pz - 400.0
    Z_FAR  = pz + 800.0

    glColor3f(0.76, 0.60, 0.34)   # sand colour
    glBegin(GL_QUADS)
    glVertex3f(-GROUND_HALF, 0.0, Z_NEAR)
    glVertex3f(-ROAD_HALF,   0.0, Z_NEAR)
    glVertex3f(-ROAD_HALF,   0.0, Z_FAR)
    glVertex3f(-GROUND_HALF, 0.0, Z_FAR)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f( ROAD_HALF,   0.0, Z_NEAR)
    glVertex3f( GROUND_HALF, 0.0, Z_NEAR)
    glVertex3f( GROUND_HALF, 0.0, Z_FAR)
    glVertex3f( ROAD_HALF,   0.0, Z_FAR)
    glEnd()


def draw_arcade_road():
    """Dark purple neon-lit road with cyan/purple lane markings."""
    pz       = config.car_pos[2]
    seg_start= math.floor(pz / ROAD_SEGMENT) - 2
    white_w  = 3.0
    dash_len = 15.0
    gap_len  = 15.0
    period   = dash_len + gap_len

    for s in range(seg_start, seg_start + NUM_SEGMENTS):
        z0 = s * ROAD_SEGMENT
        z1 = z0 + ROAD_SEGMENT

        # Dark purple tarmac
        glColor3f(0.10, 0.06, 0.16)
        glBegin(GL_QUADS)
        glVertex3f(-ROAD_HALF, 0.01, z0)
        glVertex3f( ROAD_HALF, 0.01, z0)
        glVertex3f( ROAD_HALF, 0.01, z1)
        glVertex3f(-ROAD_HALF, 0.01, z1)
        glEnd()

        # Neon pink kerb left
        glColor3f(0.9, 0.1, 0.7)
        glBegin(GL_QUADS)
        glVertex3f(-ROAD_HALF,       0.02, z0)
        glVertex3f(-ROAD_HALF + 4.0, 0.02, z0)
        glVertex3f(-ROAD_HALF + 4.0, 0.02, z1)
        glVertex3f(-ROAD_HALF,       0.02, z1)
        glEnd()
        # Neon pink kerb right
        glBegin(GL_QUADS)
        glVertex3f( ROAD_HALF - 4.0, 0.02, z0)
        glVertex3f( ROAD_HALF,       0.02, z0)
        glVertex3f( ROAD_HALF,       0.02, z1)
        glVertex3f( ROAD_HALF - 4.0, 0.02, z1)
        glEnd()

    # Neon dashes
    first_dash = math.floor(pz / period) - 5
    for d in range(first_dash, first_dash + 80):
        dz0 = d * period
        dz1 = dz0 + dash_len
        for lane_x in [0.0, -LANE_OFFSET, LANE_OFFSET]:
            if lane_x == 0.0:
                glColor3f(0.0, 1.0, 0.9)    # cyan centre line
            else:
                glColor3f(0.65, 0.0, 1.0)   # purple lane dividers
            glBegin(GL_QUADS)
            glVertex3f(lane_x - white_w, 0.03, dz0)
            glVertex3f(lane_x + white_w, 0.03, dz0)
            glVertex3f(lane_x + white_w, 0.03, dz1)
            glVertex3f(lane_x - white_w, 0.03, dz1)
            glEnd()


def draw_arcade_environment():
    """
    Desert scenery: large setting sun, stone pillars, and occasional cacti
    alongside the road — completely different from the normal city environment.
    """
    pz = config.car_pos[2]
    ENV_SPAN    = NUM_SEGMENTS * ROAD_SEGMENT
    base_offset = math.floor(pz / ENV_SPAN) * ENV_SPAN

    # --- Large setting sun on the horizon ---
    glPushMatrix()
    glTranslatef(-250.0, 220.0, pz + 2500.0)
    glColor3f(1.0, 0.45, 0.05)
    gluSphere(gluNewQuadric(), 130.0, 16, 16)
    glPopMatrix()

    # --- Stone pillars & cacti (deterministic seeded layout) ---
    rng = random.Random(77)   # fixed seed = same pillars every run
    for i in range(40):
        side = rng.choice([-1, 1])
        bx   = side * (ROAD_HALF + rng.uniform(18, 110))
        bz   = rng.uniform(0, ENV_SPAN)
        kind = rng.choice(['pillar', 'cactus'])

        world_z = bz + base_offset
        # Wrap if behind or too far ahead
        if world_z < pz - 300 or world_z > pz + 700:
            world_z += ENV_SPAN if world_z < pz - 300 else -ENV_SPAN
        if abs(world_z - pz) > 750:
            continue

        if kind == 'pillar':
            h = rng.uniform(35, 75)
            # Pillar shaft
            glPushMatrix()
            glTranslatef(bx, 0.0, world_z)
            glColor3f(0.55, 0.44, 0.33)
            gluCylinder(gluNewQuadric(), 7.0, 5.5, h, 8, 4)
            glPopMatrix()
            # Pillar cap
            glPushMatrix()
            glTranslatef(bx, h, world_z)
            glColor3f(0.65, 0.52, 0.38)
            gluSphere(gluNewQuadric(), 9.0, 8, 6)
            glPopMatrix()

        else:  # cactus
            trunk_h = rng.uniform(20, 40)
            # Main trunk
            glPushMatrix()
            glTranslatef(bx, 0.0, world_z)
            glColor3f(0.18, 0.52, 0.18)
            gluCylinder(gluNewQuadric(), 4.0, 3.5, trunk_h, 8, 4)
            glPopMatrix()
            # Left arm
            glPushMatrix()
            glTranslatef(bx - 6.0, trunk_h * 0.55, world_z)
            glRotatef(-60, 1, 0, 0)
            glColor3f(0.18, 0.52, 0.18)
            gluCylinder(gluNewQuadric(), 2.5, 2.0, 12.0, 8, 2)
            glPopMatrix()
            # Right arm
            glPushMatrix()
            glTranslatef(bx + 6.0, trunk_h * 0.6, world_z)
            glRotatef(60, 1, 0, 0)
            glColor3f(0.18, 0.52, 0.18)
            gluCylinder(gluNewQuadric(), 2.5, 2.0, 12.0, 8, 2)
            glPopMatrix()


def draw_arcade_coins():
    """
    Gold spinning coins floating above the road.
    Each coin is a flattened sphere (squashed on X axis) that
    rotates on the Y axis using the shared arcade_coin_rotation angle.
    """
    for coin in config.arcade_coins:
        if coin[3]:       # already collected — skip
            continue
        cx, cy, cz = coin[0], coin[1], coin[2]

        glPushMatrix()
        glTranslatef(cx, cy, cz)
        glRotatef(config.arcade_coin_rotation, 0, 1, 0)

        # Gold disc body (flatten sphere on X so it looks like a coin face-on)
        glColor3f(1.0, 0.82, 0.0)
        glPushMatrix()
        glScalef(0.25, 1.0, 1.0)     # squash X → thin coin
        gluSphere(gluNewQuadric(), 6.0, 12, 8)
        glPopMatrix()

        # Slightly darker gold rim (cylinder on its side)
        glColor3f(0.85, 0.65, 0.0)
        glPushMatrix()
        glRotatef(90, 0, 1, 0)
        glTranslatef(0, 0, -1.2)
        gluCylinder(gluNewQuadric(), 6.0, 6.0, 2.4, 12, 2)
        glPopMatrix()

        glPopMatrix()


def draw_arcade_obstacles():
    """
    Orange/white traffic barriers on the road.
    Each barrier is a chunky cube body with a white stripe and a weighted base.
    """
    for obs in config.arcade_obstacles:
        if obs[3]:        # already hit — skip (gone from world)
            continue
        ox, oy, oz = obs[0], obs[1], obs[2]

        glPushMatrix()
        glTranslatef(ox, oy, oz)

        # Heavy base (dark orange)
        glColor3f(0.65, 0.18, 0.0)
        glPushMatrix()
        glTranslatef(0, 4, 0)
        glScalef(1.4, 0.4, 0.6)
        glutSolidCube(20)
        glPopMatrix()

        # Main body (bright orange)
        glColor3f(0.95, 0.35, 0.05)
        glPushMatrix()
        glTranslatef(0, 13, 0)
        glScalef(1.2, 0.55, 0.45)
        glutSolidCube(20)
        glPopMatrix()

        # White diagonal stripe across the body
        glColor3f(1.0, 1.0, 1.0)
        glPushMatrix()
        glTranslatef(0, 13, 0)
        glRotatef(30, 0, 0, 1)
        glScalef(0.25, 0.58, 0.46)
        glutSolidCube(20)
        glPopMatrix()

        # Reflective top knob (small yellow sphere)
        glColor3f(1.0, 0.9, 0.0)
        glPushMatrix()
        glTranslatef(0, 24, 0)
        gluSphere(gluNewQuadric(), 3.5, 8, 6)
        glPopMatrix()

        glPopMatrix()


def draw_arcade_hud():
    """2D HUD overlay for Arcade mode: coins, lives, speed, distance."""

    # ---------- text labels ----------
    draw_text(20, 760, "ARCADE MODE", GLUT_BITMAP_TIMES_ROMAN_24)
    draw_text(20, 720, f"Coins : {config.arcade_score}")
    draw_text(20, 690, f"Dist  : {config.arcade_distance} m")
    speed_disp = int(config.arcade_speed * 9)
    draw_text(20, 660, f"Speed : {speed_disp} km/h")
    draw_text(20, 630, "Lives :")

    # ---------- life hearts (drawn in 2D ortho) ----------
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    for i in range(3):
        x0 = 100 + i * 65
        if i < config.arcade_lives:
            glColor3f(0.95, 0.15, 0.15)   # red = alive
        else:
            glColor3f(0.30, 0.10, 0.10)   # dark = lost
        glBegin(GL_QUADS)
        glVertex2f(x0,      620)
        glVertex2f(x0 + 50, 620)
        glVertex2f(x0 + 50, 645)
        glVertex2f(x0,      645)
        glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    # ---------- NEW: ARCADE COUNTDOWN DISPLAY ----------
    elapsed_total = time.time() - config.race_start_time
    if elapsed_total < 3.0:
        countdown_num = 3 - int(elapsed_total)
        draw_text(480, 450, str(countdown_num), GLUT_BITMAP_TIMES_ROMAN_24)
    elif elapsed_total < 4.0:
        draw_text(470, 450, "GO!", GLUT_BITMAP_TIMES_ROMAN_24)


    # ---------- game-over screen ----------
    if config.arcade_game_over:
        draw_text(330, 490, "GAME OVER!", GLUT_BITMAP_TIMES_ROMAN_24)
        draw_text(310, 448, f"Coins Collected : {config.arcade_score}")
        draw_text(310, 410, f"Distance        : {config.arcade_distance} m")
        draw_text(310, 372, "Press 'M' for Main Menu")
# ==========================================

ROAD_WIDTH    = 120.0      # total tarmac width
LANE_OFFSET   = 35.0       # distance from centre to lane centre
ROAD_HALF     = ROAD_WIDTH / 2.0
ROAD_SEGMENT  = 200.0      # length of each visible road chunk
NUM_SEGMENTS  = 12         # how many chunks rendered ahead+behind

# Pre-built environment objects (generated once, then scrolled)
env_buildings = []   # list of (x, z, w, h, d, r, g, b)
env_trees     = []   # list of (x, z, r, g, b)
# Fix the generator (was using g_val before assigned)
def generate_env_objects():
    global env_buildings, env_trees
    env_buildings = []
    env_trees     = []

    ENV_SPAN = NUM_SEGMENTS * ROAD_SEGMENT

    rng = random.Random(42)
    for _ in range(80):
        side = rng.choice([-1, 1])
        x    = side * (ROAD_HALF + rng.uniform(20, 130))
        z    = rng.uniform(0, ENV_SPAN)
        w    = rng.uniform(18, 45)
        h    = rng.uniform(30, 100)
        d    = rng.uniform(18, 45)
        r    = rng.uniform(0.3, 1.0)
        g    = rng.uniform(0.3, 1.0)
        b_   = rng.uniform(0.3, 1.0)
        env_buildings.append((x, z, w, h, d, r, g, b_))

    for _ in range(120):
        side = rng.choice([-1, 1])
        x    = side * (ROAD_HALF + rng.uniform(8, 180))
        z    = rng.uniform(0, ENV_SPAN)
        r    = rng.uniform(0.0, 0.35)
        g    = rng.uniform(0.5, 0.9)
        b_   = rng.uniform(0.0, 0.25)
        env_trees.append((x, z, r, g, b_))


def draw_ground_plane():
    GROUND_HALF = 800.0
    ROAD_Z_NEAR = config.car_pos[2] - 400.0
    ROAD_Z_FAR  = config.car_pos[2] + 800.0
    is_night = getattr(config, 'setting_time_of_day', 'Day') == "Night"

    grass_color = (0.05, 0.2, 0.08) if is_night else (0.18, 0.55, 0.18)

    glColor3f(*grass_color)
    glBegin(GL_QUADS)
    glVertex3f(-GROUND_HALF, 0.0, ROAD_Z_NEAR)
    glVertex3f(-ROAD_HALF,   0.0, ROAD_Z_NEAR)
    glVertex3f(-ROAD_HALF,   0.0, ROAD_Z_FAR)
    glVertex3f(-GROUND_HALF, 0.0, ROAD_Z_FAR)
    glEnd()

    glColor3f(*grass_color)
    glBegin(GL_QUADS)
    glVertex3f(ROAD_HALF,   0.0, ROAD_Z_NEAR)
    glVertex3f(GROUND_HALF, 0.0, ROAD_Z_NEAR)
    glVertex3f(GROUND_HALF, 0.0, ROAD_Z_FAR)
    glVertex3f(ROAD_HALF,   0.0, ROAD_Z_FAR)
    glEnd()


def draw_road():
    pz        = config.car_pos[2]
    seg_start = math.floor(pz / ROAD_SEGMENT) -2
    white_w   = 3.0
    dash_len  = 20.0
    gap_len   = 20.0
    period    = dash_len + gap_len
    is_night  = getattr(config, 'setting_time_of_day', 'Day') == "Night"

    tarmac_color = (0.1, 0.1, 0.12) if is_night else (0.22, 0.22, 0.22)
    kerb_color   = (0.4, 0.4, 0.45) if is_night else (0.95, 0.95, 0.95)
    center_color = (0.6, 0.6, 0.0) if is_night else (1.0, 1.0, 0.0)
    dash_color   = (0.4, 0.4, 0.45) if is_night else (0.9, 0.9, 0.9)

    for s in range(seg_start, seg_start + NUM_SEGMENTS):
        z0 = s * ROAD_SEGMENT
        z1 = z0 + ROAD_SEGMENT

        glColor3f(*tarmac_color)
        glBegin(GL_QUADS)
        glVertex3f(-ROAD_HALF, 0.01, z0)
        glVertex3f( ROAD_HALF, 0.01, z0)
        glVertex3f( ROAD_HALF, 0.01, z1)
        glVertex3f(-ROAD_HALF, 0.01, z1)
        glEnd()

        glColor3f(*kerb_color)
        glBegin(GL_QUADS)
        glVertex3f(-ROAD_HALF,       0.02, z0)
        glVertex3f(-ROAD_HALF + 4.0, 0.02, z0)
        glVertex3f(-ROAD_HALF + 4.0, 0.02, z1)
        glVertex3f(-ROAD_HALF,       0.02, z1)
        glEnd()
        glBegin(GL_QUADS)
        glVertex3f(ROAD_HALF - 4.0, 0.02, z0)
        glVertex3f(ROAD_HALF,       0.02, z0)
        glVertex3f(ROAD_HALF,       0.02, z1)
        glVertex3f(ROAD_HALF - 4.0, 0.02, z1)
        glEnd()

    first_dash = math.floor(pz / period) -5
    for d in range(first_dash, first_dash + 60):
        dz0 = d * period
        dz1 = dz0 + dash_len
        for lane_x in [0.0, -LANE_OFFSET, LANE_OFFSET]:
            glColor3f(*center_color) if lane_x == 0.0 else glColor3f(*dash_color)
            glBegin(GL_QUADS)
            glVertex3f(lane_x - white_w, 0.03, dz0)
            glVertex3f(lane_x + white_w, 0.03, dz0)
            glVertex3f(lane_x + white_w, 0.03, dz1)
            glVertex3f(lane_x - white_w, 0.03, dz1)
            glEnd()


def draw_environment():
    ENV_SPAN = NUM_SEGMENTS * ROAD_SEGMENT
    pz       = config.car_pos[2]
    base_offset = math.floor(pz / ENV_SPAN) * ENV_SPAN
    is_night = getattr(config, 'setting_time_of_day', 'Day') == "Night"

    # --- NEW: 3D Sun and Moon ---
    # Lowered the Y value to 300 so it actually fits inside the camera's downward tilt!
    glPushMatrix()
    celestial_z = pz + 3200.0  
    glTranslatef(300.0, 300.0, celestial_z) 
    if is_night:
        glColor3f(0.9, 0.9, 0.8) # Moon
        gluSphere(gluNewQuadric(), 150.0, 20, 20)
    else:
        glColor3f(1.0, 0.9, 0.2) # Sun
        gluSphere(gluNewQuadric(), 150.0, 20, 20)
    glPopMatrix()
    # ----------------------------

    for (bx, bz, bw, bh, bd, r, g, b) in env_buildings:
        world_z = bz + base_offset
        if world_z < pz - 300 or world_z > pz + 700:
            world_z += ENV_SPAN if world_z < pz - 300 else -ENV_SPAN
        if abs(world_z - pz) > 750:
            continue

        glPushMatrix()
        glTranslatef(bx, 0.0, world_z)
        
        # Apply night darkening to building base color
        if is_night:
            glColor3f(r * 0.2, g * 0.2, b * 0.3)
        else:
            glColor3f(r, g, b)
            
        glTranslatef(0.0, bh / 2.0, 0.0)
        glScalef(bw, bh, bd)
        glutSolidCube(1.0)
        glPopMatrix()

        # Windows (Moved to the -Z face so the oncoming player sees them!)
        glPushMatrix()
        glTranslatef(bx, bh * 0.5, world_z - bd * 0.52) 
        
        if is_night:
            glColor3f(1.0, 0.9, 0.2) # Bright glowing yellow windows
        else:
            glColor3f(0.3, 0.5, 0.6) # Darker daytime glass

        rows = max(1, int(bh / 20))
        cols = max(1, int(bw / 12))
        for row in range(rows):
            for col in range(cols):
                wy = -bh * 0.4 + row * (bh * 0.8 / max(rows, 1))
                wx =  -bw * 0.35 + col * (bw * 0.7 / max(cols, 1))
                glPushMatrix()
                glTranslatef(wx, wy, 0)
                glScalef(4.0, 4.0, 0.5)
                glutSolidCube(1.0)
                glPopMatrix()
        glPopMatrix()

    for (tx, tz, r, g, b) in env_trees:
        world_z = tz + base_offset
        if world_z < pz - 300 or world_z > pz + 700:
            world_z += ENV_SPAN if world_z < pz - 300 else -ENV_SPAN
        if abs(world_z - pz) > 750:
            continue

        # Trunk
        glPushMatrix()
        glTranslatef(tx, 0.0, world_z)
        if is_night:
            glColor3f(0.15, 0.08, 0.02)
        else:
            glColor3f(0.45, 0.27, 0.07)
        gluCylinder(gluNewQuadric(), 2.5, 1.5, 14.0, 8, 4)
        glPopMatrix()

        # Foliage
        glPushMatrix()
        glTranslatef(tx, 18.0, world_z)
        if is_night:
            glColor3f(r * 0.3, g * 0.3, b * 0.4)
        else:
            glColor3f(r, g, b)
        gluSphere(gluNewQuadric(), 12.0, 8, 8)
        glPopMatrix()


def draw_sky():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(-1, 1, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    is_night = getattr(config, 'setting_time_of_day', 'Day') == "Night"

    if is_night:
        # Night sky gradient
        glBegin(GL_QUADS)
        glColor3f(0.02, 0.02, 0.08)   
        glVertex2f(-1,  1)
        glVertex2f( 1,  1)
        glColor3f(0.1, 0.1, 0.2)   
        glVertex2f( 1, -1)
        glVertex2f(-1, -1)
        glEnd()
    else:
        # Day sky gradient
        glBegin(GL_QUADS)
        glColor3f(0.1, 0.4, 0.8)   
        glVertex2f(-1,  1)
        glVertex2f( 1,  1)
        glColor3f(0.6, 0.8, 1.0)   
        glVertex2f( 1, -1)
        glVertex2f(-1, -1)
        glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def update_ai():
    for ai in config.ai_cars:
        ai["lane_change_timer"] -= 0.016
        if ai["lane_change_timer"] <= 0:
            ai["lane"] = random.choice([-LANE_OFFSET, 0.0, LANE_OFFSET])
            ai["lane_change_timer"] = random.uniform(3.0, 7.0)

        # Smoothly approach target lane X
        target_x = ai["lane"]
        dx = target_x - ai["pos"][0]
        ai["pos"][0] += dx * 0.04

        # Accelerate toward max speed using their specific, slower acceleration
        ai["velocity_z"] = min(ai["velocity_z"] + ai["accel"], ai["max_speed"])
        ai["pos"][2] += ai["velocity_z"]
        ai["facing_angle"] = 0.0   # AI always faces forward (+Z)

# ==========================================
# 4. CAMERA
# ==========================================
def apply_camera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(80, 1.25, 0.5, 4000)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    rad_facing = math.radians(config.car_facing_angle)
    facing_dx  = math.sin(rad_facing)
    facing_dz  = math.cos(rad_facing)

    if config.current_camera == config.CAM_CHASE:
        cam_dist   = 80.0
        swing_rad  = math.radians(config.cam_swing_angle)
        cam_x = config.car_pos[0] - math.sin(rad_facing + swing_rad) * cam_dist
        cam_z = config.car_pos[2] - math.cos(rad_facing + swing_rad) * cam_dist
        cam_y = config.car_pos[1] + config.cam_height_offset
        gluLookAt(cam_x, cam_y, cam_z,
                  config.car_pos[0], config.car_pos[1] + 5, config.car_pos[2],
                  0, 1, 0)
    else:  # Hood cam
        cam_x = config.car_pos[0] + facing_dx * 10.0
        cam_y = config.car_pos[1] + 15.0
        cam_z = config.car_pos[2] + facing_dz * 10.0
        gluLookAt(cam_x, cam_y, cam_z,
                  cam_x + facing_dx * 200.0, cam_y, cam_z + facing_dz * 200.0, 0, 1, 0)


# ==========================================
# 5. CAR MODEL
# ==========================================
def draw_car(is_player=True, x=0, y=0, z=0, angle=0):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 1, 0)

    if is_player:
        roll  = config.current_wheel_angle * 0.3
        speed = math.sqrt(config.car_velocity[0]**2 + config.car_velocity[2]**2)
        pitch = -speed * 0.5 if config.keys_pressed[b'w'] else (speed * 0.3 if config.keys_pressed[b's'] else 0)
        glRotatef(pitch, 1, 0, 0)
        glRotatef(roll,  0, 0, 1)

    # --- Body (Chassis) ---
    glColor3f(0.85, 0.1, 0.1) if is_player else glColor3f(0.1, 0.2, 0.85)
    glPushMatrix()
    glTranslatef(0, 7, 0)
    glScalef(1.1, 0.35, 2.2) 
    glutSolidCube(20)
    glPopMatrix()

    # --- Cabin (Roof) ---
    glColor3f(0.6, 0.05, 0.05) if is_player else glColor3f(0.05, 0.1, 0.6)
    glPushMatrix()
    glTranslatef(0, 14, -2)
    glScalef(0.8, 0.35, 1.0)
    glutSolidCube(20)
    glPopMatrix()
    
    # --- Glass (Windshields & Windows) ---
    glColor3f(0.5, 0.8, 0.9) 
    
    # Windshield (Front)
    glPushMatrix()
    glTranslatef(0, 14, 8) 
    glRotatef(20, 1, 0, 0) 
    glScalef(0.78, 0.32, 0.05)
    glutSolidCube(20)
    glPopMatrix()
    
    # Rear Window
    glPushMatrix()
    glTranslatef(0, 14, -12) 
    glRotatef(-15, 1, 0, 0)
    glScalef(0.78, 0.32, 0.05)
    glutSolidCube(20)
    glPopMatrix()
    
    # Side Windows 
    glPushMatrix()
    glTranslatef(-8.1, 14, -2) 
    glScalef(0.05, 0.32, 0.95)
    glutSolidCube(20)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(8.1, 14, -2)
    glScalef(0.05, 0.32, 0.95)
    glutSolidCube(20)
    glPopMatrix()

    # --- Wheels (Lowered and tucked to fix the top-view glitch!) ---
    wheel_positions = [(-11.0, 3.5, 12), (11.0, 3.5, 12), (-11.0, 3.5, -12), (11.0, 3.5, -12)]
    for i, (wx, wy, wz) in enumerate(wheel_positions):
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        if is_player and i < 2:          
            glRotatef(config.current_wheel_angle, 0, 1, 0)
        
        # 1. Tire Tread (Cylinder)
        glColor3f(0.1, 0.1, 0.1) 
        glPushMatrix()
        glRotatef(90, 0, 1, 0)
        glTranslatef(0, 0, -2.5) 
        gluCylinder(gluNewQuadric(), 3.5, 3.5, 5.0, 12, 4)
        glPopMatrix()

        # 2. Tire Wall (Flattened Sphere)
        glColor3f(0.15, 0.15, 0.15)
        glPushMatrix()
        glScalef(0.4, 1.0, 1.0) 
        gluSphere(gluNewQuadric(), 3.4, 12, 12)
        glPopMatrix()

        # 3. Hubcap 
        glColor3f(0.7, 0.7, 0.7)
        glPushMatrix()
        side_dir = -1 if wx < 0 else 1
        glTranslatef(side_dir * 2.6, 0, 0)
        glScalef(0.3, 1.0, 1.0)
        gluSphere(gluNewQuadric(), 1.8, 10, 8)
        glPopMatrix()

        glPopMatrix()

    glPopMatrix()


# ==========================================
# 6. PHYSICS
# ==========================================
def update_physics():
    if config.race_finished:
        return

    config.TURN_SPEED = config.setting_sensitivity

    # --- Steering ---
    target_wheel = 0.0
    if config.keys_pressed[b'a']:
        target_wheel =  config.MAX_WHEEL_ANGLE
    elif config.keys_pressed[b'd']:
        target_wheel = -config.MAX_WHEEL_ANGLE

    step = config.TURN_SPEED
    if config.current_wheel_angle < target_wheel:
        config.current_wheel_angle = min(config.current_wheel_angle + step, target_wheel)
    elif config.current_wheel_angle > target_wheel:
        config.current_wheel_angle = max(config.current_wheel_angle - step, target_wheel)

    # --- Thrust / Brake ---
    rad_facing  = math.radians(config.car_facing_angle)
    facing_dx   = math.sin(rad_facing)
    facing_dz   = math.cos(rad_facing)
    fwd_vel     = (config.car_velocity[0] * facing_dx +
                   config.car_velocity[2] * facing_dz)
    # NEW: Nitrous Logic
    current_thrust = config.THRUST
    current_max_speed = config.MAX_SPEED

    if config.keys_pressed[b' '] and config.boost_amount > 0:
        current_thrust *= 2.5         # Massive acceleration boost
        current_max_speed *= 1.4      # 40% higher top speed
        config.boost_amount -= 1.0    # Drain the nitrous tank
    elif config.boost_amount < config.boost_max:
        config.boost_amount += 0.2    # Slowly regenerate when not in use

    # Apply the current_thrust (boosted or normal)
    if config.keys_pressed[b'w']:
        if fwd_vel < -0.1:
            config.car_velocity[0] += facing_dx * config.BRAKE_FORCE * 2.0
            config.car_velocity[2] += facing_dz * config.BRAKE_FORCE * 2.0
        else:
            config.car_velocity[0] += facing_dx * current_thrust
            config.car_velocity[2] += facing_dz * current_thrust

    if config.keys_pressed[b's']:
        if fwd_vel > 0.1:
            config.car_velocity[0] -= facing_dx * config.BRAKE_FORCE * 2.0
            config.car_velocity[2] -= facing_dz * config.BRAKE_FORCE * 2.0
        else:
            config.car_velocity[0] -= facing_dx * config.THRUST * 0.5
            config.car_velocity[2] -= facing_dz * config.THRUST * 0.5

    # --- FRICTION ---
    config.car_velocity[0] *= config.FRICTION
    config.car_velocity[2] *= config.FRICTION

    # --- Clamp to max speed ---
    speed = math.sqrt(config.car_velocity[0]**2 + config.car_velocity[2]**2)
    if speed > current_max_speed:      # Using the dynamically boosted max speed here!
        ratio = current_max_speed / speed
        config.car_velocity[0] *= ratio
        config.car_velocity[2] *= ratio

    # --- Turning (speed-dependent) ---
    if speed > 0.2:
        # NEW: Check if reversing to invert the steering angle naturally
        direction_multiplier = 1.0 if fwd_vel >= 0 else -1.0
        turn_factor = (speed / config.MAX_SPEED) * 0.18 * direction_multiplier
        
        config.car_facing_angle += config.current_wheel_angle * turn_factor
        
        # Slight speed reduction when turning (scrubbing speed realistically)
        if abs(config.current_wheel_angle) > 5.0:
            config.car_velocity[0] *= 0.99
            config.car_velocity[2] *= 0.99

    # --- Road boundary clamp (keep on road) ---
    ROAD_HALF = 60.0
    config.car_pos[0] = max(-ROAD_HALF + 12, min(ROAD_HALF - 12, config.car_pos[0]))

    # --- Move car ---
    config.car_pos[0] += config.car_velocity[0]
    config.car_pos[2] += config.car_velocity[2]

    # --- Score (distance driven) ---
    config.score = max(config.score, int(config.car_pos[2] / 10))

def check_collisions_and_laps():
    if config.race_finished:
        return

    if config.setting_collisions:
        hit_radius = 18.0
        for ai in config.ai_cars:
            dx = config.car_pos[0] - ai["pos"][0]
            dz = config.car_pos[2] - ai["pos"][2]
            dist = math.sqrt(dx**2 + dz**2)
            if dist < hit_radius and dist > 0.01:
                # Slight realistic speed decrease instead of massive stop
                config.car_velocity[0] *= 0.85 
                config.car_velocity[2] *= 0.85
                config.car_pos[0] += (dx / dist) * 3.0
                config.car_pos[2] += (dz / dist) * 3.0

    # Lap / distance checkpoint for Race mode
    if config.current_state == config.STATE_RACE:
        lap_distance = 3000.0
        
        # Calculate current lap (Start at lap 1)
        config.current_lap = int(config.car_pos[2] / lap_distance) + 1
        
        # Check if we passed the final finish line
        if config.current_lap > config.setting_laps and not config.race_finished:
            config.race_finished = True
            config.current_lap = config.setting_laps # Lock HUD display to max laps
            
            # --- NEW: Lock the final position ---
            # This ensures if the AI drives past your parked car after the race, 
            # your placement text doesn't change!
            all_z_positions = [config.car_pos[2]] + [ai["pos"][2] for ai in config.ai_cars]
            all_z_positions.sort(reverse=True)
            config.final_position = all_z_positions.index(config.car_pos[2]) + 1


# ==========================================
# 7. TEXT & UI
# ==========================================
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_time_select_menu():
    # Background
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glBegin(GL_QUADS)
    glColor3f(0.05, 0.05, 0.15)
    glVertex2f(0, 800)
    glVertex2f(1000, 800)
    glColor3f(0.10, 0.10, 0.35)
    glVertex2f(1000, 0)
    glVertex2f(0, 0)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    draw_text(370, 550, "SELECT TIME OF DAY", GLUT_BITMAP_TIMES_ROMAN_24)
    draw_text(360, 500, "W/S = navigate   ENTER = select")

    opts  = ["Day Mode", "Night Mode"]
    start_y  = 400
    for i, option in enumerate(opts):
        ypos = start_y - i * 50
        if i == getattr(config, 'current_time_selection', 0):
            draw_text(410, ypos, f">  {option}  <")
        else:
            draw_text(440, ypos, option)


def draw_main_menu():
    # Background
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Sky gradient
    glBegin(GL_QUADS)
    glColor3f(0.05, 0.05, 0.15)
    glVertex2f(0, 800)
    glVertex2f(1000, 800)
    glColor3f(0.10, 0.10, 0.35)
    glVertex2f(1000, 0)
    glVertex2f(0, 0)
    glEnd()

    # Road strip at bottom
    glColor3f(0.2, 0.2, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(0, 0); glVertex2f(1000, 0)
    glVertex2f(1000, 120); glVertex2f(0, 120)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

    draw_text(360, 680, "VECTOR VELOCITY", GLUT_BITMAP_TIMES_ROMAN_24)
    draw_text(310, 640, "Endless Highway Racing  |  CSE 423 Group 01")
    draw_text(290, 600, "W/S = navigate menu   A/D = change value   ENTER = select")

    options  = get_menu_options()
    start_y  = 530
    for i, option in enumerate(options):
        ypos = start_y - i * 42
        if i == config.current_menu_selection:
            draw_text(370, ypos, f">  {option}  <")
            if i >= 2:
                draw_text(660, ypos, "[A / D]")
        else:
            draw_text(400, ypos, option)

    draw_text(300, 150, "In-game controls:")
    draw_text(300, 120, "W/S = Gas/Brake   A/D = Steer   P = Pause   RMB = Toggle Camera")
    draw_text(300, 90,  "Arrow Keys = Camera angle/height   M = Main Menu (when paused/finished)")


def draw_pause_menu():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    
    glColor3f(0.05, 0.05, 0.15)
    glBegin(GL_QUADS)
    glVertex2f(350, 300)
    glVertex2f(650, 300)
    glVertex2f(650, 500)
    glVertex2f(350, 500)
    glEnd()
    
    draw_text(445, 460, "PAUSED", GLUT_BITMAP_TIMES_ROMAN_24)
    draw_text(390, 410, "Press  'P'  to Resume")
    draw_text(390, 370, "Press  'M'  for Main Menu")

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_hud():
    speed_val = math.sqrt(config.car_velocity[0]**2 + config.car_velocity[2]**2)
    speed_kmh = int(speed_val * 18)   # rough km/h scale
    draw_text(20, 40, f"Speed: {speed_kmh} km/h")
    draw_text(20, 70, f"Score: {config.score} m")
    speed_val = math.sqrt(config.car_velocity[0]**2 + config.car_velocity[2]**2)
    speed_kmh = int(speed_val * 18)   
    draw_text(20, 40, f"Speed: {speed_kmh} km/h")
    draw_text(20, 70, f"Score: {config.score} m")

    # --- NEW: Nitrous UI ---
    draw_text(20, 100, f"N2O: {int(config.boost_amount)}%")
    
    # Background Bar (Dark Gray)
    glColor3f(0.2, 0.2, 0.2) 
    glBegin(GL_QUADS)
    glVertex2f(20, 115)
    glVertex2f(220, 115)
    glVertex2f(220, 125)
    glVertex2f(20, 125)
    glEnd()
    
    # Foreground Bar (Cyan normally, turns Red when running low)
    if config.boost_amount > 25:
        glColor3f(0.0, 0.8, 1.0) # Cyan
    else:
        glColor3f(1.0, 0.1, 0.1) # Flashing Red warning
        
    bar_width = config.boost_amount * 2 # Scales 0-100 to 0-200 pixels
    glBegin(GL_QUADS)
    glVertex2f(20, 115)
    glVertex2f(20 + bar_width, 115)
    glVertex2f(20 + bar_width, 125)
    glVertex2f(20, 125)
    glEnd()

    cam_label = "Chase Cam" if config.current_camera == config.CAM_CHASE else "Hood Cam"
    draw_text(840, 40, cam_label)

    if config.current_state == config.STATE_RACE:
        
        # --- POSITION CALCULATION ---
        # Sort all cars by their Z coordinate (highest Z is 1st place)
        all_z_positions = [config.car_pos[2]] + [ai["pos"][2] for ai in config.ai_cars]
        all_z_positions.sort(reverse=True)
        player_pos = all_z_positions.index(config.car_pos[2]) + 1
        
        # --- COUNTDOWN DISPLAY ---
        elapsed_total = time.time() - config.race_start_time
        if elapsed_total < 3.0:
            countdown_num = 3 - int(elapsed_total)
            draw_text(480, 450, str(countdown_num), GLUT_BITMAP_TIMES_ROMAN_24)
        elif elapsed_total < 4.0:
            draw_text(470, 450, "GO!", GLUT_BITMAP_TIMES_ROMAN_24)

        elapsed = f"{config.current_race_time:.1f}s" if config.current_race_time > 0 else "0.0s"
        
        # --- LAP & POS DISPLAY ---
        draw_text(840, 780, f"Pos: {player_pos} / 3")
        draw_text(840, 750, f"Lap: {config.current_lap} / {config.setting_laps}")
        draw_text(840, 720, f"Time: {elapsed}")

        if config.race_finished:
            # Use the locked final position so it doesn't change after you stop
            final_pos = getattr(config, 'final_position', player_pos)
            
            # --- NEW: Custom End Messages ---
            if final_pos == 1:
                draw_text(300, 500, "Congratulations, You're the winner", GLUT_BITMAP_TIMES_ROMAN_24)
            elif final_pos == 2:
                draw_text(360, 500, "Great, You're Runnerup", GLUT_BITMAP_TIMES_ROMAN_24)
            else:
                draw_text(360, 500, "You looser, Try again.", GLUT_BITMAP_TIMES_ROMAN_24)
                
            draw_text(390, 455, f"Final Time: {config.current_race_time:.1f}s")
            draw_text(360, 415, "Press 'M' for Main Menu")

    elif config.current_state == config.STATE_FREE_ROAM:
        draw_text(830, 750, "FREE ROAM")

# ==========================================
# 8. MAIN GAME LOOP
# ==========================================
def reset_race():
    config.car_pos           = [0.0, 0.0, 0.0]
    config.car_velocity      = [0.0, 0.0, 0.0]
    config.car_facing_angle  = 0.0
    config.current_wheel_angle = 0.0
    config.current_lap       = 1
    config.player_waypoint   = 0
    config.race_finished     = False
    config.score             = 0
    config.race_start_time   = time.time()
    config.cam_swing_angle   = 0.0
    config.cam_height_offset = 50.0
    config.current_camera    = config.CAM_CHASE
    config.last_time = time.time()
    config.accumulator = 0.0
    config.boost_amount = config.boost_max

def keyboardListener(key, x, y):
    # Safely initialize new Day/Night state variables if they don't exist
    if not hasattr(config, 'STATE_TIME_SELECT'):
        config.STATE_TIME_SELECT = 4
        config.current_time_selection = 0
        config.pending_game_state = config.STATE_RACE
        config.setting_time_of_day = "Day"

    key_lower = key.lower()

    if config.current_state == config.STATE_MENU:
        opts = get_menu_options()
        if key_lower == b'w':
            config.current_menu_selection = max(0, config.current_menu_selection - 1)
        elif key_lower == b's':
            config.current_menu_selection = min(len(opts) - 1, config.current_menu_selection + 1)
        elif key_lower in (b'a', b'd'):
            direction = -1 if key_lower == b'a' else 1
            sel = config.current_menu_selection
            
            if sel == 3:   # Laps (was 2, shifted by Arcade insertion)
                config.setting_laps = max(1, min(10, config.setting_laps + direction))
            elif sel == 4:  # Difficulty (was 3)
                diffs = ["Easy", "Normal", "Hard"]
                idx = diffs.index(config.setting_difficulty)
                config.setting_difficulty = diffs[(idx + direction) % 3]
            elif sel == 5:  # Collisions (was 4)
                config.setting_collisions = not config.setting_collisions
            elif sel == 6:  # Sensitivity (was 5)
                config.setting_sensitivity = max(1.0, min(4.0, config.setting_sensitivity + direction * 0.5))
        
        elif key == b'\r':
            # Instead of starting the game directly, go to Time Selection
            if config.current_menu_selection == 0:
                config.pending_game_state = config.STATE_RACE
                config.current_state = config.STATE_TIME_SELECT
                config.current_time_selection = 0
            elif config.current_menu_selection == 1:
                config.pending_game_state = config.STATE_FREE_ROAM
                config.current_state = config.STATE_TIME_SELECT
                config.current_time_selection = 0
            elif config.current_menu_selection == 2:
                # Arcade mode — no time-of-day selection, launch directly
                reset_arcade()
                config.current_state = config.STATE_ARCADE

    elif config.current_state == config.STATE_TIME_SELECT:
        if key_lower == b'w':
            config.current_time_selection = 0
        elif key_lower == b's':
            config.current_time_selection = 1
        elif key == b'\r':
            # Set the time of day and finalize the game launch
            config.setting_time_of_day = "Day" if config.current_time_selection == 0 else "Night"
            reset_race()
            config.current_state = config.pending_game_state
            if config.current_state == config.STATE_RACE:
                init_ai(config.setting_opponents, config.setting_difficulty)
            else:
                config.ai_cars = []

    elif config.current_state in [config.STATE_RACE, config.STATE_FREE_ROAM]:
        if key_lower in config.keys_pressed:
            config.keys_pressed[key_lower] = True
        if key_lower == b'p':
            config.resume_state = config.current_state
            config.current_state = config.STATE_PAUSED
        if config.race_finished and key_lower == b'm':
            config.current_state = config.STATE_MENU

    elif config.current_state == config.STATE_ARCADE:
        if key_lower in config.keys_pressed:
            config.keys_pressed[key_lower] = True
        if key_lower == b'p':
            config.resume_state = config.STATE_ARCADE
            config.current_state = config.STATE_PAUSED
        if config.arcade_game_over and key_lower == b'm':
            config.current_state = config.STATE_MENU

    elif config.current_state == config.STATE_PAUSED:
        if key_lower == b'p':
            # Return to whichever state we paused from
            config.current_state = getattr(config, 'resume_state', config.STATE_RACE)
        elif key_lower == b'm':
            config.current_state = config.STATE_MENU

    glutPostRedisplay()


def keyboardUpListener(key, x, y):
    key_lower = key.lower()
    if key_lower in config.keys_pressed:
        config.keys_pressed[key_lower] = False


def specialKeyListener(key, x, y):
    if config.current_state in [config.STATE_RACE, config.STATE_FREE_ROAM, config.STATE_ARCADE]:
        if key == GLUT_KEY_UP:
            config.cam_height_offset += 3.0
        elif key == GLUT_KEY_DOWN:
            config.cam_height_offset = max(10.0, config.cam_height_offset - 3.0)
        elif key == GLUT_KEY_LEFT:
            config.cam_swing_angle += 3.0
        elif key == GLUT_KEY_RIGHT:
            config.cam_swing_angle -= 3.0
    glutPostRedisplay()


def mouseListener(button, state, x, y):
    if config.current_state in [config.STATE_RACE, config.STATE_FREE_ROAM, config.STATE_ARCADE]:
        if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
            config.current_camera = (config.CAM_HOOD
                                     if config.current_camera == config.CAM_CHASE
                                     else config.CAM_CHASE)
    glutPostRedisplay()


def idle():
    # 1. Calculate time passed since last frame (Delta Time)
    current_time = time.time()
    
    # Fallback initialization just in case
    if not hasattr(config, 'last_time'):
        config.last_time = current_time
    if not hasattr(config, 'accumulator'):
        config.accumulator = 0.0
        
    dt = current_time - config.last_time
    config.last_time = current_time

    # Prevent "spiral of death" (if you drag the window or lag, don't run 1000 physics steps)
    if dt > 0.1:
        dt = 0.1

    # 2. Add time to accumulator
    config.accumulator += dt

    # 3. Only run logic if in game
    if config.current_state in [config.STATE_RACE, config.STATE_FREE_ROAM]:
        elapsed_total = time.time() - config.race_start_time
        
        # --- COUNTDOWN LOGIC ---
        if config.current_state == config.STATE_RACE and elapsed_total < 3.0:
            config.current_race_time = 0.0 # Race timer doesn't start yet
            config.accumulator = 0.0       # Consume time so physics doesn't fast-forward after countdown
            glutPostRedisplay()
            return # Freeze the game logic during countdown
            
        if not config.race_finished:
            if config.current_state == config.STATE_RACE:
                config.current_race_time = elapsed_total - 3.0 # Shift timer so it starts at 0
            else:
                config.current_race_time = elapsed_total
                
        # --- FIXED TIME STEP LOOP ---
        # Run physics exactly 60 times a second, no matter the refresh rate
        PHYSICS_TIME_STEP = 1.0 / 60.0
        while config.accumulator >= PHYSICS_TIME_STEP:
            update_physics()
            check_collisions_and_laps()
            update_ai()
            # Deduct the 1/60th of a second and loop if there's more time to catch up on
            config.accumulator -= PHYSICS_TIME_STEP 

    # Tell OpenGL to draw the frame
    glutPostRedisplay()

# --- ARCADE MODE UPDATE ---
    if config.current_state == config.STATE_ARCADE:
        if not config.arcade_game_over:
            elapsed_total = time.time() - config.race_start_time
            
            # --- NEW: ARCADE COUNTDOWN LOGIC ---
            if elapsed_total < 3.0:
                config.accumulator = 0.0       # Consume time so physics doesn't fast-forward
                glutPostRedisplay()
                return                         # Freeze the game logic during countdown
            
            # Advance coin spin animation
            config.arcade_coin_rotation = (config.arcade_coin_rotation + 3.0) % 360.0
            update_arcade_objects()
            PHYSICS_TIME_STEP = 1.0 / 60.0
            while config.accumulator >= PHYSICS_TIME_STEP:
                update_arcade_physics()
                check_arcade_collisions()
                config.accumulator -= PHYSICS_TIME_STEP
        glutPostRedisplay()
def draw_lap_lines():
    lap_distance = 3000.0
    ROAD_HALF = 60.0 
    
    # Draw the start line and all lap finish lines
    for lap in range(config.setting_laps + 1):
        z_pos = lap * lap_distance
        
        # Only draw if it's close to the player to save rendering performance
        if abs(config.car_pos[2] - z_pos) < 1000:
            strip_width = 15.0
            
            # White base line
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_QUADS)
            glVertex3f(-ROAD_HALF, 0.04, z_pos)
            glVertex3f(ROAD_HALF, 0.04, z_pos)
            glVertex3f(ROAD_HALF, 0.04, z_pos + strip_width)
            glVertex3f(-ROAD_HALF, 0.04, z_pos + strip_width)
            glEnd()
            
            # Black checkered squares
            glColor3f(0.0, 0.0, 0.0)
            glBegin(GL_QUADS)
            num_squares = 12
            sq_width = (ROAD_HALF * 2) / num_squares
            for i in range(num_squares):
                sx = -ROAD_HALF + i * sq_width
                if i % 2 == 0: # Front row squares
                    glVertex3f(sx, 0.05, z_pos)
                    glVertex3f(sx + sq_width, 0.05, z_pos)
                    glVertex3f(sx + sq_width, 0.05, z_pos + strip_width/2)
                    glVertex3f(sx, 0.05, z_pos + strip_width/2)
                else:          # Back row squares
                    glVertex3f(sx, 0.05, z_pos + strip_width/2)
                    glVertex3f(sx + sq_width, 0.05, z_pos + strip_width/2)
                    glVertex3f(sx + sq_width, 0.05, z_pos + strip_width)
                    glVertex3f(sx, 0.05, z_pos + strip_width)
            glEnd()

def showScreen():
    # Clear buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    STATE_TIME_SELECT = getattr(config, 'STATE_TIME_SELECT', 4)

    if config.current_state == config.STATE_MENU:
        draw_main_menu()
        
    elif config.current_state == STATE_TIME_SELECT:
        draw_time_select_menu()

    elif config.current_state in [config.STATE_RACE,
                                   config.STATE_FREE_ROAM,
                                   config.STATE_PAUSED]:
        
        # Draw sky first (without depth testing enabled yet)
        draw_sky()                     
        apply_camera()
        
        # --- THE ALLOWED EXCEPTION ---
        # Enabling Depth Test exactly as permitted to stop the see-through world bugs
        glEnable(GL_DEPTH_TEST)

        draw_ground_plane()
        draw_road()
        draw_lap_lines() 
        draw_environment()

        # Player car
        draw_car(True,
                 config.car_pos[0], config.car_pos[1], config.car_pos[2],
                 config.car_facing_angle)

        # AI cars
        for ai in config.ai_cars:
            draw_car(False,
                     ai["pos"][0], ai["pos"][1], ai["pos"][2],
                     ai["facing_angle"])

        # Disable Depth Test before 2D HUD so text draws perfectly on top
        glDisable(GL_DEPTH_TEST)

        # --- 2-D overlays ---
        if config.current_state == config.STATE_PAUSED:
            draw_pause_menu()
        else:
            draw_hud()

    # ============ ARCADE MODE RENDERING ============
    elif config.current_state == config.STATE_ARCADE:

        draw_arcade_sky()
        apply_camera()
        glEnable(GL_DEPTH_TEST)

        draw_arcade_ground()
        draw_arcade_road()
        draw_arcade_environment()
        draw_arcade_coins()
        draw_arcade_obstacles()

        # Player car (no AI in arcade)
        draw_car(True,
                 config.car_pos[0], config.car_pos[1], config.car_pos[2],
                 config.car_facing_angle)

        glDisable(GL_DEPTH_TEST)
        draw_arcade_hud()

    glutSwapBuffers()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Vector Velocity  |  CSE 423")

    generate_env_objects()

    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    glutMainLoop()


if __name__ == "__main__":
    main()