from abc import ABC, abstractmethod
from itertools import chain
import time
from typing import Callable, Generic, Optional, TypeVar, Union

from ..geometry.core import GeometricObject, LineSegment, Point, PointReference
from ..data_structures import DoublyConnectedSimplePolygon, DoublyConnectedEdgeList, PointLocation
from .drawing import DrawingMode, LineSegmentsMode, PointsMode, PolygonMode, DCELMode

import numpy as np


I = TypeVar("I")

Algorithm = Callable[[I], GeometricObject]

class InstanceHandle(ABC, Generic[I]):
    def __init__(self, instance: I, drawing_mode: DrawingMode):
        self._instance = instance
        self._drawing_mode = drawing_mode

    @property
    def drawing_mode(self) -> DrawingMode:
        return self._drawing_mode

    def run_algorithm(self, algorithm: Algorithm[I]) -> tuple[GeometricObject, float]:
        instance_points = self.extract_points_from_raw_instance(self._instance)

        start_time = time.perf_counter()
        algorithm_output = algorithm(self._instance)
        end_time = time.perf_counter()

        self.clear()
        for point in instance_points:
            self.add_point(point)

        return algorithm_output, 1000 * (end_time - start_time)
    
    def run_algorithm_with_preprocessing(self, preprocessing: Algorithm[I], algorithm: Algorithm[I]) -> tuple[GeometricObject, float]:
        instance_points = self.extract_points_from_raw_instance(self._instance)

        preprocessing(self._instance)

        start_time = time.perf_counter()
        algorithm_output = algorithm(self._instance)
        end_time = time.perf_counter()

        self.clear()
        for point in instance_points:
            self.add_point(point)

        return algorithm_output, 1000 * (end_time - start_time)

    @abstractmethod
    def add_point(self, point: Point) -> Union[bool, tuple[bool, Point]]:
        pass

    @abstractmethod
    def clear(self):
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    @staticmethod
    @abstractmethod
    def extract_points_from_raw_instance(instance: I) -> list[Point] | list[PointReference]:
        pass

    @property
    @abstractmethod
    def default_number_of_random_points(self) -> int:
        pass

    def generate_random_points(self, max_x: float, max_y: float, number: int) -> list[Point]:
        x_values = np.random.uniform(0.05 * max_x, 0.95 * max_x, number)
        y_values = np.random.uniform(0.05 * max_y, 0.95 * max_y, number)
        return [Point(x, y) for x, y  in zip(x_values, y_values)]


class PointSetInstance(InstanceHandle[set[Point]]):
    def __init__(self, drawing_mode: Optional[DrawingMode] = None):
        if drawing_mode is None:
            drawing_mode = PointsMode()
        super().__init__(set(), drawing_mode)

    def add_point(self, point: Point) -> bool:
        if point in self._instance:
            return False
        self._instance.add(point)

        return True

    def clear(self):
        self._instance.clear()

    def size(self) -> int:
        return len(self._instance)

    @staticmethod
    def extract_points_from_raw_instance(instance: set[Point]) -> list[Point]:
        return list(instance)

    @property
    def default_number_of_random_points(self) -> int:
        return 250

    def generate_random_points(self, max_x: float, max_y: float, number: int) -> list[Point]:
        x_values = np.clip(np.random.normal(0.5 * max_x, 0.15 * max_x, number), 0.05 * max_x, 0.95 * max_x)
        y_values = np.clip(np.random.normal(0.5 * max_y, 0.15 * max_y, number), 0.05 * max_y, 0.95 * max_y)
        return [Point(x, y) for x, y in zip(x_values, y_values)]


