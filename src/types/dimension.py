from dataclasses import dataclass

@dataclass
class Dimension:
    w: int
    l: int
    h: int

    # dimensi hasil rotasi terhadap suatu sumbu
    def get_dimensions(self, orientation: tuple[str, str, str]) -> tuple[int, int, int]:
        dim = {'x': self.w, 'y': self.l, 'z': self.h}
        return (dim[orientation[0]], dim[orientation[1]], dim[orientation[2]])