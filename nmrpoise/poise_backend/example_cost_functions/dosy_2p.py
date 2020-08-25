def cost_function():
    target = get1d_real(epno=[99998, 1])
    spec = get1d_real()
    # optimise to 25% signal left
    return np.abs(np.sum(spec)/np.sum(target) - 0.25) + getpar("D20")
