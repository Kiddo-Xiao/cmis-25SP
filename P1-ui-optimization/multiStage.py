from ui import UI 
import gurobipy as gp 
from gurobipy import GRB
import itertools
import random
import sys
import numpy as np

# Load scene information
scene_path = "scenes/scene-1.json"
if len(sys.argv) >= 2:
    scene_path = sys.argv[1]

# Loads target scene
# default: scene.json
scene_UI = UI(scene_path)

# Gets available applications
app_ids = list(scene_UI.apps.keys())

# Get scene information
info = scene_UI.get_info()
# print(info)

''' Create a model for Phase 1 (Application & LoD selection) '''
print("--------STAGE-1-------")
m1 = gp.Model("ui_selection")

# Decision Variables: y[app, lod] = 1 if app is selected with lod
y = {}
for app, lod in itertools.product(app_ids, range(scene_UI.LODS)):
    y[app, lod] = m1.addVar(vtype=GRB.BINARY, name=f"y_{app}_{lod}")

# Constraint 1-1: Max 4 applications placed
m1.addConstr(gp.quicksum(y[app, lod] for app in app_ids for lod in range(scene_UI.LODS)) <= 4)

# Constraint 1-2: Each app can only be selected with one LoD
for app in app_ids:
    m1.addConstr(gp.quicksum(y[app, lod] for lod in range(scene_UI.LODS)) <= 1)

# Constraint 1-3: 
# LoD Selection with Feasibility Constraints (Now in Pixels)
max_grid_space = info["columns"] * info["rows"]
# Convert grid size to pixels
grid_width_px = info["columns"] * info["block_size"]
grid_height_px = info["rows"] * info["block_size"]
# Get UI element sizes in pixels(already in pixels)
btn_all_width_px, btn_all_height_px = info["btn_all_size"]
questions_width_px, questions_height_px = info["questions_size"]
roi_radius_px = info["roi_rad"]  
btn_all_area_px = btn_all_width_px * btn_all_height_px
questions_area_px = questions_width_px * questions_height_px
roi_area_px = np.pi * (roi_radius_px ** 2)
# Compute available space in pixels
total_ui_area_px = grid_width_px * grid_height_px
available_space_px = total_ui_area_px - (btn_all_area_px + questions_area_px + roi_area_px)
# bies_for_better_placement = 1
bies_for_better_placement = 1 - roi_radius_px * 2 / grid_width_px
available_space = (available_space_px * bies_for_better_placement) // (info["block_size"] ** 2)
# Ensure selected applications fit within the available space
m1.addConstr(gp.quicksum(y[app, lod] * ((1 if lod == 0 else 2) * (1 if lod < 2 else 2)) 
              for app, lod in itertools.product(app_ids, range(scene_UI.LODS))) <= available_space)


# Bonus-1: Automatically calculate relevance(Implemented in ui.py)
for app in app_ids:
    print(f"{app}: {scene_UI.relevance[app]}")

# Objective Function: Maximize relevance * LoD weight
objective1 = gp.quicksum(scene_UI.relevance[app] * (1 + 0.5 * lod) * y[app, lod] for app in app_ids for lod in range(scene_UI.LODS))
m1.ModelSense = GRB.MAXIMIZE
m1.setObjective(objective1)
m1.update()
m1.optimize()

selected_apps = [(app, lod) for app, lod in itertools.product(app_ids, range(scene_UI.LODS)) if y[app, lod].X == 1]
print("bies_for_better_placement: ", bies_for_better_placement)
print("selected_apps: ", selected_apps)
print("--------STAGE-1 END-------")

