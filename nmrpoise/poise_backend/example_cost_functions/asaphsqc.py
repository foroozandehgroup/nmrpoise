def cost_function():
    spec = get2d_rr()
    proj = np.amax(spec, axis=0)
    return -np.sum(proj)
