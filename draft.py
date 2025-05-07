from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import sys

# Define missing GLUT font constants if they're not available
if not hasattr(GLUT, 'GLUT_BITMAP_HELVETICA_18'):
    GLUT_BITMAP_HELVETICA_18 = None
if not hasattr(GLUT, 'GLUT_BITMAP_HELVETICA_12'):
    GLUT_BITMAP_HELVETICA_12 = None
if not hasattr(GLUT, 'GLUT_BITMAP_TIMES_ROMAN_24'):
    GLUT_BITMAP_TIMES_ROMAN_24 = None

# Camera-related variables
camera_pos = (0, 6, 15)  # Default camera position (slightly elevated behind player)
camera_distance = 15     # Distance from camera target
camera_orbit_angle = 0   # Horizontal orbit angle around player
camera_height_angle = 20 # Vertical angle (elevation)
camera_target = (0, 2, 0) # Target to look at (will be updated to player position)
fovY = 75  # Field of view
camera_mode = "follow"   # Camera mode: "follow", "orbit", "fixed", "first-person"

# --- Environment variables ---
sky_color = (0.6, 0.8, 1.0)  # Lighter blue for sky
road_color = (0.2, 0.2, 0.2)  # Darker gray for road
grass_color = (0.2, 0.7, 0.2)  # Green for roadside
sunset_mode = False  # Toggle for sunset color theme
tree_offset = 0.0    # Offset for tree movement
lamp_offset = 0.0    # Offset for lamp movement
player_tilt = 15.0   # Tilt angle for the player and skateboard
player_stance = 90.0  # Player stands sideways on board (perpendicular to movement)
game_over_state = False  # Track if game is over
distance_traveled = 0.0  # Track distance traveled in meters

# --- Road variables ---
stripe_length = 5.0   # Length of the road stripes
stripe_spacing = 5.0  # Space between road stripes

# --- Player control states ---
player_lane     = 0      # -1 = left, 0 = middle, 1 = right
player_y        = 0.5    # Base Y position
jumping         = False  # In jump arc?
ducking         = False  # Is player ducking?
duck_start      = 0      # Time when duck started (ms)
duck_duration   = 600    # Duck duration in ms
duck_height     = 0.7    # How much player height is reduced when ducking
jump_start      = 0      # Time when jump started (ms)
jump_duration   = 600    # Jump duration in ms
jump_height_max = 2.0    # Peak jump height
jump_height     = 0.0    # Current vertical offset
player_life     = 5      # Player's life
hit_cooldown    = 0      # Cooldown timer for collision detection (in ms)
hit_cooldown_max = 500   # Maximum cooldown duration (500ms)
life_hit_cooldown= 0     # Cooldown timer for life collision detection (in ms)
life_hit_cooldown_max=500  # different variable for life as after getting a life you don't need cooldown for obstacle
road_offset    = 0.0     # Offset for stripe animation
road_speed     = 0.3     # Base speed of road movement
max_road_speed = 1.0     # Increased maximum road speed for higher challenge
game_time      = 0       # Game time in milliseconds
speed_increase_interval = 8000  # Reduce interval for faster difficulty progression (8 seconds)
obstacle_frequency_multiplier = 2.0  # Increased from 1.0 for higher initial difficulty

# --- Player height variables ---
player_height_normal = 2.0  # Normal player height
player_height_ducking = 1.0  # Height when ducking

# --- Score variable ---
score_multiplier = 1.0  # Default score multiplier

# --- Obstacle (car) states ---
obstacles      = []      # List of {'lane', 'z'}

# --- Human (NPC) states ---
humans         = []      # List of {'lane', 'z'}

# --- Collect Lives ---
collect_lives  = []      # List of {'lane', 'z'}

# --- Obstacle types ---
OBSTACLE_CAR = 'car'
OBSTACLE_BIRD = 'bird'  # New flying bird obstacle type

# Set this to completely disable all powerup functionality
enable_powerups = False

# Define lane positions as a global lookup table to avoid calculations
lane_positions = {-1: -4, 0: 0, 1: 4}

def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.8, 0.9, 1.0)  # Light blue sky
    
    # Enable blending for transparency effects
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

# Update draw_lives to position hearts in the top-left corner
def draw_lives():
    glColor3f(1, 0, 0)  # Red color
    for i in range(player_life):
        x = -7.5 + i * 0.5  # Adjusted spacing for top-left corner
        y = 5.5  # Top-left corner position
        draw_heart(x, y)

def draw_heart(x, y):
    glBegin(GL_TRIANGLES)
    # Left half of heart
    glVertex2f(x, y)
    glVertex2f(x-0.25, y+0.25)
    glVertex2f(x-0.125, y+0.5)
    
    # Right half of heart
    glVertex2f(x, y)
    glVertex2f(x+0.25, y+0.25)
    glVertex2f(x+0.125, y+0.5)
    
    # Fill the middle
    glVertex2f(x-0.125, y+0.5)
    glVertex2f(x, y+0.25)
    glVertex2f(x+0.125, y+0.5)
    glEnd()


def check_collision():
    global player_lane, player_life, game_over_state, hit_cooldown, life_hit_cooldown

    # Skip collision detection if on cooldown
    current_time = glutGet(GLUT_ELAPSED_TIME)
    if current_time - hit_cooldown < hit_cooldown_max:
        return
        
    # Player collision detection - use actual player position
    player_z = 0
    player_height = player_height_ducking if ducking else player_height_normal
    
    # Check obstacle collisions
    for obs in obstacles[:]:
        # Skip obstacles that are past the player
        if obs['z'] > 5:
            continue
        
        # Check lane alignment
        if obs['lane'] != player_lane:
            continue
        
        # Calculate horizontal distance
        dist = abs(player_z - obs['z'])
        
        # If obstacle is near player (1 unit collision box)
        if dist < 1.0:
            # For birds, check height - only collide if not ducking
            if obs.get('type') == OBSTACLE_BIRD:
                if not ducking:
                    # Bird collision - lose life
                    handle_collision(obs)
                    return
            # For cars, check height - only collide if not jumping high enough
            else:
                if jump_height < 1.0:  # Car height threshold
                    # Car collision - lose life
                    handle_collision(obs)
                    return
    
    # Check collectible lives collision - separate cooldown for lives
    if current_time - life_hit_cooldown < life_hit_cooldown_max:
        return
        
    for life in collect_lives[:]:
        if life['lane'] == player_lane and abs(player_z - life['z']) < 1.0:
            collect_lives.remove(life)
            player_life = min(player_life + 1, 10)  # Maximum of 10 lives
            life_hit_cooldown = current_time
            # Play sound effect would go here in a complete game
            return

