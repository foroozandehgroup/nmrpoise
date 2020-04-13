def cost_function():
    f = getpar("SPOFFS2") + getpar("O1")   # frequency of selective pulse
    bw = 50.0                              # rough bandwidth of selective pulse
    sfo1 = getpar("SFO1")
    maxshift = (f + bw/2.0)/sfo1
    minshift = (f - bw/2.0)/sfo1
    return -abs(np.sum(get_real_spectrum(None, maxshift)) + np.sum(get_real_spectrum(minshift, None)))
