def cost_function():
    """
    Obtains the distance between the current spectrum and a target spectrum.
    """
    target = get_real_spectrum(epno=[1, 1])
    spec = get_real_spectrum()
    return np.linalg.norm(target/np.linalg.norm(target) -
                          spec/np.linalg.norm(spec))