def handle_collision(obstacle):
    global player_life, game_over_state, hit_cooldown
    
    # Remove the obstacle
    obstacles.remove(obstacle)
    
    # No shield, take damage
    player_life -= 1
    play_sound("hit")
    
    # Set cooldown to prevent multiple hits in succession
    hit_cooldown = glutGet(GLUT_ELAPSED_TIME)
    
    if player_life <= 0:
        game_over_state = True
        play_sound("game_over")
        return False
    
    return True

# Unified person‑drawing
def draw_person(lane, z_pos, include_board=True):
    x = 4 * lane
    glPushMatrix()
    # Position Y based on board or floor
    y_off = player_y + jump_height if (include_board and lane == player_lane) else 0.0
    glTranslatef(x, y_off, z_pos)
    
    # Apply proper skateboard stance and tilting for player
    if include_board and lane == player_lane:
        # Rotate entire character/board to stand sideways (perpendicular to movement)
        glRotatef(player_stance, 0, 1, 0)  # Rotate 90 degrees around Y axis to face right
        
        # Apply tilt when changing lanes (leaning into turns)
        tilt_direction = -1 if player_lane > 0 else 1 if player_lane < 0 else 0
        # Tilt the board and player when turning
        glRotatef(player_tilt * tilt_direction * 0.5, 0, 0, 1)  # Reduced tilt amount by 50%
    
    # Skateboard (improved stylistic design with curved edges and more details)
    if include_board:
        # Main board (deck) with curved shape
        glColor3f(0.6, 0.4, 0.2)  # Wooden brown color
        glPushMatrix()
        
        # Draw a more stylish deck with curved shape
        glTranslatef(0, -0.1, 0)
        
        # Center part of the board (main deck)
        glBegin(GL_QUADS)
        # Top face
        glVertex3f(-2.3, 0.05, -0.7)
        glVertex3f( 2.3, 0.05, -0.7)
        glVertex3f( 2.3, 0.05,  0.7)
        glVertex3f(-2.3, 0.05,  0.7)
        
        # Bottom face
        glVertex3f(-2.3, -0.05, -0.7)
        glVertex3f( 2.3, -0.05, -0.7)
        glVertex3f( 2.3, -0.05,  0.7)
        glVertex3f(-2.3, -0.05,  0.7)
        
        # Front edge - curved up
        glVertex3f( 2.3,  0.05, -0.7)
        glVertex3f( 2.5,  0.15, -0.6)
        glVertex3f( 2.5,  0.15,  0.6)
        glVertex3f( 2.3,  0.05,  0.7)
        
        # Back edge - curved up
        glVertex3f(-2.3,  0.05, -0.7)
        glVertex3f(-2.5,  0.15, -0.6)
        glVertex3f(-2.5,  0.15,  0.6)
        glVertex3f(-2.3,  0.05,  0.7)
        glEnd()
        
        # Draw the curved nose and tail
        glBegin(GL_TRIANGLES)
        # Nose (front) curve
        glVertex3f( 2.5,  0.15, -0.6)
        glVertex3f( 2.7,  0.25,  0.0)
        glVertex3f( 2.5,  0.15,  0.6)
        
        # Tail (back) curve
        glVertex3f(-2.5,  0.15, -0.6)
        glVertex3f(-2.7,  0.25,  0.0)
        glVertex3f(-2.5,  0.15,  0.6)
        glEnd()
        
        glPopMatrix()
        
        # Board details - grip tape (top surface)
        glColor3f(0.1, 0.1, 0.1)  # Dark gray/black for grip tape
        glPushMatrix()
        glTranslatef(0, 0.01, 0)
        
        # Grip tape (slightly smaller than board)
        glBegin(GL_QUADS)
        glVertex3f(-2.2, 0.06, -0.65)
        glVertex3f( 2.2, 0.06, -0.65)
        glVertex3f( 2.2, 0.06,  0.65)
        glVertex3f(-2.2, 0.06,  0.65)
        glEnd()
        
        # Add skateboard graphic/logo
        glColor3f(0.9, 0.1, 0.1)  # Red logo
        glBegin(GL_QUADS)
        glVertex3f(-0.8, 0.07, -0.3)
        glVertex3f( 0.8, 0.07, -0.3)
        glVertex3f( 0.8, 0.07,  0.3)
        glVertex3f(-0.8, 0.07,  0.3)
        glEnd()
        
        glPopMatrix()
        
        # Trucks and wheels
        for tz in [-0.8, 0.8]:
            # Draw wheels directly without the grey parts underneath
            wheel_color = (0.2, 0.2, 0.2)  # Dark gray/black wheels
            wheel_positions = [(-1.8, tz), (1.8, tz)]
            
            for wx, wz in wheel_positions:
                glPushMatrix()
                glTranslatef(wx, -0.25, wz)  # Raised position to be right under the board
                
                # Wheel body (urethane)
                glColor3f(*wheel_color)
                glRotatef(90, 0, 1, 0)
                gluDisk(gluNewQuadric(), 0, 0.3, 12, 1)
                gluCylinder(gluNewQuadric(), 0.3, 0.3, 0.2, 12, 1)
                glTranslatef(0, 0, 0.2)
                gluDisk(gluNewQuadric(), 0, 0.3, 12, 1)
                
                # Wheel core/bearing
                glColor3f(0.8, 0.8, 0.8)  # Light gray for bearing
                glTranslatef(0, 0, -0.1)
                gluDisk(gluNewQuadric(), 0, 0.1, 8, 1)
                glPopMatrix()

    # Player character with proper staggered stance (when on board)
    if include_board and lane == player_lane:
        # Apply ducking transformation if player is ducking
        duck_scale = 1.0
        if ducking:
            # Lower the player's height when ducking
            duck_scale = 1.0 - duck_height
            glTranslatef(0, -0.8, 0)  # Lower the entire player model
            
        # Torso - turned sideways
        glColor3f(0.2, 0.5, 0.8)  # Blue shirt for player
        glPushMatrix()
        if ducking:
            # When ducking, torso is more horizontal
            glTranslatef(0, 1.6, 0.3)
            glRotatef(30, 0, 0, 1)  # Tilt torso forward
            glScalef(0.8, 0.9, 0.5)  # Squash slightly
        else:
            glTranslatef(0, 2.0, 0)
            glScalef(0.8, 1.2, 0.5)
        glutSolidCube(1)
        glPopMatrix()
        
        # Head - turned slightly to look forward
        glColor3f(1.0, 0.8, 0.6)  # Skin tone
        glPushMatrix()
        if ducking:
            # Head positioned lower and more forward when ducking
            glTranslatef(0, 2.2, 0.5)
            glRotatef(-30, 0, 1, 0)  # Head turned to look in direction of travel
            glRotatef(30, 0, 0, 1)   # Head tilted with body
        else:
            glTranslatef(0, 3.1, 0)
            glRotatef(-30, 0, 1, 0)  # Head turned to look in direction of travel
        glutSolidSphere(0.4, 16, 16)
        
        # Hair
        glColor3f(0.1, 0.1, 0.1)  # Dark hair
        glTranslatef(0, 0.2, 0)
        glScalef(0.42, 0.2, 0.42)
        glutSolidSphere(1.0, 16, 16)
        glPopMatrix()
        
        # Arms adjusted for ducking or normal position
        if ducking:
            # Arms stretched forward when ducking
            # Front arm
            glPushMatrix()
            glColor3f(0.9, 0.8, 0.6)  # Skin tone
            glTranslatef(0, 1.9, 0.6)  # More forward position
            glRotatef(60, 1, 0, 0)     # More horizontal
            glRotatef(20, 0, 0, 1)     # Slightly out
            gluCylinder(gluNewQuadric(), 0.12, 0.1, 0.7, 12, 1)
            glPopMatrix()
            
            # Back arm
            glPushMatrix()
            glColor3f(0.9, 0.8, 0.6)  # Skin tone
            glTranslatef(0, 1.9, -0.1)  # Back arm position
            glRotatef(-30, 1, 0, 0)     # Backward stretching
            glRotatef(-20, 0, 0, 1)     # Slightly out
            gluCylinder(gluNewQuadric(), 0.12, 0.1, 0.7, 12, 1)
            glPopMatrix()
        else:
            # Front arm (pointing forward)
            glPushMatrix()
            glColor3f(0.9, 0.8, 0.6)  # Skin tone
            glTranslatef(0, 2.5, 0.3)  # Front arm position
            glRotatef(30, 1, 0, 0)     # Slightly forward
            glRotatef(20, 0, 0, 1)     # Slightly out
            gluCylinder(gluNewQuadric(), 0.12, 0.1, 0.7, 12, 1)
            glPopMatrix()
            
            # Back arm (pointing back for balance)
            glPushMatrix()
            glColor3f(0.9, 0.8, 0.6)  # Skin tone
            glTranslatef(0, 2.5, -0.3)  # Back arm position
            glRotatef(-30, 1, 0, 0)     # Slightly backward
            glRotatef(-20, 0, 0, 1)     # Slightly out
            gluCylinder(gluNewQuadric(), 0.12, 0.1, 0.7, 12, 1)
            glPopMatrix()
        
        # Legs with better shape and positioning
        # Front leg (properly attached to the body)
        glPushMatrix()
        glColor3f(0.1, 0.1, 0.5)  # Blue jeans
        
        # Upper front leg - thigh
        glTranslatef(0, 1.5, 0.3)  # Start from torso connection point
        glRotatef(60, 1, 0, 0)     # Angle downward
        gluCylinder(gluNewQuadric(), 0.15, 0.15, 0.7, 12, 1)
        
        # Knee joint
        glTranslatef(0, 0, 0.7)
        glutSolidSphere(0.16, 8, 8)
        
        # Lower front leg - calf
        glRotatef(-30, 1, 0, 0)    # Bend at knee
        gluCylinder(gluNewQuadric(), 0.15, 0.14, 0.8, 12, 1)
        
        # Ankle joint
        glTranslatef(0, 0, 0.8)
        glutSolidSphere(0.14, 8, 8)
        
        # Front foot
        glColor3f(0.1, 0.1, 0.1)   # Black shoes
        glRotatef(30, 1, 0, 0)     # Angle foot forward
        glScalef(1.0, 0.3, 2.0)
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
        
        # Back leg (properly attached to the body)
        glPushMatrix()
        glColor3f(0.1, 0.1, 0.5)  # Blue jeans
        
        # Upper back leg - thigh
        glTranslatef(0, 1.5, -0.3)  # Start from torso connection point
        glRotatef(120, 1, 0, 0)     # Angle backward and down
        gluCylinder(gluNewQuadric(), 0.15, 0.15, 0.7, 12, 1)
        
        # Knee joint
        glTranslatef(0, 0, 0.7)
        glutSolidSphere(0.16, 8, 8)
        
        # Lower back leg - calf
        glRotatef(-20, 1, 0, 0)     # Slight bend at knee
        gluCylinder(gluNewQuadric(), 0.15, 0.14, 0.8, 12, 1)
        
        # Ankle joint
        glTranslatef(0, 0, 0.8)
        glutSolidSphere(0.14, 8, 8)
        
        # Back foot
        glColor3f(0.1, 0.1, 0.1)    # Black shoes
        glRotatef(-10, 1, 0, 0)     # Angle foot slightly
        glScalef(1.0, 0.3, 2.0)
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
    else:
        # Non-player character or human without board (use original drawing)
        # Torso
        if lane == player_lane and include_board:
            glColor3f(0.2, 0.5, 0.8)  # Blue shirt for player
        else:
            glColor3f(random.uniform(0.2, 0.8), random.uniform(0.2, 0.8), random.uniform(0.2, 0.8))  # Random colors for NPCs
        
        glPushMatrix()
        glTranslatef(0, 2.0 if include_board else 1.0, 0)
        glScalef(0.8 if include_board else 0.6, 1.2, 0.5 if include_board else 0.4)
        glutSolidCube(1)
        glPopMatrix()
    
        # Head with better skin tone
        glColor3f(1.0, 0.8, 0.6)  # Skin tone
        glPushMatrix()
        glTranslatef(0, (3.1 if include_board else 2.3), 0)
        glutSolidSphere(0.4, 16, 16)
        glPopMatrix()
        
        # Hair
        glColor3f(0.1, 0.1, 0.1)  # Dark hair
        glPushMatrix()
        glTranslatef(0, (3.3 if include_board else 2.5), 0)
        glScalef(0.42, 0.2, 0.42)
        glutSolidSphere(1.0, 16, 16)
        glPopMatrix()
    
        # Arms with better joints
        for side in [-1, 1]:
            # Upper arm
            glPushMatrix()
            glColor3f(0.9, 0.8, 0.6)  # Skin tone
            glTranslatef((0.55 if include_board else 0.5) * side,
                         (2.5 if include_board else 2.0), 0)
            glRotatef(side * 20, 0, 0, 1)  # Slight angle for arms
            glRotatef(90, 1, 0, 0)
            gluCylinder(gluNewQuadric(), 0.1, 0.1,
                        (0.4 if include_board else 0.3), 12, 1)
                        
            # Elbow joint
            glutSolidSphere(0.11, 8, 8)
            
            # Lower arm
            glRotatef(side * -40, 1, 0, 0)
            gluCylinder(gluNewQuadric(), 0.1, 0.1,
                        (0.4 if include_board else 0.3), 12, 1)
            glPopMatrix()
    
        # Legs with better joints and details
        for side in [-0.3, 0.3]:
            # Upper leg
            glPushMatrix()
            # Pants color
            glColor3f(0.1, 0.1, 0.5)  # Blue jeans
            glTranslatef(side, (1.0 if include_board else 0.5), 0.1)
            glRotatef(-90, 1, 0, 0)
            gluCylinder(gluNewQuadric(), 0.15, 0.15,
                        (0.5 if include_board else 0.4), 12, 1)
                        
            # Knee joint
            glutSolidSphere(0.16, 8, 8)
            
            # Lower leg
            gluCylinder(gluNewQuadric(), 0.15, 0.15,
                        (0.5 if include_board else 0.4), 12, 1)
                        
            # Foot/shoe
            glColor3f(0.1, 0.1, 0.1)  # Black shoes
            glTranslatef(0, 0, 0.5)
            glScalef(1.0, 1.0, 1.5)
            glutSolidSphere(0.15, 8, 8)
            glPopMatrix()

    glPopMatrix()

