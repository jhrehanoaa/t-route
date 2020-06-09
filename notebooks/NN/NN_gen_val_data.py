import numpy as np
import sys;sys.path.append(r'../fortran_routing/mc_pylink_v00/MC_singleSeg_singleTS')
import mc_sseg_stime_NOLOOP as mc
import itertools
import NN_normalization

def main():

    num_samp = 1000000
    dt = 60 # Time step
    dx = 1800 # segment length
    # bw = np.linspace(0.135, 230.035, array_length, endpoint=True) # Trapezoidal bottom width
    bw = np.random.uniform(bw_min, bw_max, num_samp) # Trapezoidal bottom width
    tw = np.random.uniform(tw_min, tw_max, num_samp) # Channel top width (at bankfull)
    # twcc = np.linspace(0.67, 1150.17, array_length, endpoint=True) # Flood plain width
    # twcc = tw*  # Flood plain width tw*3
    n_manning = .028   # manning roughness of channel
    n_manning_cc = .028 # manning roughness of floodplain
    cs = np.random.uniform(cs_min,cs_max, num_samp)# channel trapezoidal sideslope
    s0 = np.random.uniform(s0_min, s0_max, num_samp) # Lateral inflow in this time step
    qup = np.random.uniform(qup_min, qup_max, num_samp) # Flow from the upstream neighbor in the previous timestep
    # quc = np.linsprandom.uniformace(10, 1000, array_length, endpoint=True) # Flow from the upstream neighbor in the current timestep 
    quc = np.random.uniform(quc_min, quc_max, num_samp)  # Flow from the upstream neighbor in the current timestep 
    # qdp = np.linspace(10, 1000, array_length, endpoint=True) # Flow at the current segment in the previous timestep
    qdp = np.random.uniform(qdp_min, qdp_max, num_samp)  # Flow at the current segment in the previous timestep
    qlat = np.random.uniform(qlat_min, qlat_max, num_samp) # lat inflow into current segment in the current timestep
    velp = .5  # Velocity in the current segment in the previous timestep NOT USED AS AN INPUT!!!
    depthp = np.random.uniform(depthp_min ,depthp_max , num_samp) # D

    VAL_x = []
    VAL_y = []
    for i in range(num_samp):
        VAL_x.append( [normalize(qup[i],qup_max,qup_min), 
        normalize(quc[i],quc_max,quc_min), 
        normalize(qlat[i],qlat_max,qlat_min),
        normalize(qdp[i],qdp_max,qdp_min),
        # dx,  
        normalize(bw[i],bw_max,bw_min),
        normalize(tw[i],tw_max,tw_min),
        # normalize(tw[tw_o]*3,tw_max,tw_min),
        # n_manning, 
        # n_manning_cc, 
        normalize(cs[i],cs_max,cs_min),
        normalize(s0[i], s0_max, s0_min),
        # velp, 
        normalize(depthp[i],depthp_max,depthp_min)])
        S = singlesegment(
                                    dt=dt,
                                    qup=qup[i],
                                    quc=quc[i],
                                    qlat=qlat[i],
                                    qdp=qdp[i],
                                    
                                    dx=dx ,
                                    bw=bw[i],
                                    tw=tw[i],
                                    twcc=tw[i]*3,
                                    n_manning=n_manning,
                                    n_manning_cc=n_manning_cc,
                                    cs=cs[i],
                                    s0=s0[i],
                                    velp=velp,
                                    depthp=depthp[i])*1000
        VAL_y.append(S[0])
    VAL_x = np.array(VAL_x)
    VAL_y = np.array(VAL_y)
