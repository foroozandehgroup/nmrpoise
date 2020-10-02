"""
make_double_saltire.py
----------------------

Download from: https://git.io/JUHOZ

This script reads in a pulse duration (stored in us as P40) and bandwidth
(stored in Hz as CNST21), then creates a double saltire shaped file called
"auto_double_saltire" which can be directly used as the shaped file in
PSYCHE experiments.

This can be included in an AU programme using the line:

    XCMD("sendgui xpy make_double_saltire")

SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import division
from math import sin, cos, pi, sqrt, degrees, atan2


def make_double_saltire(duration, bandwidth):
    """
    Parameters
    ----------
    duration : float
        Time in units of seconds.

    bandwidth : float
        Bandwidth in units of Hz.

    Returns
    -------
    A : list of float
        Amplitudes, scaled between 0 and 100.
    phi : list of float
        Phases, in degrees between -180 and 180.

    These lists can be directly passed to the Bruker SAVE_SHAPE routine, as
    demonstrated in this script. The amplitude of the pulse should be
    automatically calculated in the pulse programme.
    """
    # Our strategy is to generate the first saltire first.

    # Number of points in half of the pulse. We use 1 point per us.
    npoints = int(duration * 1000000 / 2)
    # 20% smoothing.
    s = 0.2
    # This is equivalent to ls = np.linspace(0, 1, npoints), but you can't use
    # numpy in TopSpin...
    ts = [i/(npoints - 1) for i in range(0, npoints)]

    # Construct the amplitude piecewise function for a single chirp.
    A_chirp = [sin((pi * t) / (2 * s)) if t < s
               else 1 if s <= t and t <= 1 - s
               else sin((pi * (1 - t)) / (2 * s))
               for t in ts]
    # These are phases for a single chirp, not a saltire.
    phi_chirp = [pi * (duration/2) * bandwidth * ((t - 0.5) ** 2) for t in ts]
    # Calculate x-coefficients (Cx) for the saltire.
    Cx = [100 * a * cos(phi) for a, phi in zip(A_chirp, phi_chirp)]
    # The Cy's are 100 * a * sin(phi) ..., but that's only for one chirp. For a
    # saltire, the two component chirps have equal and opposite Cy's (because
    # sin(phi) = -sin(-phi)), so the total Cy is simply zero for every point.
    # In principle we could make a list full of zeroes, like Cy = [0 for _ in
    # range(npoints)], but that's a waste of memory and time.
    # Incidentally, the Cx's for both chirps add up since cos(phi) = cos(-phi),
    # but because the amplitudes are scaled to [0, 100], there's no point
    # actually adding them up.

    # Convert back to polar coordinates. Ordinarily A = sqrt(xi * xi + yi *
    # yi), but since all the yi's are zero, we just leave it out of the
    # equation.
    A = [sqrt(xi * xi) for xi in Cx]
    # Likewise here we use atan2(0, xi) instead of atan2(yi, xi).
    phi = [degrees(atan2(0, xi)) for xi in Cx]
    # Finally, we double the lists (because it's a double saltire).
    return A * 2, phi * 2


if __name__ == "__main__":
    # Let the user know what's going on
    SHOW_STATUS("make_double_saltire: generating saltire...")
    # Pulses are by default in us, so must convert first
    duration = float(GETPAR("P 40"))/1000000
    # Bandwidth is specified in Hz.
    bandwidth = float(GETPAR("CNST 21"))
    # Generate the amplitudes and phases.
    A, phi = make_double_saltire(duration, bandwidth)
    # Save it to disk.
    shape_name = "auto_double_saltire"
    SAVE_SHAPE(shape_name, "Excitation", A, phi)
    # Use it as SPNAM40. It's too easy to forget this!
    PUTPAR("SPNAM 40", shape_name)