def showScreen():
    """
    Display function to render the game scene:
    - Clears the screen and sets up the camera.
    - Draws everything of the screen
    """
    # Clear color and depth buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()  # Reset modelview matrix
    glViewport(0, 0, 1024, 600)  # Increased from 800 to 1024 for wider view

    setupCamera()  # Configure camera perspective

    draw_map()
    draw_obstacles()
    draw_humans()
    # added draw for lives
    draw_collect_lives()
    # Draw the main player on board
    draw_person(player_lane, 11, include_board=True)
    # Draw lives at the top left corner
    draw_lives()
    
    # Display game info text
    draw_text(10, 570, f"Lives: {player_life}", GLUT_BITMAP_HELVETICA_18)
    draw_text(700, 570, f"Distance: {distance_traveled:.1f}m", GLUT_BITMAP_HELVETICA_18)
    
    # If game is over, display game over screen
    if game_over_state:
        draw_game_over_screen()
    
    glutSwapBuffers()

def display_text(text, x, y, size=0.1):
    glColor3f(1.0, 0.0, 0.0)  # Set the text color to red
    glRasterPos2f(x, y)  # Set the position on the screen
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))  # Display the character

def game_over():
    global player_life, game_over_state
    print("Game Over!")
    game_over_state = True
    display_text("Game Over! Press 'R' to Restart", 300, 300, size=0.2)
    glutSwapBuffers()
    
