import pygame
import os
import csv
import random

pygame.init()
pygame.mixer.init()

# Constants
WIDTH, HEIGHT = 540, 540
CELL_SIZE = WIDTH // 9
BG_COLOR = (211, 176, 227)
#MENU_COLOR = (173, 216, 230) # Light blue, keep this for now??
MENU_COLOR = (211, 176, 227) # Light purple
CELL_COLOR = (255, 255, 255) # White
GRID_COLOR = (0, 0, 0) # Black
SELECTED_COLOR = (0, 0, 255) # Blue
CONFLICT_COLOR = (255, 0, 0) # Red
FIXED_NUM_COLOR = (105, 167, 225) # Its like a light bluey thing
USER_NUM_COLOR = (60, 60, 60) # Dark Grey
TITLE_COLOR = (255, 255, 255) # White
TEXT_COLOR = (255, 255, 255) # White

# Game state stuff
START_SCREEN = 0
GAME_SCREEN = 1
WIN_SCREEN = 2
current_state = START_SCREEN

# Languages
languages = [
    {'code': 'zh', 'name': '中文'},
    {'code': 'jp', 'name': '日本語'},
    {'code': 'de', 'name': 'Deutsch'},
    {'code': 'ko', 'name': '한국어'},
    {'code': 'none', 'name': 'No Audio'}
]
selected_lang = 0

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sudoku")

# Fonts shit - Should work universally ? Idk, works on my machine!
CJK_FONT_PATH = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
title_font = pygame.font.Font(None, 80)
win_font = pygame.font.Font(None, 100)
menu_font = pygame.font.Font(None, 36)
number_font = pygame.font.Font(None, 40)

try:
    cjk_font = pygame.font.Font(CJK_FONT_PATH, 48)
    #print(f"Successfully loaded CJK font: {CJK_FONT_PATH}")
except pygame.error as e:
    print(f"Warning: Could not load CJK font from {CJK_FONT_PATH}: {e}")
    print("Language names might not render correctly. Using default font.")
    cjk_font = pygame.font.Font(None, 48)

# Sudoku game state shit
sample_board = [[0 for _ in range(9)] for _ in range(9)]
editable = [[True for _ in range(9)] for _ in range(9)]
selected_row, selected_col = 0, 0
sounds = []
conflict_cells = set()

need_redraw = True
win_surface_cached = None

# Key mappings
keys = {
    pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
    pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6,
    pygame.K_7: 7, pygame.K_8: 8, pygame.K_9: 9,
    pygame.K_KP1: 1, pygame.K_KP2: 2, pygame.K_KP3: 3,
    pygame.K_KP4: 4, pygame.K_KP5: 5, pygame.K_KP6: 6,
    pygame.K_KP7: 7, pygame.K_KP8: 8, pygame.K_KP9: 9
}

# Sudoku Generation Logic
def is_valid(grid, row, col, num): # Checks if a number can be placed at any given position (during generation)
    for x in range(9):
        if grid[row][x] == num or grid[x][col] == num:
            return False
    start_row, start_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(3):
        for j in range(3):
            if grid[start_row + i][start_col + j] == num:
                return False
    return True

def find_empty(grid): # To find the next empty cell (0) in the grid
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                return (r, c)
    return None

def fill_grid(grid): # Recursively fill the grid w/ backtracking shit
    find = find_empty(grid)
    if not find:
        return True
    else:
        row, col = find

    nums = list(range(1, 10))
    random.shuffle(nums)

    for num in nums:
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if fill_grid(grid):
                return True
            grid[row][col] = 0
    return False

def solve_sudoku(grid): # This function solves them to make sure there is only one possible solution - AFAIK it is working better now!!
    find = find_empty(grid)
    if not find:
        return 1 # Found one solution

    row, col = find
    solutions_count = 0

    for num in range(1, 10):
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            solutions_count += solve_sudoku(grid)
            grid[row][col] = 0 # Backtrack

            if solutions_count > 1: # If we find more than one solution, no need to continue
                break
    return solutions_count

