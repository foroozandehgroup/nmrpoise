# Edit cf_function() to return the value you want it to, as a float.
# Some builtin methods are available:
#  - getpar(param)       takes a string and returns the value of the
#                        parameter as a float.
#  - get_real_spectrum() returns the real spectrum as a numpy array
#                        of size SI. You can pass two arguments, "left"
#                        and "right", to specify a particular region
#                        of the spectrum of interest.
#           For example:
#           - get_real_spectrum() OR get_real_spectrum(None, None)
#             return the entire spectrum.
#           - get_real_spectrum(6.21, None)
#             returns the part of the spectrum with shift <= 6.21
#             (i.e. the spectrum is left-bounded by 6.21 ppm).
#           - get_real_spectrum(None, 6.21)
#             returns the part of the spectrum with shift >= 6.21.
#           - get_real_spectrum(6.21, 4)
#             returns the part of the spectrum between 6.21 and 4 ppm.
#
#  - get_imag_spectrum() does the same for the imaginary spectrum.
#  - get_fid()           returns the complex-valued FID as a numpy
#                        array of size TD/2.

# In this short example, we simply sum the intensities at each point
# of the real spectrum. This gives us a quick and easy measure of the
# total signal intensity (as long as the spectrum is correctly phased).

def cf_function():
    return np.sum(get_real_spectrum())