def reset_game():
    global player_life, player_lane, jumping, jump_height, road_speed
    global obstacle_frequency_multiplier, obstacles, humans, collect_lives
    global game_time, tree_offset, lamp_offset, road_offset
    global distance_traveled, game_over_state
    global ducking  # Added ducking
    
    # Reset player state
    player_life = 5
    player_lane = 0
    jumping = False
    jump_height = 0.0
    ducking = False
    
    # Reset game progression
    road_speed = 0.3
    obstacle_frequency_multiplier = 2.0
    game_time = 0
    distance_traveled = 0.0
    game_over_state = False
    
    # Clear all objects from the game
    obstacles.clear()
    humans.clear()
    collect_lives.clear()
    
    # Reset movement offsets
    road_offset = 0.0
    tree_offset = 0.0
    lamp_offset = 0.0
    
    print("Game reset! New game started.")

def draw_map():
    # Draw sky with gradient effect
    draw_sky()
    
    # Ground/grassy areas on sides
    draw_ground()
    
    # Road
    glColor3f(*road_color)
    glBegin(GL_QUADS)
    glVertex3f(-6, 0, -100); glVertex3f( 6, 0, -100)
    glVertex3f( 6, 0,   20); glVertex3f(-6, 0,   20)
    glEnd()

    # Lane lines
    glLineWidth(2); glColor3f(1,1,1)
    for x in [-2,2]:
        glBegin(GL_LINES)
        glVertex3f(x,0.01,-100); glVertex3f(x,0.01,20)
        glEnd()

    # Moving stripes with better 3D effect
    glColor3f(1,1,1)
    pattern = stripe_length + stripe_spacing
    offset  = road_offset % pattern
    count   = int(120/pattern) + 2
    for i in range(count):
        z0 = -100 + i*pattern + offset
        glBegin(GL_QUADS)
        glVertex3f(-1.0,0.02,z0)
        glVertex3f( 1.0,0.02,z0)
        glVertex3f( 1.0,0.02,z0+stripe_length)
        glVertex3f(-1.0,0.02,z0+stripe_length)
        glEnd()
        
    # Draw roadside objects for better environment
    draw_roadside_objects()
    draw_environment_mountains()
    draw_clouds()

def draw_ground():
    """Draw grassy areas on the sides of the road"""
    # Left side grass
    glColor3f(*grass_color)
    glBegin(GL_QUADS)
    glVertex3f(-50, 0, -100)
    glVertex3f(-6, 0, -100)
    glVertex3f(-6, 0, 20)
    glVertex3f(-50, 0, 20)
    glEnd()
    
    # Right side grass4
    glBegin(GL_QUADS)
    glVertex3f(6, 0, -100)
    glVertex3f(50, 0, -100)
    glVertex3f(50, 0, 20)
    glVertex3f(6, 0, 20)
    glEnd()

def draw_obstacles():
    for obs in obstacles:
        if obs.get('type') == OBSTACLE_BIRD:
            draw_bird(obs['lane'], obs['z'], obs['height'])
        else:  # Default to car if type not specified
            draw_car(obs['lane'], obs['z'])