class LineSegmentSetInstance(InstanceHandle[set[LineSegment]]):
    def __init__(self, drawing_mode: Optional[DrawingMode] = None):
        if drawing_mode is None:
            drawing_mode = LineSegmentsMode(vertex_radius = 3)
        super().__init__(set(), drawing_mode)
        self._cached_point: Optional[Point] = None

    def add_point(self, point: Point) -> bool:
        if self._cached_point is None:
            self._cached_point = point
            return True
        elif self._cached_point == point:
            return False

        line_segment = LineSegment(self._cached_point, point)
        if line_segment in self._instance:
            return False
        self._instance.add(line_segment)
        self._cached_point = None

        return True

    def clear(self):
        self._instance.clear()
        self._cached_point = None

    def size(self) -> int:
        return len(self._instance)

    @staticmethod
    def extract_points_from_raw_instance(instance: set[LineSegment]) -> list[Point]:
        return list(chain.from_iterable((segment.upper, segment.lower) for segment in instance))

    @property
    def default_number_of_random_points(self) -> int:
        return 500

    def generate_random_points(self, max_x: float, max_y: float, number: int) -> list[Point]:
        points: list[Point] = []
        for point in super().generate_random_points(max_x, max_y, number // 2):
            points.append(point)
            scale = np.random.uniform(0.01, 0.05)
            x = np.clip(np.random.normal(point.x, scale * max_x), 0.05 * max_x, 0.95 * max_x)
            y = np.clip(np.random.normal(point.y, scale * max_y), 0.05 * max_y, 0.95 * max_y)
            points.append(Point(x, y))

        if number % 2 == 1:
            points.extend(super().generate_random_points(max_x, max_y, 1))

        return points


class SimplePolygonInstance(InstanceHandle[DoublyConnectedSimplePolygon]):
    def __init__(self, drawing_mode: Optional[DrawingMode] = None):
        if drawing_mode is None:
            drawing_mode = PolygonMode(mark_closing_edge = True, draw_interior = False, vertex_radius = 3)
        super().__init__(DoublyConnectedSimplePolygon(), drawing_mode)

    def add_point(self, point: Point) -> bool:
        try:
            self._instance.add_vertex(point)
        except Exception:
            return False

        return True

    def clear(self):
        self._instance.clear()

    def size(self) -> int:
        return len(self._instance)

    @staticmethod
    def extract_points_from_raw_instance(instance: DoublyConnectedSimplePolygon) -> list[Point]:
        return [vertex.point for vertex in instance.vertices()]

    @property
    def default_number_of_random_points(self) -> int:
        return 100

    def generate_random_points(self, max_x: float, max_y: float, number: int) -> list[Point]:
        while True:
            points = super().generate_random_points(max_x, max_y, number)

            try:
                polygon = DoublyConnectedSimplePolygon.try_from_unordered_points(points)
            except Exception:
                continue

            return self.extract_points_from_raw_instance(polygon)


class DCELInstance(InstanceHandle[DoublyConnectedEdgeList]):
    def __init__(self, drawing_mode: Optional[DrawingMode] = None, drawing_epsilon: float = 5):
        if drawing_mode is None:
            drawing_mode = DCELMode(vertex_radius = 3)
        self._drawing_epsilon = drawing_epsilon
        self._last_added_point = None
        self._dcel = self._instance  # This is so that that DCELInstance can be used by the PointLocationInstance where the dcel is not the instance itself
        super().__init__(DoublyConnectedEdgeList(), drawing_mode)

    def add_point(self, point: Point) -> bool:
        # Check if point is already in the DCEL
        is_new_point = True
        for instance_point in self._dcel.points:
            if instance_point.close_to(point, epsilon = self._drawing_epsilon):
                is_new_point = False
                point = instance_point
                break

        # Add point (if necessary)
        if is_new_point:
            if isinstance(point, PointReference):
                self._dcel.add_vertex(point.container[point.position])
                # Add edges from Point-Reference-Container
                for i, neighbor in enumerate(point.container):
                    if i == point.position:
                        continue
                    if neighbor not in [vertex.point for vertex in self._dcel.vertices]:
                        continue
                    found = False
                    for edge in self._dcel.edges:
                        if edge.origin == point and edge.destination == neighbor:
                            found = True
                            break
                    if not found:
                        self._dcel.add_edge_by_points(point, neighbor)
            else:
                self._dcel.add_vertex(point)

        # Add edge from last clicked point
        if self._last_added_point is not None and self._last_added_point != point:
            self._dcel.add_edge_by_points(self._last_added_point, point)
            point = PointReference([point, self._last_added_point], 0)
            self._last_added_point = None
        elif not is_new_point:
            self._last_added_point = point

        return is_new_point, point

    def clear(self):
        self._instance.clear()
        self._last_added_point = None

    def size(self) -> int:
        return self._dcel.number_of_vertices

    @staticmethod
    def extract_points_from_raw_instance(instance: DoublyConnectedEdgeList) -> list[PointReference]:
        point_list: list[PointReference] = []
        for vertex in instance.vertices:
            neighbors: list[Point] = [vertex.point]  # start with the point itself in the list
            if vertex.edge.destination != vertex:  # at least one neighbor
                neighbors.append(vertex.edge.destination.point)
                edge = vertex.edge.twin.next
                while edge != vertex.edge:  # iterate over all neighbors
                    neighbors.append(edge.destination.point)
                    edge = edge.twin.next
            point_list.append(PointReference(neighbors, 0))
        return point_list

    @property
    def default_number_of_random_points(self) -> int:
        return 20
    
    def generate_random_points(self, max_x: float, max_y: float, number: int, min_distance = None) -> list[PointReference]:
        while True:
            # grid pattern with min distance up/down and left/right = 1
            if min_distance is None:
                min_distance = self._drawing_epsilon
            points = super().generate_random_points(max_x/min_distance, max_y/min_distance, number)

            points = [Point(np.round(point.x, 0), np.round(point.y, 0)) for point in points]
            points = [Point(point.x*min_distance, point.y*min_distance) for point in points]

            if len(points) != len(set(points)):  # Duplicate point(s)
                continue

            # 2-OPT path as in DCSP
            path = list(points)
            n = len(path)
            found_improvement = True
            while found_improvement:
                found_improvement = False
                for i in range(0, n - 1):
                    for j in range(i + 1, n):
                        subpath_distances = path[i].distance(path[j]) + path[i + 1].distance(path[(j + 1) % n])
                        neighbour_distances = path[i].distance(path[i + 1]) + path[j].distance(path[(j + 1) % n])
                        if subpath_distances < neighbour_distances:
                            path[i + 1:j + 1] = reversed(path[i + 1:j + 1])
                            found_improvement = True
                        #print("loop end")
            
            circle = [(i, i + 1) for i in range(n - 1)]
            if len(circle) > 1:
                circle.append((n - 1, 0))
            try:
                dcel = DoublyConnectedEdgeList(path, circle)
            except Exception():
                continue

            # Add some more edges:
            count = 0
            first  = np.int32(np.random.uniform(0, dcel.number_of_vertices, 1000))
            second = np.int32(np.random.uniform(0, dcel.number_of_vertices, 1000))
            tuple = zip(first, second)
            for tuple in zip(first, second):
                try:
                    if dcel.add_edge(tuple, True):
                        count = count + 1
                        if count >= number / 5:
                            break
                except (RuntimeError, Exception):
                    continue

            return self.extract_points_from_raw_instance(dcel)

class PointLocationInstance(DCELInstance, InstanceHandle[PointLocation]):
    def __init__(self, drawing_mode: Optional[DrawingMode] = None, drawing_epsilon: float = 5, random_seed: Optional[int] = None):
        if drawing_mode is None:
            drawing_mode = DCELMode(vertex_radius = 3)
        self._drawing_mode = drawing_mode
        self._drawing_epsilon = drawing_epsilon
        self._last_added_point = None
        self._instance = PointLocation(random_seed=random_seed)
        self._dcel = self._instance._dcel

    @staticmethod
    def extract_points_from_raw_instance(instance: Union[DoublyConnectedEdgeList, PointLocation]) -> list[PointReference]:
        if isinstance(instance, DoublyConnectedEdgeList):
            return DCELInstance.extract_points_from_raw_instance(instance)
        else:
            return DCELInstance.extract_points_from_raw_instance(instance._dcel)