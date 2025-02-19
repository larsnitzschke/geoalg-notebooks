class TreeNode:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children if children is not None else []

class TreeLayout:
    def __init__(self, node, x=0, y=0, mod=0):
        self.node = node
        self.x = x
        self.y = y
        self.mod = mod
        self.children = []

def first_walk(node, depth=0, mod=0):
    layout = TreeLayout(node, y=depth, mod=mod)
    if not node.children:
        return layout

    for child in node.children:
        layout.children.append(first_walk(child, depth + 1))

    if len(layout.children) == 1:
        layout.x = layout.children[0].x
    else:
        layout.x = (layout.children[0].x + layout.children[-1].x) / 2

    return layout

def second_walk(layout, mod=0):
    layout.x += mod
    for child in layout.children:
        second_walk(child, mod + layout.mod)

def reingold_tilford(root):
    layout = first_walk(root)
    second_walk(layout)
    return layout

def draw_tree(canvas, layout, dx=50, dy=50):
    if layout is None:
        return

    x = layout.x * dx + 200
    y = layout.y * dy + 50
    canvas.fill_text(str(layout.node.value), x, y)

    for child in layout.children:
        child_x = child.x * dx + 200
        child_y = child.y * dy + 50
        canvas.stroke_line(x, y, child_x, child_y)
        draw_tree(canvas, child, dx, dy)