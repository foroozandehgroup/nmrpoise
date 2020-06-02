def cost_function():
    target = get_real_spectrum(epno=[1, 1])
    spec = get_real_spectrum()
    return np.linalg.norm(target/np.linalg.norm(target) -
                          spec/np.linalg.norm(spec))
