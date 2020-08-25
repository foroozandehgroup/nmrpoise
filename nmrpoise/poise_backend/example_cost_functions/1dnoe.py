def cost_function():
    f = getpar("SPOFFS2") + getpar("O1")   # frequency of selective pulse
    bw = 50.0                              # rough bandwidth of selective pulse
    sfo1 = getpar("SFO1")
    upperhalf = f"{(f + bw/2)/sfo1:.3f}.."
    lowerhalf = f"..{(f - bw/2)/sfo1:.3f}"
    return -abs(np.sum(get1d_real(bounds=upperhalf)) +
                np.sum(get1d_real(bounds=lowerhalf)))
