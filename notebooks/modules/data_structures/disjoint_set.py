from typing import TypeVar, Generic

T = TypeVar('T')

class DisjointSet(Generic[T]):
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def make_set(self, x: T):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0

    def find(self, x: T) -> T:
        if x != self.parent[x]:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x: T, y: T):
        if x not in self.parent:  # Efficient, as python dicts are hash tables
            self.make_set(x)
        if y not in self.parent:
            self.make_set(y)
        
        rep_x = self.find(x)
        rep_y = self.find(y)

        if rep_x != rep_y:
            if self.rank[rep_x] < self.rank[rep_y]:
                self.parent[rep_x] = rep_y
            else:  # >=
                self.parent[rep_y] = rep_x
            if self.rank[rep_x] == self.rank[rep_y]:
                self.rank[rep_x] += 1

    def contains(self, x: T) -> bool:
        return x in self.parent
    
    def in_same_set(self, x: T, y: T) -> bool:
        return self.find(x) == self.find(y)