''' Create a model for Phase 2 (Placement Optimization) '''
stage2_iteration = 0
while True:  # Adaptive LoD Reduction Loop
    m2 = gp.Model("ui_placement")
    print("--------STAGE-2: Tryout-", stage2_iteration, " --------")

    # Decision variables: x[app, lod, xIdx, yIdx] = 1 if app is placed at (xIdx, yIdx) with lod
    x = {}
    for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
        x[app, lod, xIdx, yIdx] = m2.addVar(vtype=GRB.BINARY, name=f"x_{app}_{lod}_{xIdx}_{yIdx}")

    ##### TODO: DEFINE OBJECTIVES AND CONSTRAINTS #####
    '''
    Input into interface.init_app() should be as follows:
    optimal_results (list of dict): A list where each dictionary contains:
                - "name" (str): The name of the app (e.g., "weather", "time").
                - "lod" (int): Level of detail (e.g., 0 or 1).
                - "placement" (list of int): A list of two integers indicating the placement slot (e.g., [4, 4]; NOTE: This specifies the placement slot rather than the exact placement position)

    Potentially relevant information can be obtained by calling scene_UI.get_info(), which returns a dictionary containing:
    - "columns" (int): Number of columns in the UI grid.
    - "rows" (int): Number of rows in the UI grid.
    - "block_size" (int): Size of each block in the grid.
    - "questions_pos" (numpy.ndarray): Position of the question panel in the UI.
    - "questions_size" (numpy.ndarray): Width and height of the question panel.
    - "btn_all_pos" (numpy.ndarray): Position of the "Apps" button.
    - "btn_all_size" (numpy.ndarray): Width and height of the "Apps" button.
    - "roi_pos" (numpy.ndarray): Position of the Region of Interest (ROI) in the UI.
    - "roi_rad" (int): Radius of the Region of Interest (ROI).
    - "relevance" (dict[str, float]): A dictionary mapping application names to their relevance scores.
    '''

    # Constraint 2-1: Place only selected apps
    m2.addConstr(gp.quicksum(x[app, lod, xIdx, yIdx] for app, lod, xIdx, yIdx 
                            in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"]))
                            if (app, lod) not in selected_apps)
                            == 0)

    # Constraint 2-2: Each app is placed at most once
    for app, lod in selected_apps:
        m2.addConstr(gp.quicksum(x[app, lod, xIdx, yIdx] for xIdx in range(info["columns"]) for yIdx in range(info["rows"])) <= 1)

    # Constraint 2-3: Ensure apps fit within grid boundaries considering their size
    for app, lod in selected_apps:
        for xIdx, yIdx in itertools.product(range(info["columns"]), range(info["rows"])):
            width = 1 if lod == 0 else 2
            height = 1 if lod < 2 else 2
            if xIdx + width > info["columns"] or yIdx + height > info["rows"]:
                m2.addConstr(x[app, lod, xIdx, yIdx] == 0)

    # Constraint 2-4: Prevent overlapping, considering dif lod of apps
    occupied = {(x, y): gp.LinExpr() for x in range(info["columns"]) for y in range(info["rows"]) }
    for app, lod in selected_apps:
        for xIdx, yIdx in itertools.product(range(info["columns"]), range(info["rows"])):
            width = 1 if lod == 0 else 2
            height = 1 if lod < 2 else 2
            for dx in range(width):
                for dy in range(height):
                    if xIdx + dx < info["columns"] and yIdx + dy < info["rows"]:
                        occupied[xIdx + dx, yIdx + dy] += x[app, lod, xIdx, yIdx]
    m2.addConstrs(occupied[x, y] <= 1 for x, y in occupied)

    # Constraint 2-5: Avoid overlapping "All Apps" button & questions panel, considering dif lod of apps
    q_x, q_y = info["questions_pos"][0] // info["block_size"], info["questions_pos"][1] // info["block_size"]
    btn_all_x, btn_all_y = info["btn_all_pos"][0] // info["block_size"], info["btn_all_pos"][1] // info["block_size"]
    restricted_areas_for_lod_0 = [(btn_all_x, btn_all_y), (q_x, q_y)]
    restricted_areas_for_lod_1 = [(btn_all_x, btn_all_y), (q_x, q_y)]
    restricted_areas_for_lod_2 = [(btn_all_x, btn_all_y), (q_x, q_y)]
    surroundings_for_lod_012 = [(0, 1), (1, 0), (1, 1)]
    surroundings_for_lod_12 = [(-1, 0), (-1, 1)]
    surroundings_for_lod_2 = [(-1, -1), (0, -1), (1, -1)]
    for dx, dy in surroundings_for_lod_012:
        nx, ny = q_x + dx, q_y + dy
        if 0 <= nx < info["columns"] and 0 <= ny < info["rows"]:
            restricted_areas_for_lod_0.append((nx, ny))
            restricted_areas_for_lod_1.append((nx, ny))
            restricted_areas_for_lod_2.append((nx, ny))
    for app, lod in selected_apps:
        for xIdx, yIdx in itertools.product(range(info["columns"]), range(info["rows"])):
            if lod == 1 or lod == 2:
                for dx, dy in surroundings_for_lod_12:
                    nx, ny = q_x + dx, q_y + dy
                    if 0 <= nx < info["columns"] and 0 <= ny < info["rows"]:
                        restricted_areas_for_lod_1.append((nx, ny))
                        restricted_areas_for_lod_2.append((nx, ny))
            if lod == 2:
                for dx, dy in surroundings_for_lod_2:
                    nx, ny = q_x + dx, q_y + dy
                    if 0 <= nx < info["columns"] and 0 <= ny < info["rows"]:
                        restricted_areas_for_lod_2.append((nx, ny))

    m2.addConstr(gp.quicksum(x[app, 0, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_0) == 0)
    m2.addConstr(gp.quicksum(x[app, 1, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_1) == 0)
    m2.addConstr(gp.quicksum(x[app, 2, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_2) == 0)

    # Constraint 2-6: Avoid overlapping Region of Interest (ROI)
    roi_x, roi_y = info["roi_pos"]
    roi_radius = info["roi_rad"]
    # print(f"ROI_Center: {roi_x}, {roi_y} , ROI_Radius: {roi_radius}")
    for app, lod in selected_apps:
        for xIdx in range(info["columns"]):
            for yIdx in range(info["rows"]):
                width = 1 if lod == 0 else 2
                height = 1 if lod < 2 else 2
                if scene_UI.circle_rectangle_overlap(roi_x, roi_y, roi_radius, xIdx * info['block_size'], yIdx * info['block_size'], width * info['block_size'], height * info['block_size']):
                    # print(f"Overlap Pos: {xIdx}, {yIdx}, LoD: {lod}")
                    m2.addConstr(x[app, lod, xIdx, yIdx] == 0)

    # Version-3: Relevance, LoD Preference, and Interaction Cost
    lambda_weight = 0.1  # Interaction cost penalty weight
    question_x, question_y = info["questions_pos"][0] // info["block_size"] + 1 , info["questions_pos"][1] // info["block_size"] + 1 # Center of questions panel(2 x 2)
    objective2 = gp.quicksum(
        (scene_UI.relevance[app] / (1 + lambda_weight * ((xIdx - question_x) ** 2 + (yIdx - question_y) ** 2)))
        * (1 + lod) * x[app, lod, xIdx, yIdx]
        for app, lod in selected_apps
        for xIdx in range(info["columns"])
        for yIdx in range(info["rows"])
    )

    # Setting up the model in Gurobi and optimizing it
    m2.ModelSense = GRB.MAXIMIZE  # Maximize relevance score
    m2.setObjective(objective2)
    m2.update()
    m2.optimize()
    print("--------STAGE-2 Tryout-", stage2_iteration, " END--------")

    # Check if placement succeeded**
    placed_apps = set()
    for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
        if x[app, lod, xIdx, yIdx].X == 1:
            placed_apps.add(app)

    if len(placed_apps) == len(selected_apps):
        print(f"Success: All {len(selected_apps)} apps placed.")
        break  

    # Step 3: Reduce LoD of the least relevant app in selected_apps
    print("Placement failed!")
    max_lod = max(lod for _, lod in selected_apps)
    max_lod_apps = [(app, lod) for app, lod in selected_apps if lod == max_lod]
    app_to_reduce = min(max_lod_apps, key=lambda app: scene_UI.relevance[app[0]])
    # Reduce LoD
    selected_apps.remove(app_to_reduce)
    new_lod = app_to_reduce[1] - 1
    selected_apps.append((app_to_reduce[0], new_lod))
    print(f"Reduced LoD of {app_to_reduce[0]} to {new_lod}")
    # If all apps are at LoD=0, stop to prevent infinite loops
    if all(lod == 0 for _, lod in selected_apps):
        print("All apps are at LoD=0, stopping optimization.")
        break

    stage2_iteration += 1


# Extract optimal results
optimal_results = []
for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
    if x[app, lod, xIdx, yIdx].X == 1:
        optimal_results.append({
            "name": app,
            "lod": lod,
            "placement": [xIdx, yIdx]
        })

# Start optimized UI
scene_UI.init_app(optimal_results)
