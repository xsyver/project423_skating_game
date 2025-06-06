from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random
import sys  # Adding sys import for exit functionality

# --- Player control states ---
player_lane     = 0      # -1 = left, 0 = middle, 1 = right
player_y        = 0.5    # Base Y position
jumping         = False  # In jump arc?
jump_start      = 0      # Time when jump started (ms)
jump_duration   = 600    # Jump duration in ms
jump_height_max = 2.0    # Peak jump height
jump_height     = 0.0    # Current vertical offset
ducking         = False  # Is player ducking?
duck_start      = 0      # Time when duck started
duck_duration   = 500    # Duck duration in ms (auto-release after this time)
player_life     = 5      # Player's life
hit_cooldown    = 0      # Cooldown timer for collision detection (in ms)
hit_cooldown_max = 500   # Maximum cooldown duration (500ms)
life_hit_cooldown= 0      # Cooldown timer for life collision detection (in ms)
life_hit_cooldown_max=500  # different variable for life as after getting a life you don't need cooldown for obstacle
road_offset    = 0.0     # Offset for stripe animation
road_speed     = 0.7    # Speed of road movement
stripe_length  = 5.0     # Length of each stripe along Z
stripe_spacing = 15.0    # Gap between stripes

# --- Shield variables ---
shield_active   = False  # Track if player has shield protection
shield_start    = 0      # When did we activate the shield?
shield_duration = 10000  # Shield lasts 10 seconds
shield_cooldown = 0      # Need to wait before picking up another shield

# --- Game stats ---
score          = 0       # Player score
game_time      = 0       # Time elapsed in game
distance       = 0       # Distance traveled (used internally, not displayed)

# --- Camera settings ---
camera_height  = 5       # Height of camera
camera_distance = 15     # Distance behind player
camera_mode    = 0       # 0 = normal, 1 = 3D view with orbit controls
camera_angle_x = 0       # Horizontal orbit angle
camera_angle_y = 30      # Vertical orbit angle

# --- Obstacle (car) states ---
obstacles      = []      # List of {'lane', 'z'}

# --- Human (NPC) states ---
humans         = []      # List of {'lane', 'z'}

# --- Bird obstacles ---
birds          = []      # List of {'lane', 'z', 'height'}

# --- Collect Lives ---
collect_lives  = []      # List of {'lane', 'z'}

# --- Collect Shields ---
collect_shields = []     # Keeps track of shield powerups on the track
max_shields = 1          # Only want one shield on screen at a time
shield_spawn_chance = 0.0015  # Made shields rarer - was too common at 0.003

# --- Environment objects ---
trees         = []      # List of tree positions

def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.8, 0.9, 1.0)  # Light blue sky
    
    # Initialize trees on both sides of the road
    global trees
    for z in range(-100, 50, 25):  # Trees every 25 units on z-axis
        # Left side trees with some randomness
        left_offset = random.uniform(-12, -8)
        trees.append({'x': left_offset, 'z': z, 'size': random.uniform(0.8, 1.2)})
        
        # Right side trees with some randomness
        right_offset = random.uniform(8, 12)
        trees.append({'x': right_offset, 'z': z, 'size': random.uniform(0.8, 1.2)})
        
        # Some additional trees with more variation
        if random.random() < 0.5:
            far_left = random.uniform(-15, -12)
            trees.append({'x': far_left, 'z': z + random.uniform(-10, 10), 'size': random.uniform(0.6, 1.0)})
            
        if random.random() < 0.5:
            far_right = random.uniform(12, 15)
            trees.append({'x': far_right, 'z': z + random.uniform(-10, 10), 'size': random.uniform(0.6, 1.0)})

def draw_lives():
    # Draw hearts in bottom left corner with more spacing between them
    for i in range(player_life):
        x = 30 + i * 50  # Increased spacing between hearts (from 30 to 50)
        y = 30           # Keep at bottom left
        draw_heart_2d(x, y)
    
    # Draw shield indicator when active
    if shield_active:
        now = glutGet(GLUT_ELAPSED_TIME)
        remaining = (shield_duration - (now - shield_start)) / 1000  # Convert to seconds
        
        # Shield icon at bottom right
        draw_shield_icon(700, 30)
        
        # Shield timer text
        shield_text = f"Shield: {remaining:.1f}s"
        draw_text(620, 60, shield_text)

# Draw a 2D shield icon for the HUD
def draw_shield_icon(x, y):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)  # Setup 2D projection
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw shield icon
    # Shield outline
    glColor3f(0.0, 0.4, 0.8)  # Blue
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y)  # Center
    
    radius = 20
    segments = 16
    for i in range(segments + 1):
        angle = i * 2.0 * math.pi / segments
        glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
    glEnd()
    
    # Shield border
    glColor3f(0.8, 0.8, 0.1)  # Gold
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    for i in range(segments):
        angle = i * 2.0 * math.pi / segments
        glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
    glEnd()
    
    # Shield center
    glColor3f(0.8, 0.1, 0.1)  # Red
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y)  # Center
    
    radius = 7
    for i in range(segments + 1):
        angle = i * 2.0 * math.pi / segments
        glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# Updated heart drawing function with smaller hearts and better separation
