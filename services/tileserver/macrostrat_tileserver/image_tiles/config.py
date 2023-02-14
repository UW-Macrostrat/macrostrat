# All of our burwell scales
scales = ["tiny", "small", "medium", "large"]

# Which zoom levels correspond to which map scales
scale_zooms = {
    "tiny": [0, 1, 2],
    "small": [3, 4, 5],
    "medium": [6, 7, 8],
    "large": [9, 10, 11, 12, 13],
}


def scale_for_zoom(zoom):
    if zoom < 3:
        return "tiny"
    if zoom < 6:
        return "small"
    if zoom < 9:
        return "medium"
    return "large"


# The order in which scales should be drawn for each layer
layer_order = {
    "tiny": ["tiny"],
    "small": ["tiny", "small"],
    "medium": ["small", "medium"],
    "large": ["medium", "large"],
}
