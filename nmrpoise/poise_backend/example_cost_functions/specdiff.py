def cost_function():
    """
    Obtains the distance between the current spectrum and a target spectrum.
    """
    target = get1d_real(epno=[1, 1])
    spec = get1d_real()
    return np.linalg.norm(target/np.linalg.norm(target) -
                          spec/np.linalg.norm(spec))
