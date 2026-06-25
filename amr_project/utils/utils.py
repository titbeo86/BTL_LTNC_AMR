import numpy as np

# Notice that pygame coordinate system vs node coordinate system
# turn node position into pixel position 
def turn2pixel(map, height, width, row_position, col_position): 
    row_segment = len(map) - 1 
    col_segment = len(map[0]) - 1 
    row_distance = height/row_segment 
    col_distance = width/col_segment 
    x_pixel = col_position * col_distance 
    y_pixel = height - row_position * row_distance 
    return (x_pixel, y_pixel)

# turn pixel position to node position 
def turn2node(map, width, height, x_pixel, y_pixel): 
    row_segment = len(map) - 1 
    col_segment = len(map[0]) - 1 
    row_distance = height/row_segment 
    col_distance = width/col_segment 
    row_pos = round((height - y_pixel)/row_distance) 
    col_pos = round(x_pixel/col_distance) 
    return (row_pos, col_pos)

def transformationMatrix2d(scale=(1.0, 1.0), rotation_deg=0.0, translation=(0.0, 0.0)):
    """
    Create a 3x3 2D transformation matrix for scaling, rotation, and translation.
    Order of operations: Scale -> Rotate -> Translate.
    
    Parameters:
        scale (tuple): (sx, sy) scaling factors.
        rotation_deg (float): Rotation angle in degrees (counterclockwise).
        translation (tuple): (tx, ty) translation values.
    
    Returns:
        np.ndarray: 3x3 transformation matrix.
    """
    sx, sy = scale
    tx, ty = translation
    theta = np.deg2rad(rotation_deg)

    # Scaling matrix
    S = np.array([
        [sx, 0,  0],
        [0,  sy, 0],
        [0,  0,  1]
    ])

    # Rotation matrix
    R = np.array([
        [np.cos(theta), -np.sin(theta), 0],
        [np.sin(theta),  np.cos(theta), 0],
        [0,              0,             1]
    ])

    # Translation matrix
    T = np.array([
        [1, 0, tx],
        [0, 1, ty],
        [0, 0, 1 ]
    ])

    # Combined transformation: T * R * S
    return T @ R @ S


def apply_transformation(points, matrix):
    """
    Apply a 3x3 transformation matrix to a set of 2D points.
    
    Parameters:
        points (np.ndarray): Nx2 array of (x, y) points.
        matrix (np.ndarray): 3x3 transformation matrix.
    
    Returns:
        np.ndarray: Transformed Nx2 points.
    """
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("Points must be an Nx2 array.")

    # Convert to homogeneous coordinates
    ones = np.ones((points.shape[0], 1))
    homogeneous_points = np.hstack([points, ones])

    # Apply transformation
    transformed = homogeneous_points @ matrix.T

    # Convert back to 2D
    return transformed[:, :2]