def generate_sudoku(cells_to_remove=45): # Poops out a new puzzle
    grid = [[0 for _ in range(9)] for _ in range(9)]
    fill_grid(grid) # New solved grid!

    # Create a list of all cell coordinates
    all_cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(all_cells)

    puzzle = [row[:] for row in grid]
    removed_count = 0
    
    for r, c in all_cells:
        if removed_count >= cells_to_remove:
            break

        original_value = puzzle[r][c]
        puzzle[r][c] = 0

        temp_grid = [row[:] for row in puzzle]
        
        # Check for if it still has a unique solution after removal of numbers
        if solve_sudoku(temp_grid) == 1:
            removed_count += 1
        else:
            puzzle[r][c] = original_value # If not unique, put the number back lol
            
    #print(f"Generated a new puzzle, removed {removed_count} cells.")
    return puzzle


# Gameplay Logic

def find_conflicts(grid): # Finds all cells that break the RULES!
    conflicts = set()
    for i in range(9):
        row_counts = {}
        for j in range(9):
            num = grid[i][j]
            if num != 0: row_counts.setdefault(num, []).append((i, j))
        for num, coords in row_counts.items():
            if len(coords) > 1: conflicts.update(coords)

        col_counts = {}
        for j in range(9):
            num = grid[j][i]
            if num != 0: col_counts.setdefault(num, []).append((j, i))
        for num, coords in col_counts.items():
            if len(coords) > 1: conflicts.update(coords)


    for box_row in range(3):
        for box_col in range(3):
            box_counts = {}
            for i in range(3):
                for j in range(3):
                    row, col = box_row * 3 + i, box_col * 3 + j
                    num = grid[row][col]
                    if num != 0:
                        box_counts.setdefault(num, []).append((row, col))
            for num, coords in box_counts.items():
                if len(coords) > 1: conflicts.update(coords)
    return conflicts

def check_win(grid): # Win checker :D
    if any(0 in row for row in grid):
        return False
    if find_conflicts(grid):
        return False
    return True

def load_sounds(language):
    if language == 'none':
        return []
    
    loaded_sounds = []
    csv_path = os.path.join('res', f'{language}.csv')
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    audio_path = os.path.join('res', row[2].strip())
                    if os.path.exists(audio_path):
                        try:
                            loaded_sounds.append(pygame.mixer.Sound(audio_path))
                        except pygame.error as e:
                            print(f"Error loading sound {audio_path}: {e}")
                    else:
                        print(f"Missing audio: {audio_path}")
    except FileNotFoundError:
        print(f"Missing CSV: {csv_path}")
    return loaded_sounds

