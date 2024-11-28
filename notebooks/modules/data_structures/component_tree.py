from typing import Optional
from ..geometry import Disk
from pyquadtree import QuadTree

Component = list[Disk]

class ComponentTree:
    def __init__(self):
        self._root = ComponentTreeNode()
        self._leafQueue = [self._root]

    def _full_sub_tree(self, depth):
        if depth <= 0:
            return None
        node = ComponentTreeNode()
        node._level = depth - 1
        if node._level == 0:
            self._leafQueue.append(node)
        else:
            node._left = self._full_sub_tree(depth = depth - 1)
            if node._left is not None:
                node._left._parent = node
            node._right = self._full_sub_tree(depth = depth - 1)
            if node._right is not None:
                node._right._parent = node
        return node

    def insert_component(self, component: list[Disk]):
        # 1 Get Leaf
        if self._leafQueue == []:
            # Double the size of the tree
            new_node = ComponentTreeNode()
            new_node.set_left_child(self._root)
            new_node.set_right_child(self._full_sub_tree(depth = self._root._level + 1))
            new_node._level = self._root._level + 1
            for disk_element in self._root._awnn.get_all_elements():
                new_node._awnn.add(disk_element.item, disk_element.point)
            self._root = new_node
        leaf: ComponentTreeNode = self._leafQueue.pop(0)

        # 2 Insert component into the leaf
        leaf._component = component            
        for disk in component:
            leaf._awnn.add(disk, disk.center_point.as_tuple())

        # Update awnns on the path to the root
        current_node: ComponentTreeNode = leaf
        while current_node._parent is not None:
            current_node = current_node._parent
            for disk in component:
                current_node._awnn.add(disk, disk.center_point.as_tuple())

    def query(self, disk: Disk) -> list[Component]:
        return [node._component for node in self.query_nodes(disk)]

    def query_nodes(self, disk: Disk):
        # Query root
        nearest = self._root._awnn.nearest_neighbors(disk.center_point.as_tuple())
        if len(nearest) == 0:
            return []  # No intersected components
        nearest = nearest[0]
        if disk.center_point.distance(nearest.item.center_point) > disk.radius + nearest.item.radius:
            return []  # No intersected components
        return self._root.query_intersected(disk)

    
    def insert_disk(self, disk: Disk):
        intersected_component_leafs = self.query_nodes(disk)
        if intersected_component_leafs == []:
            # Insert singleton component
            self.insert_component([disk])
        else:
            # find largest component
            largest_component_leaf: ComponentTreeNode = max(intersected_component_leafs, key=lambda node: len(node._component))
            # insert into largest component  # TODO: Maybe use component object for readability
            largest_component_leaf._component.append(disk)  # TODO: Check whether it is also updated in the leaf node of the tree
            largest_component_leaf._awnn.add(disk, disk.center_point.as_tuple())

            # Update awnns on the path to the root
            current_node: ComponentTreeNode = largest_component_leaf
            while current_node._parent is not None:
                current_node = current_node._parent
                for disk in largest_component_leaf._component:
                    current_node._awnn.add(disk, disk.center_point.as_tuple())

            # if more than one intersected component: clean-up step
            if len(intersected_component_leafs) > 1:
                # for every component but the largest one, find lca and update awnns on the path up and down 
                for component_node in intersected_component_leafs:
                    if component_node is largest_component_leaf:
                        continue
                    # Start with both nodes (largest component and the other intersected one)
                    # they are always at the same level, as we start at leafs of a full tree.
                    node_l, node_o = largest_component_leaf, component_node
                    # while not at the same node (lca), update both: insertions and deletions 
                    while node_l is not node_o:
                        for component_disk in component_node._component:
                            node_l._awnn.add(component_disk, component_disk.center_point.as_tuple())
                            node_o._awnn.delete(component_disk)

                    # empty the other node
                    component_node._component = None
                    self._leafQueue.append(component_node)


class ComponentTreeNode:
    def __init__(self):
        self._component: Optional[list[Disk]] = None
        self._awnn = QuadTree(bbox=(0, 0, 1000, 1000))
        self._left: Optional[ComponentTreeNode] = None
        self._right: Optional[ComponentTreeNode] = None
        self._parent: Optional[ComponentTreeNode] = None
        self._level: int = 0

    def set_left_child(self, leftChild):
        self._left = leftChild
        leftChild._parent = self

    def set_right_child(self, rightChild):
        self._right = rightChild
        rightChild._parent = self
    
    def is_leaf(self):
        return self._left is None and self._right is None
    
    def query_intersected(self, disk: Disk):
        if self.is_leaf():
            if self._component is None: 
                raise AssertionError("Something in the code is wrong")
            return [self]
        intersected: list[ComponentTreeNode] = []
        left_nearest = self._left._awnn.nearest_neighbors(disk.center_point.as_tuple())[0]
        if disk.center_point.distance(left_nearest.item.center_point) <= disk.radius + left_nearest.item.radius:
            # If result not empty recurse into the child.
            intersected.extend(self._left.query_intersected(disk))  #  TODO: is extend efficient?
        right_nearest = self._right._awnn.nearest_neighbors(disk.center_point.as_tuple())[0]
        if disk.center_point.distance(right_nearest.item.center_point) <= disk.radius + right_nearest.item.radius:
            intersected.extend(self._right.query_intersected(disk))

        return intersected