def draw_heart_2d(x, y):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)  # Setup 2D projection
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw a 2D heart based on the image
    glColor3f(1, 0, 0)  # Red color
    
    # Draw filled heart using triangles
    # Center point of the heart
    cx = x
    cy = y - 5
    size = 8  # Base size to scale the heart
    
    # Draw the main heart shape using a triangle fan
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(cx, cy)  # Center point
    
    # Draw the curved top of the heart
    for i in range(0, 181):
        angle = i * math.pi / 180.0
        # Left lobe
        if i <= 180:
            px = cx - size * 1.0 + size * 2.0 * math.cos(angle)
            py = cy + size * 2.0 + size * 1.8 * math.sin(angle)
            glVertex2f(px, py)
    
    # Connect to right lobe
    for i in range(0, 181):
        angle = (180 - i) * math.pi / 180.0
        # Right lobe
        px = cx + size * 1.0 + size * 2.0 * math.cos(angle)
        py = cy + size * 2.0 + size * 1.8 * math.sin(angle)
        glVertex2f(px, py)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_heart(x, y):
    glPushMatrix()
    glTranslatef(x-0.15, y, 0)
    glColor3f(1, 0, 0)
    glutSolidSphere(0.2, 32, 32)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x+0.15, y, 0)
    glColor3f(1, 0, 0)
    glutSolidSphere(0.2, 32, 32)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x, y-0.05, 0)
    glRotatef(90, 1, 0, 0)
    glColor3f(1, 0, 0)
    glutSolidCone(0.35, 0.5, 32, 32)
    glPopMatrix()


def check_collision():
    global player_life, hit_cooldown, life_hit_cooldown_max, life_hit_cooldown
    global shield_active, shield_start, shield_cooldown
    now = glutGet(GLUT_ELAPSED_TIME)
    
    # Check if shield has expired
    if shield_active and (now - shield_start) > shield_duration:
        shield_active = False
        print("Shield gone! You're vulnerable again!")
    
    # Check collision with cars and humans
    for obs in humans + obstacles:
        # Only check if in the same lane and close in Z
        if player_lane == obs['lane'] and abs(obs['z'] - 5) < 1.5:
            height = obs.get('height', 1.0)  # fallback to 1.0 if height missing

            # Skip collision if jumping over obstacle
            if jumping and jump_height > height:
                continue

            # Only reduce life if not on cooldown and shield not active
            if now - hit_cooldown > hit_cooldown_max and not shield_active:
                player_life -= 1
                hit_cooldown = now
                print(f"Hit! Lives left: {player_life}")
                if player_life <= 0:
                    game_over()
    
    # Check collision with birds - need to duck to avoid
    for bird in birds:
        # Only check if in the same lane and close in Z
        if player_lane == bird['lane'] and abs(bird['z'] - 5) < 1.5:
            # For birds, we need to be ducking to avoid them, otherwise collision
            # Skip collision check if ducking - we successfully ducked under the bird
            if ducking:
                continue
                
            # Only reduce life if not on cooldown and shield not active
            if now - hit_cooldown > hit_cooldown_max and not shield_active:
                player_life -= 1
                hit_cooldown = now
                print(f"Hit by bird! Lives left: {player_life}")
                if player_life <= 0:
                    game_over()
    
    # Collision detection for lives adds life up to 5
    for life in collect_lives[:]:
        # Only check if in the same lane and close in Z
        if player_lane == life['lane'] and abs(life['z'] - 5) < 1.5:
            # Only add life if not on cooldown
            if now - life_hit_cooldown > life_hit_cooldown_max:
                if player_life < 5:
                    player_life += 1
                    print(f"Collected life! Lives left: {player_life}")
                life_hit_cooldown = now
                collect_lives.remove(life)  # Remove the collected life
    
    # Collision detection for shields
    for shield in collect_shields[:]:
        # Only check if in the same lane and close in Z
        if player_lane == shield['lane'] and abs(shield['z'] - 5) < 1.5:
            # Only activate shield if not on cooldown
            if now - shield_cooldown > hit_cooldown_max:
                shield_active = True
                shield_start = now
                shield_cooldown = now
                print("Awesome! Shield activated! You're invincible for 10 seconds!")
                collect_shields.remove(shield)  # Remove the collected shield


