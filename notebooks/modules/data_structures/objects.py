from __future__ import annotations
from typing import Iterable, Iterator, Optional, Tuple

from ..geometry import LineSegment, Orientation as ORT, Point

class Vertex:
    def __init__(self, point: Point):
        self._point = point
        self._edge: HalfEdge = HalfEdge(self)

    def outgoing_edges(self) -> Iterable[HalfEdge]:
        outgoing_edges = []
        outgoing_edge = self.edge
        if outgoing_edge.destination == self: #single vertex
            return []
        outgoing_edges.append(outgoing_edge) #at least one outgoing edge
        outgoing_edge = outgoing_edge.twin.next
        while outgoing_edge != self.edge:
            outgoing_edges.append(outgoing_edge)
            outgoing_edge = outgoing_edge.twin.next
        return outgoing_edges

    #outgoing and ingoing edges
    def incident_edges(self) -> Iterable[HalfEdge]:
        incident_edges = []
        for out_edge in self.outgoing_edges():
            incident_edges.append(out_edge)
            incident_edges.append(out_edge.twin)
        return incident_edges

    @property
    def point(self) -> Point:
        return self._point

    @property
    def x(self) -> float:
        return self._point.x

    @property
    def y(self) -> float:
        return self._point.y

    @property
    def edge(self) -> HalfEdge:
        return self._edge

    def __repr__(self) -> str:
        return f"Vertex@{self._point}"

class HalfEdge:
    def __init__(self, origin: Vertex):
        self._origin = origin
        self._twin: HalfEdge = self
        self._prev: HalfEdge = self
        self._next: HalfEdge = self
        self._incident_face = None

    def cycle(self) -> Iterable[HalfEdge]:
        cycle = [self]
        next_edge = self.next
        while next_edge != self:
            cycle.append(next_edge)
            next_edge = next_edge.next
        return cycle

    @property
    def origin(self) -> Vertex:
        return self._origin

    @property
    def destination(self) -> Vertex:
        return self._twin._origin

    @property
    def upper_and_lower(self) -> tuple[Vertex, Vertex]:
        p, q = self._origin, self.destination
        if p.y > q.y or (p.y == q.y and p.x < q.x):
            return p, q
        else:
            return q, p

    @property
    def twin(self) -> HalfEdge:
        return self._twin

    @property
    def prev(self) -> HalfEdge:
        return self._prev

    @property
    def next(self) -> HalfEdge:
        return self._next
    
    @property
    def incident_face(self) -> Face:
        return self._incident_face

    def _set_twin(self, twin: HalfEdge):
        self._twin = twin
        twin._twin = self

    def _set_prev(self, prev: HalfEdge):
        self._prev = prev
        prev._next = self

    def _set_next(self, next: HalfEdge):
        self._next = next
        next._prev = self

    def __repr__(self) -> str:
        return f"Edge@{self._origin._point}->{self.destination._point}"
    
class Face:
    """ Simple face without inner components """
    #TODO: add inner components (and corresponding methods: innercomponents, innerhalfedges, innerpolygons, ...)
    def __init__(self, outer_component: HalfEdge):
        self._outer_component: HalfEdge = outer_component
        self._is_outer = False
    
    @property
    def outer_component(self):
        return self._outer_component
    
    @property
    def is_outer(self):
        return self._is_outer
    
    def outer_points(self) -> Iterable[Point]:
        return [edge.origin.point for edge in self.outer_half_edges()]
    
    def outer_vertices(self) -> Iterable[Vertex]:
        return [edge.origin for edge in self.outer_half_edges()]
    
    def outer_half_edges(self) -> Iterable[HalfEdge]:
        if self.outer_component == None:
            return []
        outer_edges = [self._outer_component]
        current_edge = self.outer_component.next
        while current_edge != self.outer_component:
            outer_edges.append(current_edge)
            current_edge = current_edge.next
        return outer_edges
    
    def contains(self, point: Point) -> bool:
        # import here because of circular imports
        from .dcsp import DoublyConnectedSimplePolygon
        from .triangulation import monotone_triangulation
        if self.is_convex():
            for edge in self.outer_half_edges():
                if point.orientation(edge.origin, edge.destination) != ORT.LEFT:
                    return False
            return True
        else:
            # Triangulate
            dcsp = DoublyConnectedSimplePolygon.try_from_unordered_points(self.outer_points())
            point_sequence = monotone_triangulation(dcsp)
            points = point_sequence.points()
            first = None
            for point in points:
                if first == None:
                    first = point
                else:
                    added_edge = dcsp.find_edge(first, point)
                    first = None
                    inside = True
                    for edge in added_edge.cycle():
                        if point.orientation(edge.origin, edge.destination) != ORT.LEFT:
                            inside = False
                            continue
                    if inside:
                        return True
            return False

    def is_convex(self) -> bool:
        if len(self.outer_vertices) < 3:
            raise Exception("Convexitivity is illdefined for polygons of 2 or less vertices.")
        for edge in self.outer_half_edges():
            if edge.next.destination.point.orientation(edge.origin.point, edge.destination.point) == ORT.RIGHT:
                return False
        return True

    # TODO maybe add additional methods (see ruler of the plane): polygon, polygonwithourholes, area, contains, boundingbox, tostring