def draw_bird(lane, z, height):
    x = 4 * lane
    glPushMatrix()
    glTranslatef(x, height, z)
    
    # Bird body
    glColor3f(0.2, 0.2, 0.7)  # Blue bird
    glPushMatrix()
    glScalef(0.7, 0.5, 1.0)
    glutSolidSphere(0.7, 12, 12)
    glPopMatrix()
    
    # Bird head
    glPushMatrix()
    glTranslatef(0.0, 0.2, 0.7)
    glColor3f(0.2, 0.2, 0.9)
    glutSolidSphere(0.3, 10, 10)
    
    # Bird beak
    glColor3f(0.9, 0.5, 0.0)  # Orange beak
    glTranslatef(0.0, -0.1, 0.3)
    glRotatef(90, 1, 0, 0)
    glutSolidCone(0.15, 0.4, 8, 8)
    glPopMatrix()
    
    # Bird wings - animate flapping
    wingFlap = 20 * math.sin(glutGet(GLUT_ELAPSED_TIME) / 100)
    
    # Left wing
    glPushMatrix()
    glTranslatef(-0.6, 0.1, 0.0)
    glRotatef(wingFlap, 0, 0, 1)
    glColor3f(0.3, 0.3, 0.8)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(-1.0, 0.0, 0.3)
    glVertex3f(-0.8, 0.0, -0.3)
    glEnd()
    glPopMatrix()
    
    # Right wing
    glPushMatrix()
    glTranslatef(0.6, 0.1, 0.0)
    glRotatef(-wingFlap, 0, 0, 1)
    glColor3f(0.3, 0.3, 0.8)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, 0.0, 0.0)
    glVertex3f(1.0, 0.0, 0.3)
    glVertex3f(0.8, 0.0, -0.3)
    glEnd()
    glPopMatrix()
    
    # Tail
    glPushMatrix()
    glTranslatef(0.0, 0.0, -0.7)
    glRotatef(180, 0, 1, 0)
    glColor3f(0.2, 0.2, 0.7)
    glutSolidCone(0.3, 0.6, 8, 8)
    glPopMatrix()
    
    glPopMatrix()

def draw_car(lane, z):
    x = 4*lane
    glPushMatrix(); glTranslatef(x,0.25,z)
    # Body
    glColor3f(0.7,0.2,0.2)
    glPushMatrix(); glScalef(2.0,0.5,1.0); glutSolidCube(1); glPopMatrix()
    # Roof
    glColor3f(0.5,0.5,0.5)
    glPushMatrix(); glTranslatef(0,0.4,0); glScalef(1.2,0.3,0.6); glutSolidCube(1); glPopMatrix()
    # Wheels
    glColor3f(0.1,0.1,0.1)
    for wx in [-0.8,0.8]:
        for wz in [-0.4,0.4]:
            glPushMatrix()
            glTranslatef(wx,-0.15,wz)
            glRotatef(90,1,0,0)
            gluCylinder(gluNewQuadric(),0.2,0.2,0.2,12,1)
            glPopMatrix()
    glPopMatrix()

def draw_humans():
    for h in humans:
        draw_person(h['lane'], h['z'], include_board=False)

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

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text at the specified position using the specified font"""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glColor3f(1.0, 1.0, 1.0)  # White text
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_text_with_hearts(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text with heart symbols representing lives"""
    # First draw the text
    draw_text(x, y, text, font)
    
    # Then draw the hearts
    heart_spacing = 20
    heart_x = x + len(text) * 9  # Adjust spacing for text width
    
    for i in range(player_life):
        # Draw heart directly on screen coordinates
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, 800, 0, 600)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glColor3f(1.0, 0.0, 0.0)  # Red hearts
        
        # Draw a simple heart using GL_LINES
        heart_y = y - 5  # Align with text
        
        glBegin(GL_LINES)
        # Left curve
        glVertex2f(heart_x + i * heart_spacing, heart_y)
        glVertex2f(heart_x + i * heart_spacing - 4, heart_y + 4)
        glVertex2f(heart_x + i * heart_spacing - 4, heart_y + 4)
        glVertex2f(heart_x + i * heart_spacing - 2, heart_y + 8)
        glVertex2f(heart_x + i * heart_spacing - 2, heart_y + 8)
        glVertex2f(heart_x + i * heart_spacing, heart_y + 4)
        
        # Right curve
        glVertex2f(heart_x + i * heart_spacing, heart_y)
        glVertex2f(heart_x + i * heart_spacing + 4, heart_y + 4)
        glVertex2f(heart_x + i * heart_spacing + 4, heart_y + 4)
        glVertex2f(heart_x + i * heart_spacing + 2, heart_y + 8)
        glVertex2f(heart_x + i * heart_spacing + 2, heart_y + 8)
        glVertex2f(heart_x + i * heart_spacing, heart_y + 4)
        glEnd()
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def reshape(w,h):
    glViewport(0,0,w,h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, w/h if h else 1, 1.0, 200.0)
    glMatrixMode(GL_MODELVIEW)

# Fix obstacle glitches in the update function
def update():
    global jumping, jump_height, ducking, road_offset, obstacles, humans, player_life
    global collect_lives, tree_offset, lamp_offset, road_speed, game_time
    global obstacle_frequency_multiplier, distance_traveled, game_over_state

    now = glutGet(GLUT_ELAPSED_TIME)

    if game_over_state:
        glutPostRedisplay()
        return

    if jumping:
        elapsed = now - jump_start
        t = elapsed / jump_duration
        if t >= 1.0:
            jumping = False; jump_height = 0.0
        else:
            jump_height = jump_height_max * math.sin(math.pi * t)

    if ducking:
        elapsed = now - duck_start
        if elapsed >= duck_duration:
            ducking = False

    road_offset += road_speed
    tree_offset = road_offset
    lamp_offset = road_offset

    for obs in obstacles[:]:
        obs['z'] += road_speed
        if obs['z'] > 20:
            obstacles.remove(obs)

    for h in humans[:]:
        h['z'] += road_speed
        if h['z'] > 20:
            humans.remove(h)

    for l in collect_lives[:]:
        l['z'] += road_speed
        if l['z'] > 20:
            collect_lives.remove(l)

    if random.random() < 0.005 * obstacle_frequency_multiplier:
        obstacles.append({'lane': random.choice([-1, 0, 1]), 'z': -100.0, 'type': OBSTACLE_CAR})

    if random.random() < 0.004 * obstacle_frequency_multiplier:
        obstacles.append({'lane': random.choice([-1, 0, 1]), 'z': -100.0, 'type': OBSTACLE_BIRD, 'height': 2.5})

    if random.random() < 0.003 * obstacle_frequency_multiplier:
        humans.append({'lane': random.choice([-1, 0, 1]), 'z': -100.0})

    if random.random() < 0.0005 * obstacle_frequency_multiplier:
        collect_lives.append({'lane': random.choice([-1, 0, 1]), 'z': -100.0})

    game_time += 16.6
    if game_time >= speed_increase_interval:
        game_time = 0
        if road_speed < max_road_speed:
            road_speed += 0.05
        obstacle_frequency_multiplier += 0.2

    if not game_over_state:
        distance_traveled += road_speed * 0.0166

    check_collision()
    glutPostRedisplay()

# Modify keyboardListener to prevent camera movement when pressing 'A' or 'D'
def keyboardListener(key, x, y):
    global player_lane, jumping, jump_start, ducking, duck_start, game_over_state

    if game_over_state:
        if key == b'r':
            reset_game()
            return

    if key == b'a' and player_lane > -1: 
        player_lane -= 1
    elif key == b'd' and player_lane < 1: 
        player_lane += 1
    elif key == b' ' and not jumping:
        jumping = True
        jump_start = glutGet(GLUT_ELAPSED_TIME)
    elif key == b's' and not ducking and not jumping:  # Add ducking with 's' key
        ducking = True
        duck_start = glutGet(GLUT_ELAPSED_TIME)
    elif key == b'q': 
        sys.exit()