# Unified person‑drawing
def draw_person(lane, z_pos, include_board=True):
    x = 4 * lane
    glPushMatrix()
    # Position Y based on board or floor
    y_off = player_y + jump_height if (include_board and lane == player_lane) else 0.0
    glTranslatef(x, y_off, z_pos)
    
    # No rotation for player - upright exactly as in the image
    
    if include_board:
        # Draw skateboard sideways as shown in the image
        # Skateboard deck - brown wooden color
        glColor3f(0.6, 0.3, 0.1)  # Brown color for wood
        glPushMatrix()
        glRotatef(90, 0, 1, 0)  # Rotate the board to be sideways
        glTranslatef(0, 0.1, 0)  # Position at player's feet
        glScalef(2.0, 0.1, 0.8)  # Flat board shape
        glutSolidCube(1)
        glPopMatrix()
        
        # Red stripe on top of board
        glColor3f(0.8, 0.0, 0.0)  # Red color
        glPushMatrix()
        glRotatef(90, 0, 1, 0)  # Rotate the stripe to be sideways
        glTranslatef(0, 0.16, 0)  # Just above the board
        glScalef(0.8, 0.05, 0.6)  # Thin stripe
        glutSolidCube(1)
        glPopMatrix()
        
        # Wheels - silver with metallic look
        glColor3f(0.8, 0.8, 0.8)  # Silver-gray for wheels
        for side in [-1, 1]:
            for front_back in [-1, 1]:
                glPushMatrix()
                glTranslatef(0, -0.05, side * 0.7 + front_back * 0.1)
                glutSolidTorus(0.08, 0.15, 8, 8)  # More realistic wheel shape
                glPopMatrix()
    
    # Blue torso - rounded at the shoulders
    glColor3f(0.0, 0.5, 1.0)  # Blue color for torso
    
    # Main torso
    glPushMatrix()
    glTranslatef(0, 1.0, 0)
    glScalef(0.6, 0.8, 0.4)  # Slightly shorter than original
    glutSolidCube(1)
    glPopMatrix()
    
    # Rounded shoulders (small spheres)
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.3, 1.3, 0)
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
    
    # Neck
    glPushMatrix()
    glTranslatef(0, 1.5, 0)
    glScalef(0.2, 0.2, 0.2)
    glutSolidCube(1)
    glPopMatrix()
    
    # Head - flesh colored with more detail
    glPushMatrix()
    glTranslatef(0, 1.8, 0)
    
    # Base head shape
    glColor3f(0.95, 0.75, 0.6)  # Skin tone
    glutSolidSphere(0.3, 10, 10)  # Rounded head
    
    # Hair/hat - black cap
    glColor3f(0.1, 0.1, 0.1)
    glPushMatrix()
    glTranslatef(0, 0.1, 0)
    glRotatef(-90, 1, 0, 0)  # Orient for cap
    glutSolidCone(0.31, 0.25, 8, 8)  # Cap shape
    glPopMatrix()
    
    # Face elements - simple features
    glColor3f(0.0, 0.0, 0.0)  # Black for eyes
    
    # Left eye
    glPushMatrix()
    glTranslatef(-0.1, 0.05, 0.25)
    glScalef(0.05, 0.1, 0.05)
    glutSolidCube(1)
    glPopMatrix()
    
    # Right eye
    glPushMatrix()
    glTranslatef(0.1, 0.05, 0.25)
    glScalef(0.05, 0.1, 0.05)
    glutSolidCube(1)
    glPopMatrix()
    
    # Simple smile
    glLineWidth(2.0)
    glBegin(GL_LINE_STRIP)
    glVertex3f(-0.1, -0.1, 0.28)
    glVertex3f(0, -0.15, 0.28)
    glVertex3f(0.1, -0.1, 0.28)
    glEnd()
    
    glPopMatrix()  # End head
    
    # Red legs - with better shape
    glColor3f(0.8, 0.1, 0.1)  # Red color for legs
    
    # Thigh segment
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.5, 0)
        glScalef(0.2, 0.4, 0.3)  # Thighs
        glutSolidCube(1)
        glPopMatrix()
    
    # Lower legs
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.2, 0)
        glScalef(0.15, 0.3, 0.25)  # Calves
        glutSolidCube(1)
        glPopMatrix()
    
    # Feet
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.02, 0.1)
        glScalef(0.18, 0.08, 0.4)  # Feet extended forward slightly
        glutSolidCube(1) 
        glPopMatrix()
    
    # Arms - blue sleeves with flesh hands
    for side in [-1, 1]:
        # Upper arm (blue)
        glColor3f(0.0, 0.5, 1.0)  # Blue to match shirt
        glPushMatrix()
        glTranslatef(side * 0.4, 1.2, 0)
        glRotatef(side * 15, 0, 0, 1)  # Angle slightly outward
        glScalef(0.15, 0.4, 0.15)
        glutSolidCube(1)
        glPopMatrix()
        
        # Forearm with slight bend (flesh colored)
        glColor3f(0.95, 0.75, 0.6)  # Skin tone
        glPushMatrix()
        glTranslatef(side * 0.45, 0.9, 0)
        glRotatef(side * 15, 0, 0, 1)
        glScalef(0.12, 0.3, 0.12)
        glutSolidCube(1)
        glPopMatrix()
        
        # Hand
        glPushMatrix()
        glTranslatef(side * 0.5, 0.7, 0)
        glutSolidSphere(0.08, 8, 8)
        glPopMatrix()
    
    glPopMatrix()  # End player

