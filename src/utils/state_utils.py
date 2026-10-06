import random
from ..models.package import Package
from ..models.state import State
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation

# 6 kemungkinan orientasi paket
ORIENTATIONS = [
    ("w", "l", "h"), ("w", "h", "l"), ("l", "w", "h"),
    ("l", "h", "w"), ("h", "w", "l"), ("h", "l", "w"),
]

# orientasi random
def random_orientation(rng):
    w, l, h = rng.choice(ORIENTATIONS)
    return Orientation((w, l, h))

# random state awal
def random_initial_state(package, truck, seed=None):
    rng = random.Random(seed)
    new_packages = []
    for p in package:
        q = Package(
            id=p.id,
            dimension=Dimension(p.dimension.w, p.dimension.l, p.dimension.h),
            orientation=random_orientation(rng),
            value=p.value,
            weight=p.weight,
            is_fragile=p.is_fragile,
            eta=p.eta,
        )
        dim_w, dim_l, dim_h = q.dimension.get_dimensions(q.orientation.orientation)
        x = rng.randint(0, max(0, truck.dimension.w - dim_w))
        y = rng.randint(0, max(0, truck.dimension.l - dim_l))
        z = rng.randint(0, max(0, truck.dimension.h - dim_h))
        q.place(x, y, z)
        new_packages.append(q)
    return State(new_packages, truck)