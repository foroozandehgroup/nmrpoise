def cost_function():
    target = get1d_real(epno=[99998, 1])
    spec = get1d_real()
    # no np.abs, if this is <0 then it's good, if this is
    # >0 that means that even at gpz1=80% it's not enough
    # attenuation.
    return np.sum(spec)/np.sum(target) - 0.25