def draw_ducking_player(lane, z_pos, include_board=True):
    """Draw the player model in a ducking position"""
    x = 4 * lane
    glPushMatrix()
    # Position Y based on board or floor
    y_off = player_y + jump_height if (include_board and lane == player_lane) else 0.0
    glTranslatef(x, y_off, z_pos)
    
    if include_board:
        # Draw skateboard sideways as shown in the image
        # Skateboard deck - brown wooden color
        glColor3f(0.6, 0.3, 0.1)  # Brown color for wood
        glPushMatrix()
        glRotatef(90, 0, 1, 0)  # Rotate the board to be sideways
        glTranslatef(0, 0.1, 0)  # Position at player's feet
        glScalef(2.0, 0.1, 0.8)  # Flat board shape
        glutSolidCube(1)
        glPopMatrix()
        
        # Red stripe on top of board
        glColor3f(0.8, 0.0, 0.0)  # Red color
        glPushMatrix()
        glRotatef(90, 0, 1, 0)  # Rotate the stripe to be sideways
        glTranslatef(0, 0.16, 0)  # Just above the board
        glScalef(0.8, 0.05, 0.6)  # Thin stripe
        glutSolidCube(1)
        glPopMatrix()
        
        # Wheels - silver with metallic look
        glColor3f(0.8, 0.8, 0.8)  # Silver-gray for wheels
        for side in [-1, 1]:
            for front_back in [-1, 1]:
                glPushMatrix()
                glTranslatef(0, -0.05, side * 0.7 + front_back * 0.1)
                glutSolidTorus(0.08, 0.15, 8, 8)
                glPopMatrix()
    
    # Blue torso - lowered and bent forward for ducking
    glColor3f(0.0, 0.5, 1.0)  # Blue color for torso
    
    # Ducking torso - bent forward and lower
    glPushMatrix()
    glTranslatef(0, 0.7, 0.3)  # Lower position, slightly forward
    glRotatef(30, 1, 0, 0)  # Bent forward
    glScalef(0.6, 0.6, 0.4)  # Slightly smaller for ducking
    glutSolidCube(1)
    glPopMatrix()
    
    # Shoulders - lowered
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.3, 0.9, 0.3)  # Lower shoulders
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
    
    # Neck - bent forward
    glPushMatrix()
    glTranslatef(0, 1.0, 0.4)  # Lower and forward
    glScalef(0.2, 0.2, 0.2)
    glutSolidCube(1)
    glPopMatrix()
    
    # Head - lowered for ducking
    glPushMatrix()
    glTranslatef(0, 1.1, 0.6)  # Lower head position
    
    # Base head shape - looking down
    glColor3f(0.95, 0.75, 0.6)  # Skin tone
    glutSolidSphere(0.3, 10, 10)
    
    # Hat/hair
    glColor3f(0.1, 0.1, 0.1)
    glPushMatrix()
    glTranslatef(0, 0.1, 0)
    glRotatef(-120, 1, 0, 0)  # More angled forward
    glutSolidCone(0.31, 0.25, 8, 8)
    glPopMatrix()
    
    # Face elements - looking down
    glColor3f(0.0, 0.0, 0.0)
    
    # Eyes - not visible when looking down
    
    glPopMatrix()  # End head
    
    # Legs - bent for ducking
    glColor3f(0.8, 0.1, 0.1)  # Red color for legs
    
    # Bent thighs - almost horizontal
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.4, 0.2)
        glRotatef(80, 1, 0, 0)  # Bent forward horizontally 
        glScalef(0.2, 0.4, 0.3)
        glutSolidCube(1)
        glPopMatrix()
    
    # Lower legs - vertical
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.2, 0.6)  # Forward position
        glScalef(0.15, 0.3, 0.25)
        glutSolidCube(1)
        glPopMatrix()
    
    # Feet
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.25, 0.02, 0.7)  # Forward position
        glScalef(0.18, 0.08, 0.4)
        glutSolidCube(1) 
        glPopMatrix()
    
    # Arms - extended forward for balance while ducking
    for side in [-1, 1]:
        # Upper arm
        glColor3f(0.0, 0.5, 1.0)  # Blue to match shirt
        glPushMatrix()
        glTranslatef(side * 0.4, 0.8, 0.2)
        glRotatef(side * 15 + 45, 1, 0, 0)  # Extended forward
        glScalef(0.15, 0.4, 0.15)
        glutSolidCube(1)
        glPopMatrix()
        
        # Forearm
        glColor3f(0.95, 0.75, 0.6)  # Skin tone
        glPushMatrix()
        glTranslatef(side * 0.4, 0.7, 0.6)
        glRotatef(side * 10, 0, 0, 1)
        glScalef(0.12, 0.3, 0.12)
        glutSolidCube(1)
        glPopMatrix()
        
        # Hand
        glPushMatrix()
        glTranslatef(side * 0.4, 0.7, 0.9)
        glutSolidSphere(0.08, 8, 8)
        glPopMatrix()
    
    glPopMatrix()  # End player

