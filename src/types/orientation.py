from dataclasses import dataclass

@dataclass
class Orientation:
    orientation: tuple[str, str, str] = ("w", "l", "h")

    # rotasi 90 derajat terhadap sumbu x
    def rotate_x(self) -> Orientation:
        return Orientation((self.orientation[0], self.orientation[2], self.orientation[1]))

    # rotasi 90 derajat terhadap sumbu y
    def rotate_y(self) -> Orientation:
        return Orientation((self.orientation[2], self.orientation[1], self.orientation[0]))

    # rotasi 90 derajat terhadap sumbu z
    def rotate_z(self) -> Orientation:
        return Orientation((self.orientation[1], self.orientation[0], self.orientation[2]))