def draw_start_screen():
    WIN.fill(MENU_COLOR)
    lang = languages[selected_lang]
    title_text_surface = title_font.render("Sudoku", True, TITLE_COLOR)
    title_rect = title_text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
    WIN.blit(title_text_surface, title_rect)
    
    if lang['code'] == 'none':
        name_text_surface = menu_font.render(lang['name'], True, TEXT_COLOR)
    else:
        name_text_surface = cjk_font.render(lang['name'], True, TEXT_COLOR)
    
    name_rect = name_text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 + 10))
    WIN.blit(name_text_surface, name_rect)
    instr_text = menu_font.render("<- -> to select | Enter to start", True, TEXT_COLOR)
    instr_rect = instr_text.get_rect(center=(WIDTH//2, HEIGHT - 70))
    WIN.blit(instr_text, instr_rect)
    esc_text = menu_font.render("ESC to quit", True, TEXT_COLOR)
    esc_rect = esc_text.get_rect(center=(WIDTH//2, HEIGHT - 35))
    WIN.blit(esc_text, esc_rect)

def draw_grid():
    WIN.fill(BG_COLOR)
    for row in range(9):
        for col in range(9):
            rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(WIN, CELL_COLOR, rect)

            num = sample_board[row][col]
            if num != 0:
                if (row, col) in conflict_cells:
                    color = CONFLICT_COLOR
                elif not editable[row][col]:
                    color = FIXED_NUM_COLOR
                else:
                    color = USER_NUM_COLOR

                text = number_font.render(str(num), True, color)
                text_rect = text.get_rect(center=rect.center)
                WIN.blit(text, text_rect)

            if row == selected_row and col == selected_col:
                pygame.draw.rect(WIN, SELECTED_COLOR, rect, 3)

    for i in range(10):
        thickness = 4 if i % 3 == 0 else 1
        pygame.draw.line(WIN, GRID_COLOR, (i * CELL_SIZE, 0), (i * CELL_SIZE, HEIGHT), thickness)
        pygame.draw.line(WIN, GRID_COLOR, (0, i * CELL_SIZE), (WIDTH, i * CELL_SIZE), thickness)

def create_win_surface():
    global win_surface_cached
    
    win_surface_cached = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    win_surface_cached.fill((173, 216, 230, 180))
    
    win_text_surface = win_font.render("You Win!", True, TITLE_COLOR)
    win_rect = win_text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
    win_surface_cached.blit(win_text_surface, win_rect)

    instr_text = menu_font.render("Enter to Play Again | ESC for Menu", True, TEXT_COLOR)
    instr_rect = instr_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
    win_surface_cached.blit(instr_text, instr_rect)

def draw_win_screen():
    global win_surface_cached
    
    if win_surface_cached is None:
        create_win_surface()
    
    WIN.blit(win_surface_cached, (0, 0))

# Main looooop stuff
running = True
clock = pygame.time.Clock()

while running:
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            need_redraw = True
            
            if event.key == pygame.K_ESCAPE:
                if current_state == GAME_SCREEN or current_state == WIN_SCREEN:
                    current_state = START_SCREEN
                    win_surface_cached = None
                else:
                    running = False

            if current_state == START_SCREEN:
                if event.key == pygame.K_LEFT:
                    selected_lang = (selected_lang - 1) % len(languages)
                elif event.key == pygame.K_RIGHT:
                    selected_lang = (selected_lang + 1) % len(languages)
                elif event.key == pygame.K_RETURN:
                    #print(f"Selected language: {languages[selected_lang]['name']}") # debugging line, remove?
                    sounds = load_sounds(languages[selected_lang]['code'])
                    #print(f"Loaded {len(sounds)} sounds.") # debugging line, remove?

                    new_board = generate_sudoku()
                    sample_board.clear(); sample_board.extend(new_board)
                    new_editable = [[cell == 0 for cell in row] for row in sample_board]
                    editable.clear(); editable.extend(new_editable)
                    conflict_cells.clear()
                    selected_row, selected_col = 0, 0
                    current_state = GAME_SCREEN
                    win_surface_cached = None

            elif current_state == GAME_SCREEN:
                if event.key == pygame.K_UP:
                    selected_row = max(0, selected_row - 1)
                elif event.key == pygame.K_DOWN:
                    selected_row = min(8, selected_row + 1)
                elif event.key == pygame.K_LEFT:
                    selected_col = max(0, selected_col - 1)
                elif event.key == pygame.K_RIGHT:
                    selected_col = min(8, selected_col + 1)
                elif event.key in keys or event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    if editable[selected_row][selected_col]:
                        num_to_set = 0
                        if event.key in keys:
                            num_to_set = keys[event.key]
                        
                        sample_board[selected_row][selected_col] = num_to_set

                        if event.key in keys and sounds and 0 <= num_to_set - 1 < len(sounds):
                            sounds[num_to_set - 1].play()

                        conflict_cells = find_conflicts(sample_board)
                        if check_win(sample_board):
                            current_state = WIN_SCREEN
                            win_surface_cached = None

            elif current_state == WIN_SCREEN:
                if event.key == pygame.K_RETURN:
                    new_board = generate_sudoku()
                    sample_board.clear(); sample_board.extend(new_board)
                    new_editable = [[cell == 0 for cell in row] for row in sample_board]
                    editable.clear(); editable.extend(new_editable)
                    conflict_cells.clear()
                    selected_row, selected_col = 0, 0
                    current_state = GAME_SCREEN
                    win_surface_cached = None

    if need_redraw:
        if current_state == START_SCREEN:
            draw_start_screen()
        elif current_state == GAME_SCREEN:
            draw_grid()
        elif current_state == WIN_SCREEN:
            draw_grid()
            draw_win_screen()
        
        pygame.display.update()
        need_redraw = False

pygame.quit()