def draw():
    global player_y  # Add global reference to avoid variable conflict
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # Player's position (used for camera focus)
    player_x = 4 * player_lane
    py = player_y + jump_height if jumping else player_y  # Use a local variable for clarity
    player_z = 5
    
    # Set camera based on current mode
    if camera_mode == 0:
        # Default camera position (behind and above player)
        x = 0  # Center aligned with road
        y = 5  # Slightly high viewing angle
        z = 15 # Behind the player
        
        # Look at a point ahead of the player
        target_x = 0
        target_y = 1  # Slightly above ground level
        target_z = -30  # Far ahead down the road
    
    elif camera_mode == 1:
        # 3D Orbit camera - circle around player based on camera_angle_x
        radius = camera_distance
        angle_rad = camera_angle_x * math.pi / 180.0
        height_angle_rad = camera_angle_y * math.pi / 180.0
        
        # Calculate camera position based on angles (spherical coordinates)
        x = player_x + radius * math.sin(angle_rad)
        z = player_z + radius * math.cos(angle_rad)
        y = camera_height * math.sin(height_angle_rad)
        
        # Always look at the player
        target_x = player_x
        target_y = py + 1  # Look at player's head
        target_z = player_z
    
    else:  # camera_mode == 2
        # First person view - from player's perspective
        x = player_x
        y = py + 1.8  # Eye level
        z = player_z
        
        # Look down the road
        target_x = player_x
        target_y = py + 1.5  # Slightly above eye level
        target_z = player_z - 30  # Far ahead
    
    gluLookAt(x, y, z, target_x, target_y, target_z, 0, 1, 0)

    draw_map()
    draw_obstacles()
    draw_humans()
    draw_collect_lives()
    draw_birds()  # Draw all birds
    draw_collect_shields()  # Draw all shields
    
    # Draw player based on ducking state (skip in first-person mode)
    if camera_mode != 2:  # Only draw player if not in first-person
        if ducking and player_lane == player_lane:
            draw_ducking_player(player_lane, 5, include_board=True)
        else:
            draw_person(player_lane, 5, include_board=True)
    
    draw_lives()  # Draw heart icons
    
    # Display score in the top left corner
    score_text = f"Score: {score}"
    draw_text(30, 570, score_text)
    
    # Display camera mode info when in 3D view
    if camera_mode == 1:
        view_text = "3D View - Use arrow keys to adjust camera"
        draw_text(30, 540, view_text)
    elif camera_mode == 2:
        view_text = "First Person View"
        draw_text(30, 540, view_text)
    
    glutSwapBuffers()

def display_text(text, x, y, size=0.1):
    glColor3f(1.0, 0.0, 0.0)  # Set the text color to red
    glRasterPos2f(x, y)  # Set the position on the screen
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))  # Display the character

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """
    Draws text on screen at specified coordinates with proper matrix handling.
    This is an improved version of display_text with proper OpenGL matrix handling.
    """
    glColor3f(1, 1, 1)  # White text by default
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    # Set up an orthographic projection that matches window coordinates
    gluOrtho2D(0, 800, 0, 600)  # left, right, bottom, top
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Draw text at (x, y) in screen coordinates
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    # Restore original projection and modelview matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def game_over():
    global player_life
    print("Game Over!")
    
    # Draw a game over screen
    def draw_game_over():
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Switch to orthographic projection for text rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, 800, 0, 600)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw game over text
        glColor3f(1.0, 0.0, 0.0)  # Red color
        glRasterPos2f(300, 400)
        for char in "GAME OVER":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
            
        # Draw restart instruction
        glColor3f(1.0, 1.0, 1.0)  # White color
        glRasterPos2f(250, 350)
        for char in "Press 'R' to restart":
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
            
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glutSwapBuffers()
    
    # Set display function to game over screen
    glutDisplayFunc(draw_game_over)
    # Let the game continue running, waiting for restart input
    # The player can restart by pressing 'r'
    
def reset_game():
    global player_life, player_lane, jumping, jump_height, road_offset, obstacles, humans, collect_lives
    global score, distance, game_time
    
    # Reset player state
    player_life = 5
    player_lane = 0
    jumping = False
    jump_height = 0.0
    
    # Reset game environment
    road_offset = 0.0
    obstacles = []
    humans = []
    collect_lives = []
    
    # Reset game stats
    score = 0
    distance = 0
    game_time = 0
    
    # Reset display function to the main game
    glutDisplayFunc(draw)

def draw_map():
    # Green grass on both sides
    glColor3f(0.1, 0.7, 0.1)  # Brighter green for grass
    
    # Left side grass
    glBegin(GL_QUADS)
    glVertex3f(-100, 0, -100); glVertex3f(-6, 0, -100)
    glVertex3f(-6, 0, 50); glVertex3f(-100, 0, 50)
    glEnd()
    
    # Right side grass
    glBegin(GL_QUADS)
    glVertex3f(6, 0, -100); glVertex3f(100, 0, -100)
    glVertex3f(100, 0, 50); glVertex3f(6, 0, 50)
    glEnd()
    
    # Road - dark gray/black
    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(-6, 0, -100); glVertex3f(6, 0, -100)
    glVertex3f(6, 0, 50); glVertex3f(-6, 0, 50)
    glEnd()

    # Lane lines - solid white lines on sides
    glColor3f(1, 1, 1)
    glLineWidth(3)
    
    # Left lane line
    glBegin(GL_LINES)
    glVertex3f(-2, 0.01, -100); glVertex3f(-2, 0.01, 50)
    glEnd()
    
    # Right lane line
    glBegin(GL_LINES)
    glVertex3f(2, 0.01, -100); glVertex3f(2, 0.01, 50)
    glEnd()
    
    # Center dashed line (white blocks in the middle of the road)
    glColor3f(1, 1, 1)
    pattern = 5.0  # Length of each dash
    spacing = 10.0  # Space between dashes
    offset = road_offset % (pattern + spacing)
    count = int(150/(pattern + spacing)) + 2
    
    for i in range(count):
        z0 = -100 + i*(pattern + spacing) - offset
        # Draw white rectangle in the middle
        glBegin(GL_QUADS)
        glVertex3f(-1.0, 0.02, z0)
        glVertex3f(1.0, 0.02, z0)
        glVertex3f(1.0, 0.02, z0+pattern)
        glVertex3f(-1.0, 0.02, z0+pattern)
        glEnd()
    
    # Draw trees
    for tree in trees:
        draw_tree(tree['x'], tree['z'], tree['size'])

