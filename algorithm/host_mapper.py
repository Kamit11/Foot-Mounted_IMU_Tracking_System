import numpy as np
from collections import defaultdict

def calculate_walls(step_coords_list):
    """
    Takes a list of (X, Y) step coordinates, applies Manhattan snapping, 
    and prints the calculated wall lengths.
    """
    step_coords = np.array(step_coords_list)
    
    # Calculate step vectors
    delta_coords = np.diff(step_coords, axis=0)
    step_distances = np.linalg.norm(delta_coords, axis=1)

    # Filter out tiny micro movements
    valid_steps = step_distances > 0.2
    if not np.any(valid_steps):
        print("No valid steps found.")
        return

    valid_delta_coords = delta_coords[valid_steps]
    valid_step_distances = step_distances[valid_steps]

    # Find dominant grid
    step_heading_rads = np.arctan2(valid_delta_coords[:, 1], valid_delta_coords[:, 0])
    theta_4 = step_heading_rads * 4

    mean_cos = np.sum(valid_step_distances * np.cos(theta_4))
    mean_sin = np.sum(valid_step_distances * np.sin(theta_4))

    grid_offset_rad = np.arctan2(mean_sin, mean_cos) / 4.0
    grid_offset_deg = np.rad2deg(grid_offset_rad)
    print(f'Calculated grid offset: {grid_offset_deg:.2f} deg')

    # Apply Manhattan snapping
    all_headings_rad = np.arctan2(delta_coords[:, 1], delta_coords[:, 0])
    all_headings_deg = np.rad2deg(all_headings_rad)
    
    snapped_headings_deg = np.round((all_headings_deg - grid_offset_deg) / 90) * 90 + grid_offset_deg

    # Calculate steps per wall
    corner_distances = []
    current_leg_distance = step_distances[0]
    current_heading = snapped_headings_deg[0]
    
    wall_counter = 1
    steps_per_wall = defaultdict(list)

    if step_distances[0] > 0.2:
        steps_per_wall[1].append(step_distances[0])

    for i in range(1, len(step_distances)):
        raw_diff = snapped_headings_deg[i] - current_heading
        heading_diff = (raw_diff + 180) % 360 - 180
        
        is_real_step = step_distances[i] > 0.2

        if abs(heading_diff) > 1.0 and is_real_step:
            corner_distances.append(current_leg_distance)
            wall_counter += 1
            current_leg_distance = step_distances[i]
            current_heading = snapped_headings_deg[i]
        else:
            current_leg_distance += step_distances[i]

        if is_real_step:
            steps_per_wall[wall_counter].append(step_distances[i])

    corner_distances.append(current_leg_distance)
    
    # Print the output
    for idx, length in enumerate(corner_distances):
        print(f"Wall {idx+1}: {length:.2f} m")

    print(f"Total calculated distance: {sum(corner_distances):.2f} m")
    print('- - - - - - -')
    for wall_num, steps in steps_per_wall.items():
        print(f'Wall: {wall_num}, Steps: {len(steps)}, Calculated last step: {steps[-1]:.2f} m -> (total: {sum(steps):.2f})')