def reset_player():
    global player_lane, jumping, jump_height
    player_lane = 0; jumping=False; jump_height=0.0

# Update camera position for orbit mode
def updateOrbitCamera():
    global camera_pos
    x, y, z = camera_target

    # Convert spherical coordinates to Cartesian coordinates
    cam_x = x + camera_distance * math.cos(math.radians(camera_height_angle)) * math.sin(math.radians(camera_orbit_angle))
    cam_y = y + camera_distance * math.sin(math.radians(camera_height_angle))
    cam_z = z + camera_distance * math.cos(math.radians(camera_height_angle)) * math.cos(math.radians(camera_orbit_angle))

    camera_pos = (cam_x, cam_y, cam_z)

# Modify setupCamera to handle orbit mode
def setupCamera():
    """Configure camera and perspective based on current mode"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1024/600, 0.1, 200.0)  # Adjusted for wider viewport
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == "orbit":
        updateOrbitCamera()

    # Adjust camera target to follow player in x-axis (lane position)
    target_x = 4 * player_lane
    camera_target = (target_x, 2, 0)  # Update target to follow player's lane

    x, y, z = camera_pos
    target_x, target_y, target_z = camera_target

    # Ensure camera is centered on player's position
    gluLookAt(target_x + (x - target_x), y, z,  # Camera position offset from target
              target_x, target_y, target_z,  # Look-at target follows player
              0, 1, 0)                       # Up vector (y-axis)

def draw_sky():
    """Draw a gradient sky background"""
    if sunset_mode:
        # Sunset colors
        color_top = (0.1, 0.1, 0.4)  # Dark blue at top
        color_horizon = (0.9, 0.6, 0.3)  # Orange at horizon
    else:
        # Day colors
        color_top = (0.3, 0.6, 0.9)  # Blue at top
        color_horizon = (0.7, 0.8, 1.0)  # Light blue at horizon
    
    glPushMatrix()
    glLoadIdentity()
    # Draw sky as a large vertical quad with gradient
    glBegin(GL_QUADS)
    # Top vertices with darker blue
    glColor3f(*color_top)
    glVertex3f(-200, 100, -100)
    glVertex3f(200, 100, -100)
    
    # Bottom vertices with lighter blue (horizon)
    glColor3f(*color_horizon)
    glVertex3f(200, 0, -100)
    glVertex3f(-200, 0, -100)
    glEnd()
    glPopMatrix()

def draw_roadside_objects():
    """Draw objects along the sides of the road for better visual appeal"""
    # Draw trees on both sides - with tree_offset for movement
    for side in [-1, 1]:
        for base_z in range(-90, 10, 20):  # Trees spaced every 20 units
            # Apply movement offset to z position
            z = base_z + (tree_offset % 20)
            x_pos = side * 10  # Position away from the road
            draw_tree(x_pos, z)
    
    # Draw lamp posts - with lamp_offset for movement
    for side in [-1, 1]:
        for base_z in range(-80, 10, 40):  # Lamp posts spaced every 40 units
            # Apply movement offset to z position
            z = base_z + (lamp_offset % 40)
            x_pos = side * 7  # Position closer to the road than trees
            draw_lamp_post(x_pos, z)

def draw_tree(x, z):
    """Draw a simple tree with trunk and foliage"""
    glPushMatrix()
    glTranslatef(x, 0, z)
    
    # Trunk
    glColor3f(0.55, 0.27, 0.07)  # Brown
    glPushMatrix()
    glTranslatef(0, 1.5, 0)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 0.5, 0.3, 3, 8, 1)
    glPopMatrix()
    
    # Foliage (layered cones for more realistic look)
    glColor3f(0.1, 0.5, 0.1)  # Dark green
    for y_offset in [3, 4.5, 6]:
        glPushMatrix()
        glTranslatef(0, y_offset, 0)
        glRotatef(-90, 1, 0, 0)
        glutSolidCone(2.0 - (y_offset-3)*0.4, 2.0, 10, 5)
        glPopMatrix()
    
    glPopMatrix()

def draw_lamp_post(x, z):
    """Draw a lamp post with a light source on top"""
    glPushMatrix()
    glTranslatef(x, 0, z)
    
    # Post
    glColor3f(0.3, 0.3, 0.3)  # Dark gray for post
    glPushMatrix()
    glTranslatef(0, 2.5, 0)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(gluNewQuadric(), 0.2, 0.2, 5, 8, 1)
    glPopMatrix()
    
    # Lamp arm
    glPushMatrix()
    glTranslatef(0, 5, 0)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.3, 0.3, 0.3)
    gluCylinder(gluNewQuadric(), 0.1, 0.1, 1.5, 8, 1)
    glPopMatrix()
    
    # Lamp globe
    glPushMatrix()
    glTranslatef(1.5, 5, 0)
    if sunset_mode:
        glColor3f(1.0, 0.9, 0.5)  # Warm yellow light
    else:
        glColor3f(1.0, 1.0, 0.8)  # White-ish light
    glutSolidSphere(0.4, 12, 12)
    glPopMatrix()
    
    glPopMatrix()

def draw_environment_mountains():
    """Draw distant mountains to create a more immersive 3D environment"""
    # Left side mountains
    for i in range(5):
        x_offset = -80 + i * 30
        z_offset = -120
        height = 25 + random.randint(0, 10)  # Varied mountain heights
        width = 35 + random.randint(-5, 5)   # Varied mountain widths
        
        # Draw mountain using triangle fan
        glColor3f(0.5, 0.5, 0.6)  # Gray color for mountains
        glPushMatrix()
        glTranslatef(x_offset, 0, z_offset)
        
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, height, 0)  # Peak
        for angle in range(0, 361, 30):
            rad = math.radians(angle)
            glVertex3f(width * math.cos(rad), 0, width * math.sin(rad))
        glEnd()
        glPopMatrix()
    
    # Right side mountains
    for i in range(5):
        x_offset = 80 - i * 30
        z_offset = -120
        height = 25 + random.randint(0, 10)  # Varied mountain heights
        width = 35 + random.randint(-5, 5)   # Varied mountain widths
        
        # Draw mountain using triangle fan
        glColor3f(0.5, 0.5, 0.6)  # Gray color for mountains
        glPushMatrix()
        glTranslatef(x_offset, 0, z_offset)
        
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, height, 0)  # Peak
        for angle in range(0, 361, 30):
            rad = math.radians(angle)
            glVertex3f(width * math.cos(rad), 0, width * math.sin(rad))
        glEnd()
        glPopMatrix()

def draw_clouds():
    """Draw 3D clouds in the sky"""
    # Use the current time for slow cloud movement
    cloud_offset = glutGet(GLUT_ELAPSED_TIME) / 20000.0
    
    # Define cloud positions
    cloud_positions = [
        (-60, 40, -90),
        (-30, 50, -100),
        (0, 55, -110),
        (40, 45, -95),
        (70, 60, -105)
    ]
    
    for x, y, z in cloud_positions:
        # Apply slow movement to x position
        x_pos = x + (cloud_offset * 20) % 200 - 100
        
        glPushMatrix()
        glTranslatef(x_pos, y, z)
        
        # Cloud color
        glColor3f(1.0, 1.0, 1.0)  # White
        
        # Cloud composed of several spheres
        sphere_positions = [
            (0, 0, 0, 8),     # Center sphere
            (6, 2, 3, 6),     # Surrounding spheres
            (-5, 1, 4, 7),
            (7, -1, -2, 5),
            (-7, 0, -3, 6),
            (0, 3, 6, 5),
            (-3, -2, -5, 6)
        ]
        
        for sx, sy, sz, radius in sphere_positions:
            glPushMatrix()
            glTranslatef(sx, sy, sz)
            glutSolidSphere(radius, 8, 8)  # Less detail for better performance
            glPopMatrix()
            
        glPopMatrix()

# Add key controls for orbit camera
def specialKeyListener(key, x, y):
    global camera_orbit_angle, camera_height_angle, camera_distance

    if camera_mode == "orbit":
        if key == GLUT_KEY_LEFT:
            camera_orbit_angle -= 5
        elif key == GLUT_KEY_RIGHT:
            camera_orbit_angle += 5
        elif key == GLUT_KEY_UP:
            camera_height_angle = min(camera_height_angle + 5, 89)  # Limit vertical angle
        elif key == GLUT_KEY_DOWN:
            camera_height_angle = max(camera_height_angle - 5, -89)

    # Handle regular keyboard controls for zooming instead of in specialKeyListener
    # Don't call originalKeyListener as it doesn't exist

# Update draw_game_over_screen to display restart text and distance traveled
def draw_game_over_screen():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glColor4f(0.0, 0.0, 0.0, 0.7)
    glBegin(GL_QUADS)
    glVertex2f(200, 150)
    glVertex2f(600, 150)
    glVertex2f(600, 450)
    glVertex2f(200, 450)
    glEnd()

    glColor3f(1.0, 0.0, 0.0)
    draw_text(320, 380, "GAME OVER", GLUT_BITMAP_TIMES_ROMAN_24)

    glColor3f(1.0, 1.0, 1.0)
    draw_text(280, 300, f"Distance Traveled: {distance_traveled:.1f}m", GLUT_BITMAP_HELVETICA_18)

    glColor3f(1.0, 1.0, 0.0)
    draw_text(300, 220, "Press 'R' to Restart", GLUT_BITMAP_HELVETICA_18)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_text_with_hearts(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw text with heart symbols representing lives"""
    glColor3f(1.0, 1.0, 1.0)  # White text
    glRasterPos2f(x, y)
    
    # Draw the text
    for character in text:
        glutBitmapCharacter(font, ord(character))
    
    # Draw hearts for lives
    heart_spacing = 20
    heart_x = x + len(text) * 8
    
    for i in range(player_life):
        draw_heart(heart_x + i * heart_spacing, y)