def draw_tree(x, z, size):
    glPushMatrix()
    glTranslatef(x, 0, z)
    glScalef(size, size, size)

    # Draw trunk (brown rectangle)
    glColor3f(0.55, 0.27, 0.07)  # Brown color for trunk
    glPushMatrix()
    glTranslatef(0, 1.5, 0)
    glScalef(0.5, 3, 0.5)
    glutSolidCube(1)
    glPopMatrix()

    # Draw foliage (green triangle)
    glColor3f(0.0, 0.5, 0.0)  # Dark green color for foliage
    
    # Draw a cone shaped tree top
    glPushMatrix()
    glTranslatef(0, 3.5, 0)
    glRotatef(-90, 1, 0, 0)  # Orient the cone upward
    glutSolidCone(2.0, 4.0, 8, 8)  # Use cone for triangular tree top
    glPopMatrix()

    glPopMatrix()

def draw_obstacles():
    for obs in obstacles:
        draw_car(obs['lane'], obs['z'])

def draw_car(lane, z):
    x = 4*lane
    glPushMatrix(); 
    glTranslatef(x, 0.25, z)
    
    # Rotate car to be perpendicular to the road (like a crossing obstacle)
    glRotatef(90, 0, 1, 0)
    
    # Body - lower and longer
    glColor3f(0.7, 0.2, 0.2)
    glPushMatrix(); 
    glScalef(1.0, 0.4, 2.2); 
    glutSolidCube(1); 
    glPopMatrix()
    
    # Roof
    glColor3f(0.5, 0.5, 0.5)
    glPushMatrix(); 
    glTranslatef(0, 0.3, 0); 
    glScalef(0.6, 0.2, 1.4); 
    glutSolidCube(1); 
    glPopMatrix()
    
    # Wheels
    glColor3f(0.1, 0.1, 0.1)
    for wx in [-0.4, 0.4]:
        for wz in [-0.9, 0.9]:
            glPushMatrix()
            glTranslatef(wx, -0.2, wz)
            glRotatef(90, 0, 0, 1)  # Rotate wheels for proper orientation
            gluCylinder(gluNewQuadric(), 0.2, 0.2, 0.2, 12, 1)
            glPopMatrix()
    
    glPopMatrix()

def draw_humans():
    for h in humans:
        draw_pedestrian(h['lane'], h['z'])

# New function for drawing pedestrians (non-skateboarders)
def draw_pedestrian(lane, z_pos):
    x = 4 * lane
    glPushMatrix()
    glTranslatef(x, 0, z_pos)
    
    # Pedestrians face toward the player (rotate 180 degrees)
    glRotatef(0, 0, 1, 0)  # No rotation - they'll face the oncoming skateboarder
    
    # Torso
    glColor3f(random.uniform(0.2, 0.8), random.uniform(0.2, 0.8), random.uniform(0.2, 0.8))  # Random clothing color
    glPushMatrix()
    glTranslatef(0, 1.0, 0)
    glScalef(0.6, 1.0, 0.4)
    glutSolidCube(1)
    glPopMatrix()
    
    # Head
    glColor3f(1.0, 0.8, 0.6)  # Skin tone
    glPushMatrix()
    glTranslatef(0, 2.0, 0)
    glutSolidSphere(0.3, 16, 16)
    glPopMatrix()
    
    # Arms - slightly out to the sides
    glColor3f(1.0, 0.8, 0.6)  # Skin tone
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.4, 1.0, 0)
        glRotatef(side * 15, 0, 0, 1)  # Angle slightly outward
        glRotatef(90, 1, 0, 0)  # Rotate to point down
        gluCylinder(gluNewQuadric(), 0.1, 0.1, 0.7, 12, 1)
        glPopMatrix()
    
    # Legs - straight down
    glColor3f(0.2, 0.2, 0.5)  # Blue jeans
    for side in [-1, 1]:
        glPushMatrix()
        glTranslatef(side * 0.2, 0.5, 0)
        glRotatef(90, 1, 0, 0)  # Rotate to point down
        gluCylinder(gluNewQuadric(), 0.15, 0.15, 0.5, 12, 1)
        glPopMatrix()
    
    glPopMatrix()

# Player will collect life and it will increase lives upto 5
def draw_collect_lives():
    for l in collect_lives:
        draw_collect_life(l['lane'], l['z'])

# drawing 3D heart
def draw_collect_life(lane, z):
    x = 4 * lane
    glPushMatrix()
    glTranslatef(x-0.25, 2, z)
    glColor3f(1, 0, 0)
    glutSolidSphere(0.5, 32, 32)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x+0.25, 2, z)
    glColor3f(1, 0, 0)
    glutSolidSphere(0.5, 32, 32)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(x, 1.8, z)
    glRotatef(90, 1, 0, 0)
    glColor3f(1, 0, 0)
    glutSolidCone(0.75, 1.2, 32, 32)
    glPopMatrix()

# Drawing shield collectibles
def draw_collect_shields():
    for shield in collect_shields:
        draw_shield(shield['lane'], shield['z'])

