def cost_function():
    r = get_real_spectrum()
    i = get_imag_spectrum()
    return np.sum(np.abs(r + 1j*i))
