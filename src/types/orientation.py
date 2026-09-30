from dataclasses import dataclass

@dataclass
class Orientation:
    # defaultnya masih sesuai dengan orientasinya masing2
    w: str = 'x'
    l: str = 'y'
    h: str = 'z'