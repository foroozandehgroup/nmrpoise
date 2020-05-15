# Instructions

Just define a Python function named `cost_function()` to return the value you want it to, as a float!

Some builtin methods are available:

 - `getpar(param)`: takes a string and returns the value of the parameter as a float.

 - `get_real_spectrum()`: returns a real spectrum as a numpy array of size SI. Takes two arguments, `left` and `right`, to specify a particular region of the spectrum of interest. For example:

   - `get_real_spectrum()` or `get_real_spectrum(left=None, right=None)` returns the entire spectrum
   - `get_real_spectrum(left=6.21, right=None)` returns the part of the spectrum with shift <= 6.21 (i.e. the spectrum is left-bounded by 6.21 ppm).
   - `get_real_spectrum(left=None, right=6.21)` returns the part of the spectrum with shift >= 6.21.
   - `get_real_spectrum(left=6.21, right=4)` returns the part of the spectrum between 6.21 and 4 ppm.

   By default, this returns the spectrum on which the optimisation is being run. You can specify a spectrum with the same name, but with a different EXPNO and PROCNO using the parameter `epno`:

   - `get_real_spectrum(epno=[1,999])` returns the real spectrum with EXPNO 1 and PROCNO 999.
   - `get_real_spectrum(left=6.21, right=4, epno=[1,999])` returns the part between 6.21 and 4 ppm of the real spectrum with EXPNO 1 and PROCNO 999.

 - `get_imag_spectrum()` does the same for the imaginary spectrum.
 - `get_fid()` returns the complex-valued FID as a numpy array of size TD/2.

For example, the following code is used in `minrealint.py`:

     def cost_function():
         return np.sum(get_real_spectrum())

This cost function simply returns the sum of all points in the real spectrum, which is a quick measure of the spectral intensity (as long as the spectrum is phased and baseline corrected; this is the role of the acquisition AU programme). Since optimisations always seek to *minimise* the cost function, using this cost function will result in `poptpy` trying to *minimise* the intensity of the spectrum. This is useful for e.g. calibrating a 360-degree pulse (although `minabsint.py` tends to perform slightly better).
