from typing import Optional
from ..geometry import Disk
from pyquadtree import QuadTree
from .disjoint_set import DisjointSet

Component = list[Disk]

class DiskConnectivity:
    def __init__(self):
        self._disk_set: set[Disk] = set()
        self._disjoint_set = DisjointSet[Disk]()
        self._component_tree = ComponentTree()
        self._excluded_disk = None

    def clear(self):
        self._disk_set.clear()
        self._disjoint_set = DisjointSet[Disk]()
        self._component_tree = ComponentTree()
        self._excluded_disk = None


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
                #for disk in largest_component_leaf._component:
                current_node._awnn.add(disk, disk.center_point.as_tuple())

            # if more than one intersected component: clean-up step
            if len(intersected_component_leafs) > 1:
                # for every component but the largest one, find lca and update awnns on the path up and down 
                for component_node in intersected_component_leafs:
                    if component_node is largest_component_leaf:
                        continue
                    for site in component_node._component:
                        largest_component_leaf._component.append(site)
                    # Start with both nodes (largest component and the other intersected one)
                    # they are always at the same level, as we start at leafs of a full tree.
                    node_l, node_o = largest_component_leaf, component_node
                    # while not at the same node (lca), update both: insertions and deletions 
                    while node_l is not node_o:
                        for component_disk in component_node._component:
                            node_l._awnn.add(component_disk, component_disk.center_point.as_tuple())
                            node_o._awnn.delete(component_disk)
                        node_l = node_l._parent
                        node_o = node_o._parent

                    # empty the other node
                    component_node._component = None
                    self._leafQueue.append(component_node)

    def verify_tree(self):
        self._root.verify_node()

    def __repr__(self) -> str:
        return self._root.str_rep(dashes = self._root._level)
    
    def html(self) -> str:
        return str(self).replace("\n", "<br>")


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
        left_nearest = self._left._awnn.nearest_neighbors(disk.center_point.as_tuple())
        left_nearest = left_nearest[0] if left_nearest != [] else None
        if left_nearest is not None and disk.center_point.distance(left_nearest.item.center_point) <= disk.radius + left_nearest.item.radius:
            # If result not empty recurse into the child.
            intersected.extend(self._left.query_intersected(disk))  #  TODO: is extend efficient?
        right_nearest = self._right._awnn.nearest_neighbors(disk.center_point.as_tuple())
        right_nearest = right_nearest[0] if right_nearest != [] else None
        if right_nearest is not None and disk.center_point.distance(right_nearest.item.center_point) <= disk.radius + right_nearest.item.radius:
            intersected.extend(self._right.query_intersected(disk))

        return intersected
    
    def verify_node(self):
        if self._level > 0:
            if self._left is None or self._right is None:
                raise AssertionError("Non-leaf node without children")
            if self._component is not None:
                raise AssertionError("Non-leaf node with component")
            if self._left._level != self._level - 1:
                raise AssertionError("Left child has wrong level")
            if self._right._level != self._level - 1:
                raise AssertionError("Right child has wrong level")
            for site in self._left._awnn.get_all_elements():
                if site not in self._awnn.get_all_elements():
                    raise AssertionError("Left child contains site not in parent")
            for site in self._right._awnn.get_all_elements():
                if site not in self._awnn.get_all_elements():
                    raise AssertionError("Right child contains site not in parent")
            if len(self._left._awnn.get_all_elements()) + len(self._right._awnn.get_all_elements()) != len(self._awnn.get_all_elements()):
                raise AssertionError("Child awnns do not match parent")
            self._left.verify_node()
            self._right.verify_node()
        elif self._level < 0:
            raise AssertionError("Negative level")
        else:  # level == 0
            if self._left is not None or self._right is not None:
                raise AssertionError("Leaf node with children")
            if self._component is None and self._awnn.get_all_elements() != []:
                raise AssertionError("Non-empty leaf node without component")
            if self._component is not None and len(self._component) != len(self._awnn.get_all_elements()):
                raise AssertionError("Leaf node component and awnn do not match")
            for site in self._awnn.get_all_elements():
                if site.item not in self._component:
                    raise AssertionError("Leaf node contains site not in component")
                
    def str_rep(self, dashes) -> str:
        if self.is_leaf():
            return "_" * (dashes - self._level)*4 + f"Leaf: {self._component}"
        else:
            return "_" * (dashes - self._level)*4 + f"{dashes - self._level}-Node: \n {self._left.str_rep(dashes)} \n {self._right.str_rep(dashes)}"
        
