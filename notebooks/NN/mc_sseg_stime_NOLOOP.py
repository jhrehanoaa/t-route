from sys import traceback
debuglevel = 0
COMPILE = True
if COMPILE:
    try:
        import subprocess
        fortran_compile_call = []
        fortran_compile_call.append(r'f2py3')
        fortran_compile_call.append(r'-c')
        fortran_compile_call.append(r'MCsingleSegStime_f2py_NOLOOP.f90')
        fortran_compile_call.append(r'-m')
        fortran_compile_call.append(r'mc_sseg_stime_NOLOOP')
        if debuglevel <= -2:
            subprocess.run(fortran_compile_call)
        else:
            subprocess.run(fortran_compile_call, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import mc_sseg_stime_NOLOOP as mc
    except Exception as e:
        print (e)
        if debuglevel <= -1: traceback.print_exc()
else:
    import mc_sseg_stime_NOLOOP as mc

# # Method 1
# Python: time loop; segment loop; constant channel variables are passed to Fortran
# Fortran: Take constant variable values and then run MC for a single segment

def compute_mc_up2down_ReachbySegment():
    '''HANDLE LOOPING, 
        Then call single segment routine for each segment'''
    pass

def singlesegment(
        dt # dt
        , qup = None # qup
        , quc = None # quc
        , qdp = None # qdp
        , qlat = None # ql
        , dx = None # dx
        , bw = None # bw
        , tw = None # tw
        , twcc = None # twcc
        , n_manning = None #
        , n_manning_cc = None # ncc
        , cs = None # cs
        , s0 = None # s0
        , velp = None # velocity at previous time step
        , depthp = None # depth at previous time step
    ):

    # call Fortran routine
    return mc.muskingcungenwm(
        dt, qup, quc, qdp, qlat, dx, bw, tw, twcc
        ,n_manning, n_manning_cc, cs, s0, velp, depthp
    )
    #return qdc, vel, depth
        
def main ():

    dt = 60.0 # Time step
    dx = 1800.0 # segment length
    bw = 112.0 # Trapezoidal bottom width
    tw = 448.0 # Channel top width (at bankfull)
    twcc = 623.5999755859375 # Flood plain width
    n_manning = 0.02800000086426735 # manning roughness of channel
    n_manning_cc = 0.03136000037193298 # manning roughness of floodplain
    cs = 1.399999976158142 # channel trapezoidal sideslope
    s0 = 0.0017999999690800905 # downstream segment bed slope
    qlat = 40.0 # Lateral inflow in this time step
    qup = 0.04598825052380562 # Flow from the upstream neighbor in the previous timestep
    quc = 0.04598825052380562 # Flow from the upstream neighbor in the current timestep 
    qdp = 0.21487340331077576 # Flow at the current segment in the previous timestep
    velp = 0.070480190217494964 # Velocity in the current segment in the previous timestep NOT USED AS AN INPUT!!!
    depthp = 0.010033470578491688 # Depth at the current segment in the previous timestep

    qdc_expected = 0.7570106983184814
    velc_expected = 0.12373604625463486
    depthc_expected = 0.02334451675415039

    #run M-C model
    qdc, velc, depthc = singlesegment(
        dt = dt
        , qup = qup
        , quc = quc
        , qdp = qdp
        , qlat = qlat
        , dx = dx
        , bw = bw
        , tw = tw
        , twcc = twcc
        , n_manning = n_manning
        , n_manning_cc = n_manning_cc
        , cs = cs
        , s0 = s0
        , velp = velp
        , depthp = depthp
    )
    print('computed q: {} vel: {} depth: {}'.format(qdc, velc, depthc))
    print('expected q: {} vel: {} depth: {}'.format(qdc_expected, velc_expected, depthc_expected))
            
if __name__ == '__main__':
    main()
