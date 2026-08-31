import pandas as pd
import numpy as np
import pyvista as pv
import firmware_sim as sim

def extract_steps_from_raw(csv_filepath):
    df = pd.read_csv(csv_filepath, skipinitialspace=True)
    
    state = sim.SystemState()
    step_records = []
    
    # Anchor step at origin, assuming default TRANSIT (-1) state
    step_records.append({'X': 0.0, 'Y': 0.0, 'poly_id': -1}) 
    t_last = df['t_us'].iloc[0]

    print("Running offline firmware simulation...")
    for index, row in df.iterrows():
        ax, ay, az = row['ax'], row['ay'], row['az']
        gx, gy, gz = row['gx'], row['gy'], row['gz']
        t_current = row['t_us']
        poly_id = int(row.get('polygon_association', -1)) # Safely get keystroke ID

        dt = (t_current - t_last) / 1e6
        t_last = t_current
        if dt <= 0: dt = 0.005 

        is_zvw = sim.update_zvw(state.zvw, ax, ay, az, gx, gy, gz)
        sim.update_mahony(state.mahony, ax, ay, az, gx, gy, gz, dt, state.zvw.instant_quiet)

        if state.mahony.is_initialized:
            sim.update_kinematics(state.kinematics, state.mahony.q, ax, ay, az, dt, is_zvw, state.zvw.dwell_counter)

            # The exact tick the step is planted, save coordinates AND the active polygon ID
            if state.zvw.dwell_counter == sim.DWELL:
                step_records.append({
                    'X': state.kinematics.position[0],
                    'Y': state.kinematics.position[1],
                    'poly_id': poly_id
                })

    return pd.DataFrame(step_records)

def apply_manhattan_snapping(df):
    step_coords = df[['X', 'Y']].values
    delta_coords = np.diff(step_coords, axis=0)
    step_distances = np.linalg.norm(delta_coords, axis=1)

    valid_steps = step_distances > 0.2
    if not np.any(valid_steps): return df
    
    valid_deltas = delta_coords[valid_steps]
    valid_dists = step_distances[valid_steps]
    
    step_heading_rads = np.arctan2(valid_deltas[:, 1], valid_deltas[:, 0])
    theta_4 = step_heading_rads * 4
    grid_offset_rad = np.arctan2(np.sum(valid_dists * np.sin(theta_4)), 
                                 np.sum(valid_dists * np.cos(theta_4))) / 4.0
    
    all_headings_rad = np.arctan2(delta_coords[:, 1], delta_coords[:, 0])
    snapped_headings_rad = np.round((all_headings_rad - grid_offset_rad) / (np.pi/2)) * (np.pi/2) + grid_offset_rad

    snapped_dx = step_distances * np.cos(snapped_headings_rad)
    snapped_dy = step_distances * np.sin(snapped_headings_rad)
    
    snapped_coords = np.zeros_like(step_coords)
    snapped_coords[0] = step_coords[0] 
    snapped_coords[1:, 0] = step_coords[0, 0] + np.cumsum(snapped_dx)
    snapped_coords[1:, 1] = step_coords[0, 1] + np.cumsum(snapped_dy)

    df_snapped = df.copy()
    df_snapped['X'] = snapped_coords[:, 0]
    df_snapped['Y'] = snapped_coords[:, 1]
    
    return df_snapped

def render_25d_scene(df, extrude_height=1.0):
    plotter = pv.Plotter()
    
    path_points = df[['X', 'Y']].values
    path_3d = np.column_stack((path_points, np.zeros(len(path_points))))
    
    path_line = pv.lines_from_points(path_3d)
    plotter.add_mesh(path_line, color='red', line_width=3, label='Walking Path')
    
    polygons = df[df['poly_id'] != -1].groupby('poly_id')
    
    for poly_id, group in polygons:
        points = group[['X', 'Y']].values
        
        if not np.array_equal(points[0], points[-1]):
            points = np.vstack([points, points[0]])
            
        points_3d = np.column_stack((points, np.zeros(len(points))))
        
        num_verts = len(points_3d)
        faces = np.insert(np.arange(num_verts), 0, num_verts)
        mesh = pv.PolyData(points_3d, faces)
        
        if poly_id == 1:
            plotter.add_mesh(mesh, color='lightgray', opacity=0.4, show_edges=True, label='Room Boundary')
        else:
            extruded_block = mesh.extrude((0, 0, extrude_height), capping=True)
            plotter.add_mesh(extruded_block, color='lightblue', show_edges=True, label=f'Object {poly_id}')

    plotter.add_axes()
    plotter.show_grid()
    plotter.add_legend()

    plotter.export_html(f"{file_path}{file_name}".replace('.csv','interactive_room_map.html'))
    plotter.export_gltf(f"{file_path}{file_name}".replace('.csv','room_model.gltf'))

    # Let PyVista handle the screenshot during the render loop execution
    plotter.show(screenshot="static_map_render.png")


if __name__ == "__main__":
    file_path = "data/pyvista_mappings/"
    file_name = "polygons_test_wired_31-08-2026_21-21-29.csv" 
    
    df_steps = extract_steps_from_raw(f"{file_path}{file_name}")
    
    print("Applying Manhattan snapping...")
    df_snapped = apply_manhattan_snapping(df_steps)
    
    print("Rendering PyVista Environment...")
    render_25d_scene(df_snapped)