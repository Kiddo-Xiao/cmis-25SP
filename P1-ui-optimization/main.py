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

# Creates a model
m = gp.Model("ui_optimizer")

# Decision variables: x[app, lod, xIdx, yIdx] = 1 if app is placed at (xIdx, yIdx) with lod
x = {}
for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
    x[app, lod, xIdx, yIdx] = m.addVar(vtype=GRB.BINARY, name=f"x_{app}_{lod}_{xIdx}_{yIdx}")

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

# Constraint 1: Max 4 elements placed
m.addConstr(gp.quicksum(x[app, lod, xIdx, yIdx] for app in app_ids for lod in range(scene_UI.LODS) for xIdx in range(info["columns"]) for yIdx in range(info["rows"])) <= 4)

# Constraint 2: Each app is placed at most once with one LoD
for app in app_ids:
    m.addConstr(gp.quicksum(x[app, lod, xIdx, yIdx] for lod in range(scene_UI.LODS) for xIdx in range(info["columns"]) for yIdx in range(info["rows"])) <= 1)

# Constraint 3: Ensure apps fit within grid boundaries considering their size
for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
    width = 1 if lod == 0 else 2
    height = 1 if lod < 2 else 2
    if xIdx + width > info["columns"] or yIdx + height > info["rows"]:
        m.addConstr(x[app, lod, xIdx, yIdx] == 0)

# Constraint 4: Prevent overlapping between apps, considering dif lod of apps
occupied = {(x, y): gp.LinExpr() for x in range(info["columns"]) for y in range(info["rows"]) }
for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
    width = 1 if lod == 0 else 2
    height = 1 if lod < 2 else 2
    for dx in range(width):
        for dy in range(height):
            if xIdx + dx < info["columns"] and yIdx + dy < info["rows"]:
                occupied[xIdx + dx, yIdx + dy] += x[app, lod, xIdx, yIdx]
m.addConstrs(occupied[x, y] <= 1 for x, y in occupied)

# Constraint 5: Avoid overlapping "All Apps" button & questions panel, considering dif lod of apps
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
for app, lod, xIdx, yIdx in itertools.product(app_ids, range(scene_UI.LODS), range(info["columns"]), range(info["rows"])):
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

m.addConstr(gp.quicksum(x[app, 0, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_0) == 0)
m.addConstr(gp.quicksum(x[app, 1, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_1) == 0)
m.addConstr(gp.quicksum(x[app, 2, xIdx, yIdx] for app in app_ids for xIdx, yIdx in restricted_areas_for_lod_2) == 0)

# Constraint 6: Avoid overlapping Region of Interest (ROI)
roi_x, roi_y = info["roi_pos"]
roi_radius = info["roi_rad"]
# print(f"ROI_Center: {roi_x}, {roi_y} , ROI_Radius: {roi_radius}")
for lod in range(scene_UI.LODS):
    for xIdx in range(info["columns"]):
        for yIdx in range(info["rows"]):
            width = 1 if lod == 0 else 2
            height = 1 if lod < 2 else 2
            if scene_UI.circle_rectangle_overlap(roi_x, roi_y, roi_radius, xIdx * info['block_size'], yIdx * info['block_size'], width * info['block_size'], height * info['block_size']):
                # print(f"Overlap Pos: {xIdx}, {yIdx}, LoD: {lod}")
                m.addConstr(gp.quicksum(x[app, lod, xIdx, yIdx] for app in app_ids) == 0)
          
# Bonus-1: Automatically calculate relevance(Implemented in ui.py)
# print app with its relevance score
for app in app_ids:
    print(f"{app}: {scene_UI.relevance[app]}")


# # Version-1: Relevance
# # Objective Function: Maximize sum of relevance scores
# objective = gp.quicksum(scene_UI.relevance[app] * x[app, lod, xIdx, yIdx] 
#                         for app in app_ids 
#                         for lod in range(scene_UI.LODS) 
#                         for xIdx in range(info["columns"]) 
#                         for yIdx in range(info["rows"]))


# # Version-2: Relevance, LoD Preference
# # Objective Function: Maximize sum of relevance scores * LoD.weight
# objective = gp.quicksum(scene_UI.relevance[app] * (1 + 0.5 * lod) * x[app, lod, xIdx, yIdx] 
#                             for app in app_ids 
#                             for lod in range(scene_UI.LODS) 
#                             for xIdx in range(info["columns"]) 
#                             for yIdx in range(info["rows"]))


# Version-3: Relevance, LoD Preference, and Interaction Cost
lambda_weight = 0.1  # Interaction cost penalty weight
question_x, question_y = info["questions_pos"][0] // info["block_size"] + 1 , info["questions_pos"][1] // info["block_size"] + 1 # Center of questions panel(2 x 2)
width = 1 if 0 == 0 else 2
height = 1 if 0 < 2 else 2
objective = gp.quicksum((scene_UI.relevance[app] / (1 + lambda_weight * ((xIdx + width / 2 - question_x) ** 2 + (yIdx + height / 2 - question_y) ** 2))) 
                        * (1 + lod) * x[app, lod, xIdx, yIdx]
                        for app in app_ids 
                        for lod in range(scene_UI.LODS) 
                        for xIdx in range(info["columns"]) 
                        for yIdx in range(info["rows"]))

# Setting up the model in Gurobi and optimizing it
m.ModelSense = GRB.MAXIMIZE
m.setObjective(objective)
m.update()
m.optimize()


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