# 3D shield object
def draw_shield(lane, z):
    x = 4 * lane
    glPushMatrix()
    glTranslatef(x, 2, z)  # Changed Y position from 0 to 2 to make it float at same height as hearts
    
    # Shield body - blue circular shield
    glColor3f(0.0, 0.4, 0.8)  # Blue color
    
    # Main shield disc
    glPushMatrix()
    glRotatef(90, 1, 0, 0)  # Orient properly
    gluDisk(gluNewQuadric(), 0, 0.6, 20, 2)  # Circular shield
    glPopMatrix()
    
    # Shield border
    glColor3f(0.8, 0.8, 0.1)  # Gold color for border
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    gluDisk(gluNewQuadric(), 0.6, 0.7, 20, 2)  # Border ring
    glPopMatrix()
    
    # Shield center ornament
    glColor3f(0.8, 0.1, 0.1)  # Red center
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    gluDisk(gluNewQuadric(), 0, 0.2, 16, 1)  # Center circle
    glPopMatrix()
    
    # Add slight bobbing animation to make it more noticeable
    glPushMatrix()
    glTranslatef(0, 0.2, 0)
    glRotatef(glutGet(GLUT_ELAPSED_TIME) / 10 % 360, 0, 1, 0)  # Slow rotation to catch attention
    glColor3f(0.9, 0.9, 0.1)  # Bright gold color for glow effect
    glutSolidTorus(0.05, 0.8, 8, 16)  # Add a glowing ring around the shield
    glPopMatrix()
    
    glPopMatrix()

# Draw and update birds
def draw_birds():
    for bird in birds:
        draw_bird(bird['lane'], bird['z'], bird['height'])

# Function to draw a bird
def draw_bird(lane, z, height):
    x = 4 * lane
    glPushMatrix()
    glTranslatef(x, height, z)
    
    # Bird body - small oval shape
    glColor3f(0.3, 0.3, 0.7)  # Blue-gray color for bird
    
    # Main body
    glPushMatrix()
    glScalef(0.5, 0.3, 0.7)
    glutSolidSphere(0.8, 10, 10)
    glPopMatrix()
    
    # Head
    glPushMatrix()
    glTranslatef(0, 0.1, 0.7)
    glColor3f(0.4, 0.4, 0.8)  # Slightly lighter color for head
    glutSolidSphere(0.3, 8, 8)
    glPopMatrix()
    
    # Eyes
    glColor3f(0, 0, 0)  # Black eyes
    glPushMatrix()
    glTranslatef(0.15, 0.2, 0.9)
    glutSolidSphere(0.07, 6, 6)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(-0.15, 0.2, 0.9)
    glutSolidSphere(0.07, 6, 6)
    glPopMatrix()
    
    # Beak
    glColor3f(1.0, 0.5, 0.0)  # Orange beak
    glPushMatrix()
    glTranslatef(0, 0.05, 1.0)
    glRotatef(90, 1, 0, 0)
    glutSolidCone(0.1, 0.3, 8, 8)
    glPopMatrix()
    
    # Wings - flapping based on time
    wing_flap = math.sin(glutGet(GLUT_ELAPSED_TIME) / 100.0) * 30  # Oscillate between -30 and 30 degrees
    
    # Left wing
    glColor3f(0.2, 0.2, 0.6)  # Darker blue for wings
    glPushMatrix()
    glTranslatef(-0.4, 0.1, 0)
    glRotatef(wing_flap - 20, 0, 0, 1)  # Wing flapping animation
    glScalef(0.8, 0.1, 0.5)
    glutSolidCube(1)
    glPopMatrix()
    
    # Right wing
    glPushMatrix()
    glTranslatef(0.4, 0.1, 0)
    glRotatef(-wing_flap + 20, 0, 0, 1)  # Wing flapping animation (opposite)
    glScalef(0.8, 0.1, 0.5)
    glutSolidCube(1)
    glPopMatrix()
    
    # Tail
    glColor3f(0.3, 0.3, 0.7)
    glPushMatrix()
    glTranslatef(0, 0, -0.5)
    glRotatef(180, 0, 1, 0)
    glutSolidCone(0.2, 0.5, 8, 8)
    glPopMatrix()
    
    glPopMatrix()

def reshape(w,h):
    glViewport(0,0,w,h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, w/h if h else 1, 1.0, 200.0)
    glMatrixMode(GL_MODELVIEW)

