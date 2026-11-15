"""Earth gravity: point mass plus J2 oblateness (ECI frame, z = rotation axis). Level 2."""
import numpy as np
from backend.core.constants import MU_EARTH, R_EARTH, J2
def accel_j2(r, use_j2=True):
    r = np.asarray(r, float); n = np.linalg.norm(r); a = -MU_EARTH * r / n**3
    if use_j2:
        k = 1.5 * J2 * MU_EARTH * R_EARTH**2 / n**5; z2 = (r[2] / n) ** 2
        a = a + k * np.array([r[0] * (5 * z2 - 1), r[1] * (5 * z2 - 1), r[2] * (5 * z2 - 3)])
    return a