def play_sound(sound_name):
    """
    Play a sound effect
    This is a stub function that would be implemented with a proper sound library
    For now, it just prints which sound would be played
    """
    try:
        # Here you would implement actual sound playing with a library like pygame.mixer
        # For now, we'll just print the sound name to prevent crashes
        print(f"Playing sound: {sound_name}")
    except Exception as e:
        print(f"Error playing sound {sound_name}: {e}")
        # Don't let sound errors crash the game

def draw_scene():
    global road_offset, obstacle_spawn_time, obstacle_count, life_spawn_time, powerup_spawn_time
    global shield_remaining, gun_remaining, current_time, pause_start_time
    
    current_time = glutGet(GLUT_ELAPSED_TIME)
    
    if game_over_state or pause_state:
        # Don't update game state when game is over or paused
        if pause_state and pause_start_time == 0:
            pause_start_time = current_time
    else:
        # Reset pause time tracking
        if pause_start_time > 0:
            # Adjust all timing-related variables by the pause duration
            pause_duration = current_time - pause_start_time
            obstacle_spawn_time += pause_duration
            life_spawn_time += pause_duration
            powerup_spawn_time += pause_duration
            if enable_powerups:
                if active_shield:
                    shield_start += pause_duration
                if active_gun:
                    gun_start += pause_duration
            pause_start_time = 0
            
        # Update road offset for animation
        road_offset += game_speed
        if road_offset >= strip_spacing:
            road_offset = 0
        
        # Spawn new obstacles
        if current_time - obstacle_spawn_time > next_obstacle_delay:
            spawn_obstacle()
            obstacle_spawn_time = current_time
            # Randomize next obstacle delay
            next_obstacle_delay = 1500 + random.randint(-500, 1000)
            
        # Spawn new lives occasionally
        if current_time - life_spawn_time > 10000:  # Every 10 seconds
            spawn_collectible_life()
            life_spawn_time = current_time
            
        # Spawn new powerups occasionally if enabled
        if enable_powerups and current_time - powerup_spawn_time > 15000:  # Every 15 seconds
            spawn_powerup()
            powerup_spawn_time = current_time
            
        # Update shield remaining time - only if powerups are enabled
        if enable_powerups and active_shield:
            shield_elapsed = current_time - shield_start
            shield_remaining = max(0, 1.0 - (shield_elapsed / SHIELD_DURATION))
            if shield_elapsed >= SHIELD_DURATION:
                active_shield = False
        
        # Update gun remaining time - only if powerups are enabled
        if enable_powerups and active_gun:
            gun_elapsed = current_time - gun_start
            gun_remaining = max(0, 1.0 - (gun_elapsed / GUN_DURATION))
            if gun_elapsed >= GUN_DURATION:
                active_gun = False
                
        # Update obstacles
        update_obstacles()
        
    # Clear the screen and depth buffer
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # Reset transformations
    glLoadIdentity()
    
    # Set up camera based on the current camera mode
    setup_camera()
    
    # Draw skybox first
    draw_skybox()
    
    # Draw the road
    draw_road()
    
    # Draw obstacles
    for obs in obstacles:
        draw_obstacle(obs)
    
    # Draw collectible lives
    for life in collect_lives:
        draw_collectible_life(life)
        
    # Draw powerups if enabled
    if enable_powerups:
        for p in powerups:
            draw_powerup(p)
    
    # Draw environment decorations (trees, etc.)
    draw_environment()
    
    # Draw the player
    draw_player()
    
    # Draw HUD (lives, score, etc.)
    draw_hud()
    
    # Display either game over, pause menu, or proceed
    if game_over_state:
        draw_game_over()
    elif pause_state:
        draw_pause_menu()
        
    # Swap buffers
    glutSwapBuffers()