def update():
    global jumping, jump_height, road_offset, obstacles, humans, player_life, collect_lives
    global score, distance, game_time, trees, birds, ducking, duck_start, collect_shields
    
    now = glutGet(GLUT_ELAPSED_TIME)
    
    # Update game time and score
    game_time = now / 1000  # Convert to seconds
    distance += road_speed * 10  # Internal distance tracking (not displayed)
    
    # Simpler scoring system - increment score more slowly
    # Add points based on time survived and obstacles passed
    if now % 30 == 0:  # Only increment score periodically to slow it down
        score += 1  # Basic score increment just for surviving
    
    # Jump
    if jumping:
        elapsed = now - jump_start
        t = elapsed / jump_duration
        if t >= 1.0:
            jumping = False; jump_height = 0.0
        else:
            jump_height = jump_height_max * math.sin(math.pi * t)
    
    # Duck timing - auto-release after duck_duration
    if ducking:
        elapsed = now - duck_start
        if elapsed >= duck_duration:
            ducking = False

    # Road animate
    road_offset += road_speed

    # Move obstacles
    for obs in obstacles[:]:
        obs['z'] += road_speed
        if obs['z'] > 20: 
            obstacles.remove(obs)
            score += 5  # Award points for successfully avoiding a car

    # Move humans
    for h in humans[:]:
        h['z'] += road_speed
        if h['z'] > 20: 
            humans.remove(h)
            score += 10  # Award points for successfully avoiding a human

    # Move birds
    for bird in birds[:]:
        bird['z'] += road_speed
        if bird['z'] > 20: 
            birds.remove(bird)
            score += 8  # Award points for successfully avoiding a bird
        
    # Remove lives after getting out of display
    for l in collect_lives[:]:
        l['z'] += road_speed
        if l['z'] > 20: collect_lives.remove(l)
        
    # Move shields collectibles
    for shield in collect_shields[:]:
        shield['z'] += road_speed
        if shield['z'] > 20: collect_shields.remove(shield)
        
    # Move trees along with the road
    for tree in trees[:]:
        tree['z'] += road_speed
        # If a tree goes out of view, move it back to the far end with random x position
        if tree['z'] > 30:
            tree['z'] = -100 + random.uniform(-20, 20)
            if tree['x'] < 0:  # Left side
                tree['x'] = random.uniform(-15, -8)
            else:  # Right side
                tree['x'] = random.uniform(8, 15)
            tree['size'] = random.uniform(0.6, 1.2)  # Randomize size for variety

    # Spawn normal obstacles
    if random.random() < 0.01:  # 5x more cars (from 0.002 to 0.01)
        obstacles.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
    if random.random() < 0.007:  # 7x more humans (from 0.001 to 0.007)
        humans.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
    if random.random() < 0.001:  # 2x more collectible lives (from 0.0005 to 0.001)
        collect_lives.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
    # Spawn shield collectibles (rare)
    if random.random() < shield_spawn_chance and len(collect_shields) < max_shields:  # Reduced spawn chance and limit to one shield
        collect_shields.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
        
    # Spawn birds at flying height (new)
    if random.random() < 0.005:  # Bird spawn rate
        birds.append({
            'lane': random.choice([-1,0,1]), 
            'z': -100.0, 
            'height': random.uniform(1.5, 2.5)  # Height that requires ducking
        })

    check_collision()
    glutPostRedisplay()

def keyboard(key,x,y):
    global player_lane, jumping, jump_start, camera_mode, road_speed, ducking, duck_start
    
    k = key.decode('utf-8')
    if k=='a' and player_lane> -1: 
        player_lane-=1
    elif k=='d' and player_lane< 1: 
        player_lane+=1
    elif k==' ' and not jumping:
        jumping=True; jump_start = glutGet(GLUT_ELAPSED_TIME)
    elif k=='s' and not jumping:  # 'S' key for ducking (only when not jumping)
        ducking = True
        duck_start = glutGet(GLUT_ELAPSED_TIME)
    elif k=='v':  # Toggle camera view
        camera_mode = (camera_mode + 1) % 3
        print(f"Camera mode switched to: {camera_mode}")
    elif k=='+' or k=='=':  # Speed up
        road_speed += 0.1
    elif k=='-' or k=='_':  # Slow down
        road_speed = max(0.1, road_speed - 0.1)
    elif k=='r': 
        reset_game()
    elif k=='q': 
        sys.exit()

def specialKeyListener(key, x, y):
    """
    Handles special key inputs (arrow keys) for adjusting camera settings.
    """
    global camera_angle_x, camera_angle_y, camera_distance, camera_height
    
    # In 3D view mode, arrow keys rotate the camera around the player
    if camera_mode == 1:  # 3D orbit mode
        # Rotate camera left (LEFT arrow key)
        if key == GLUT_KEY_LEFT:
            camera_angle_x = (camera_angle_x - 5) % 360
        
        # Rotate camera right (RIGHT arrow key)
        elif key == GLUT_KEY_RIGHT:
            camera_angle_x = (camera_angle_x + 5) % 360
        
        # Adjust camera height angle (UP arrow key)
        elif key == GLUT_KEY_UP:
            camera_angle_y = min(80, camera_angle_y + 5)  # Limit to 80 degrees
        
        # Adjust camera height angle (DOWN arrow key)
        elif key == GLUT_KEY_DOWN:
            camera_angle_y = max(5, camera_angle_y - 5)  # Don't go below 5 degrees
    
    # In standard view, arrow keys adjust camera height and distance
    else:
        # Move camera up (UP arrow key)
        if key == GLUT_KEY_UP:
            camera_height += 1
        
        # Move camera down (DOWN arrow key)
        elif key == GLUT_KEY_DOWN:
            camera_height = max(1, camera_height - 1)
        
        # Move camera closer (LEFT arrow key)
        elif key == GLUT_KEY_LEFT:
            camera_distance = max(5, camera_distance - 1)
        
        # Move camera farther (RIGHT arrow key)
        elif key == GLUT_KEY_RIGHT:
            camera_distance += 1

def reset_player():
    global player_lane, jumping, jump_height
    player_lane = 0; jumping=False; jump_height=0.0

def main():
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(800,600)
    glutCreateWindow(b"3D SkateShift")
    init()
    glutDisplayFunc(draw)
    glutReshapeFunc(reshape)
    glutIdleFunc(update)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(specialKeyListener)
    glutMainLoop()

if __name__=="__main__": 
    main()
