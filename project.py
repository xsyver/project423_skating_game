from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random


# --- Player control states ---
player_lane     = 0      # -1 = left, 0 = middle, 1 = right
player_y        = 0.5    # Base Y position
jumping         = False  # In jump arc?
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
road_speed     = 0.03    # Speed of road movement
stripe_length  = 5.0     # Length of each stripe along Z
stripe_spacing = 15.0    # Gap between stripes


# --- Obstacle (car) states ---
obstacles      = []      # List of {'lane', 'z'}

# --- Human (NPC) states ---
humans         = []      # List of {'lane', 'z'}

# --- Collect Lives ---
collect_lives  = []      # List of {'lane', 'z'}

def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.8, 0.9, 1.0)  # Light blue sky

# def draw_lives():
#     glColor3f(1, 0, 0)  # Red color for lives
#     glRasterPos2f(-12, 10)
#     for digit in str(player_life):
#         glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(digit))
def draw_lives():
    glColor3f(1, 0, 0)  # Red color
    for i in range(player_life):
        x = -5.5 + i * 1.0  # spacing between icons
        y = 4.5
        draw_heart(x, y)

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
    now = glutGet(GLUT_ELAPSED_TIME)
    for obs in humans:
        # Only check if in the same lane and close in Z
        if player_lane == obs['lane'] and abs(obs['z'] - 11) < 1.0:
            height = obs.get('height', 1.0)  # fallback to 1.0 if height missing

            # Skip collision if jumping over obstacle
            if jumping and jump_height > height:
                continue

            # Only reduce life if not on cooldown
            if now - hit_cooldown > hit_cooldown_max:
                player_life -= 1
                hit_cooldown = now
                print(f"Hit! Lives left: {player_life}")
                if player_life <= 0:
                    game_over()

    for obs in obstacles:
        # Only check if in the same lane and close in Z
        if player_lane == obs['lane'] and abs(obs['z'] - 11) < 1.0:
            height = obs.get('height', 1.0)  # fallback to 1.0 if height missing

            # Skip collision if jumping over obstacle
            if jumping and jump_height > height:
                continue

            # Only reduce life if not on cooldown
            if now - hit_cooldown > hit_cooldown_max:
                player_life -= 1
                hit_cooldown = now
                print(f"Hit! Lives left: {player_life}")
                if player_life <= 0:
                    game_over()
    # collision detection for lives adds life upto 5
    for obs in collect_lives:
        # Only check if in the same lane and close in Z
        if player_lane == obs['lane'] and abs(obs['z'] - 11) < 1.0:
            height = obs.get('height', 1.0)  # fallback to 1.0 if height missing

            # Skip collision if jumping over life (your loss)
            if jumping and jump_height > height:
                continue

            # Only add life if not on cooldown
            if now - life_hit_cooldown > life_hit_cooldown_max:
                if player_life < 5:
                    player_life += 1
                    print(f"Collected life! Lives left: {player_life}")
                life_hit_cooldown = now
                if player_life <= 0:
                    game_over()


# Unified person‑drawing
def draw_person(lane, z_pos, include_board=True):
    x = 4 * lane
    glPushMatrix()
    # Position Y based on board or floor
    y_off = player_y + jump_height if (include_board and lane == player_lane) else 0.0
    glTranslatef(x, y_off, z_pos)

    # Skateboard (optional)
    if include_board:
        glColor3f(0.1, 0.1, 0.6)
        glPushMatrix()
        glScalef(2.5, 0.05, 0.8)
        glutSolidCube(2)
        glPopMatrix()
        glColor3f(0.2, 0.2, 0.2)
        for wx in [-2.0, 2.0]:
            for wz in [-0.8, 0.8]:
                glPushMatrix()
                glTranslatef(wx, -0.6, wz)
                glRotatef(90, 0, 1, 0)
                gluCylinder(gluNewQuadric(), 0.3, 0.3, 0.5, 12, 1)
                glPopMatrix()

    # Torso
    glColor3f(0.2, 0.5, 0.8)
    glPushMatrix()
    glTranslatef(0, 2.0 if include_board else 1.0, 0)
    glScalef(0.8 if include_board else 0.6, 1.2, 0.5 if include_board else 0.4)
    glutSolidCube(1)
    glPopMatrix()

    # Head
    glColor3f(1.0, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(0, (3.1 if include_board else 2.3), 0)
    glutSolidSphere(0.4, 16, 16)
    glPopMatrix()

    # Arms
    for side in [-1, 1]:
        glPushMatrix()
        glColor3f(0.9, 0.8, 0.6)
        glTranslatef((0.55 if include_board else 0.5) * side,
                     (2.5 if include_board else 2.0), 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1,
                    (0.8 if include_board else 0.6), 12, 1)
        glPopMatrix()

    # Legs
    for side in [-0.3, 0.3]:
        glPushMatrix()
        glColor3f(0.9, 0.8, 0.6)
        glTranslatef(side, (1.0 if include_board else 0.5), 0.1)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1,
                    (1.0 if include_board else 0.8), 12, 1)
        glPopMatrix()

    glPopMatrix()