def check_collisions():
    global player_lives, game_speed, score, active_shield, active_gun, shield_start, gun_start
    global game_over_state, score_multiplier, jump_state, duck_state
    
    player_z = -20  # Player's Z position
    player_hitbox_x = 1.0  # Player's X hitbox size
    
    # Adjust player's hitbox based on jump/duck state
    if jump_state:
        player_hitbox_y = 1.0
        player_y_offset = player_jump_height
    elif duck_state:
        player_hitbox_y = 0.5  # Smaller when ducking
        player_y_offset = 0.5  # Lower when ducking
    else:
        player_hitbox_y = 1.0
        player_y_offset = 1.0
    
    # 1. Check obstacle collisions
    for obs in obstacles[:]:
        if abs(obs['z'] - player_z) < 3:  # Close enough on Z axis
            # Check X axis collision
            if abs(obs['x'] - lane_positions[player_lane]) < player_hitbox_x + 1.0:
                # Check Y axis collision
                if obs['type'] == 'car':
                    # For cars, check if player jumped over
                    if not jump_state or player_jump_height < 1.5:
                        if not active_shield:  # Shield protects from collision
                            player_lives -= 1
                            if player_lives <= 0:
                                game_over_state = True
                        obstacles.remove(obs)
                        play_sound('crash')
                elif obs['type'] == 'bird':
                    # For birds, check if player ducked under
                    if not duck_state:
                        if not active_shield:  # Shield protects from collision
                            player_lives -= 1
                            if player_lives <= 0:
                                game_over_state = True
                        obstacles.remove(obs)
                        play_sound('crash')
                        
    # 2. Check collectible life collisions
    for life in collect_lives[:]:
        if abs(life['z'] - player_z) < 3:  # Close enough on Z axis
            # Check X axis collision
            if abs(life['x'] - lane_positions[player_lane]) < player_hitbox_x + 0.5:
                # Collect the life
                player_lives = min(player_lives + 1, MAX_LIVES)
                collect_lives.remove(life)
                play_sound('collect')
                
    # 3. Check powerup collisions (only if enabled)
    if enable_powerups:
        for p in powerups[:]:
            if abs(p['z'] - player_z) < 3:  # Close enough on Z axis
                # Check X axis collision
                if abs(p['x'] - lane_positions[player_lane]) < player_hitbox_x + 0.5:
                    # Collect the powerup
                    if p['type'] == 'shield':
                        active_shield = True
                        shield_start = glutGet(GLUT_ELAPSED_TIME)
                    elif p['type'] == 'gun':
                        active_gun = True
                        gun_start = glutGet(GLUT_ELAPSED_TIME)
                    elif p['type'] == 'speed':
                        game_speed *= 0.8  # Slow down the game
                    elif p['type'] == 'score':
                        score_multiplier = 2
                    
                    powerups.remove(p)
                    play_sound('powerup')

def update_powerups():
    global active_shield, active_gun, shield_start, gun_start, score_multiplier, powerups
    
    # Only process powerups if they're enabled
    if not enable_powerups:
        # Reset any active powerups if they were somehow activated
        active_shield = False
        active_gun = False
        score_multiplier = 1
        powerups.clear()  # Clear any powerups in the world
        return
        
    current_time = glutGet(GLUT_ELAPSED_TIME)
    
    # Update active powerups
    if active_shield:
        # Shield lasts for 10 seconds
        if current_time - shield_start > 10000:
            active_shield = False
    
    if active_gun:
        # Gun lasts for 15 seconds
        if current_time - gun_start > 15000:
            active_gun = False
            
    # Spawn new powerups occasionally
    if random.random() < 0.001 * game_speed:
        powerup_type = random.choice(['shield', 'gun', 'speed', 'score'])
        lane = random.randint(0, 2)
        powerups.append({
            'type': powerup_type,
            'x': lane_positions[lane],
            'z': -150 - random.randint(0, 50),
            'rotation': random.randint(0, 360)
        })

def handle_key(key, x, y):
    global left_press, right_press, player_x, camera_y, camera_z, top_view, first_person
    global game_over_state, obstacles, start_screen, pause_state, enable_powerups
    global life_loss_time, player_flicker, player_lives, total_distance, score
    global bullets, gun_start, active_gun, shield_start, active_shield, powerups
    
    # ESC key - exit game
    if key == b'\x1b':
        sys.exit(0)
    
    # Player movement keys
    if game_over_state == False and pause_state == False and start_screen == False:
        if key == b'a' or key == b'A':
            left_press = True
        elif key == b'd' or key == b'D':
            right_press = True
            
        # Spacebar to shoot if gun powerup is active
        elif (key == b' ') and enable_powerups and active_gun:
            # Create a new bullet at player position
            new_bullet = {'x': player_x, 'z': -4.0}
            bullets.append(new_bullet)
            
    # Game state control keys
    if key == b'r' or key == b'R':  # Restart game
        if game_over_state or pause_state or start_screen:
            reset_game()
            
    elif key == b'p' or key == b'P':  # Pause game
        if start_screen == False and game_over_state == False:
            pause_state = not pause_state
            
    elif key == b's' or key == b'S':  # Start game from start screen
        if start_screen:
            start_screen = False
            
    elif key == b'v' or key == b'V':  # Toggle view
        if top_view:
            top_view = False
            first_person = True
            camera_y = 0.5
            camera_z = -4.0
        elif first_person:
            top_view = False
            first_person = False
            camera_y = 1.5
            camera_z = -6.0
        else:
            top_view = True
            first_person = False
            camera_y = 12.0
            camera_z = -12.0
            
    elif key == b'w' or key == b'W':  # Toggle powerups
        enable_powerups = not enable_powerups
        # Clear active powerups when disabled
        if not enable_powerups:
            active_shield = False
            active_gun = False
            bullets.clear()
            powerups.clear()

def main():
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(800,600)
    glutCreateWindow(b"3D Skate Game with Sparse Spawns")
    init()
    glutDisplayFunc(showScreen)
    glutReshapeFunc(reshape)
    glutIdleFunc(update)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMainLoop()

if __name__=="__main__":
    main()