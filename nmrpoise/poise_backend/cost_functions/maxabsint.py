def cost_function():
    r = get1d_real()
    i = get1d_imag()
    return -np.sum(np.abs(r + 1j*i))