def draw():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(0, 10, 20,  0, 0, 0,  0, 1, 0)

    draw_map()
    draw_obstacles()
    draw_humans()
    # added draw for lives
    draw_collect_lives()
    # Draw the main player on board
    draw_person(player_lane, 11, include_board=True)
    draw_lives()
    
    glutSwapBuffers()
def display_text(text, x, y, size=0.1):
    glColor3f(1.0, 0.0, 0.0)  # Set the text color to red
    glRasterPos2f(x, y)  # Set the position on the screen
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))  # Display the character

def game_over():
    global player_life
    print("Game Over!")
    
    
    glutLeaveMainLoop()  #
    
def reset_game():
    global player_life
    player_life = 5 
def draw_map():
    # Road
    glColor3f(0.1, 0.1, 0.1)
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

    # Moving stripes
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

def draw_obstacles():
    for obs in obstacles:
        draw_car(obs['lane'], obs['z'])

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

def reshape(w,h):
    glViewport(0,0,w,h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, w/h if h else 1, 1.0, 200.0)
    glMatrixMode(GL_MODELVIEW)

def update():
    global jumping, jump_height, road_offset, obstacles, humans, player_life, collect_lives
    now = glutGet(GLUT_ELAPSED_TIME)
    # Jump
    if jumping:
        elapsed = now - jump_start
        t = elapsed / jump_duration
        if t >= 1.0:
            jumping = False; jump_height = 0.0
        else:
            jump_height = jump_height_max * math.sin(math.pi * t)

    # Road animate
    road_offset += road_speed

    # Move obstacles
    for obs in obstacles[:]:
        obs['z'] += road_speed
        if obs['z'] > 20: obstacles.remove(obs)

    # Move humans
    for h in humans[:]:
        h['z'] += road_speed
        if h['z'] > 20: humans.remove(h)

    # Remove lives after getting out of display
    for l in collect_lives[:]:
        l['z'] += road_speed
        if l['z'] > 20: collect_lives.remove(l)

    # Lower spawn rates
    if random.random() < 0.002:  # fewer cars
        obstacles.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
    if random.random() < 0.001:  # fewer humans
        humans.append({'lane': random.choice([-1,0,1]), 'z': -100.0})
    if random.random() < 0.0005:  # fewer collect_lives
        collect_lives.append({'lane': random.choice([-1,0,1]), 'z': -100.0})

    check_collision()
    glutPostRedisplay()

def keyboard(key,x,y):
    global player_lane, jumping, jump_start
    k = key.decode('utf-8')
    if k=='a' and player_lane> -1: player_lane-=1
    elif k=='d' and player_lane< 1: player_lane+=1
    elif k==' ' and not jumping:
        jumping=True; jump_start = glutGet(GLUT_ELAPSED_TIME)
    elif k=='r': reset_player()
    elif k=='q': sys.exit()

def reset_player():
    global player_lane, jumping, jump_height
    player_lane = 0; jumping=False; jump_height=0.0

def main():
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(800,600)
    glutCreateWindow(b"3D Skate Game with Sparse Spawns")
    init()
    glutDisplayFunc(draw)
    glutReshapeFunc(reshape)
    glutIdleFunc(update)
    glutKeyboardFunc(keyboard)
    glutMainLoop()

if __name__=="__main__":
    main()
