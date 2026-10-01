from dataclasses import dataclass

@dataclass
class Dimension:
    w: int
    l: int
    h: int

    # dimensi hasil rotasi terhadap suatu sumbu
    def get_dimensions(self, orientation: tuple[str, str, str]) -> tuple[int, int, int]:
        dim = {'w': self.w, 'l': self.l, 'h': self.h}
        return (dim[orientation[0]], dim[orientation[1]], dim[orientation[2]])

    # menghitung volume
    def volume(self) -> int:
        return self.w * self.l * self.h