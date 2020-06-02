subroutine muskingcungenwm(dt, qup, quc, qdp, ql, dx, bw, tw, twcc,&
    n, ncc, cs, s0, velp, depthp, qdc, velc, depthc)

    !* exactly follows SUBMUSKINGCUNGE in NWM:
    !* 1) qup and quc for a reach in upstream limit take zero values all the time
    !* 2) initial value of depth of time t of each reach is equal to the value at time t-1
    !* 3) qup as well as quc at time t for a downstream reach in a serial network takes
    !*    exactly the same value qdp at time t (or qdc at time t-1) for the upstream reach

    implicit none
    real, intent(in) :: dt 
    real, intent(in) :: qup, quc, qdp, ql
    real, intent(in) :: dx, bw, tw, twcc, n, ncc, cs, s0
    real, intent(in) :: velp, depthp
    real, intent(out) :: qdc, velc, depthc
    real :: z
    real :: bfd, WPC, AREAC, C1, C2, C3, C4
    integer :: iter
    integer :: maxiter, tries
    real :: mindepth, aerror, rerror
    real :: R, twl, h_1, h, h_0, Qj, Qj_0

    ! qdc = 0.0
    ! velc = velp
    ! depthc = depthp

    !* parameters of Secant method
    maxiter  = 100
    mindepth = 0.01

    aerror = 0.01
    rerror = 1.0
    tries = 0

    if(cs .eq. 0.00000000) then
        z = 1.0
    else
        z = 1.0/cs          !channel side distance (m)
    endif

    if(bw .gt. tw) then   !effectively infinite deep bankful
        bfd = bw/0.00001
    elseif (bw .eq. tw) then
        bfd =  bw/(2.0*z)  !bankfull depth is effectively
    else
        bfd =  (tw - bw)/(2.0*z)  !bankfull depth (m)
    endif

    if (n .le. 0.0 .or. s0 .le. 0.0 .or. z .le. 0.0 .or. bw .le. 0.0) then
        !print*, "Error in channel coefficients -> Muskingum cunge", n, s0, z, bw
        !call hydro_stop("In MUSKINGCUNGE() - Error in channel coefficients")
    end if

    depthc = max(depthp, 0.0)
    h     = (depthc * 1.33) + mindepth !1.50 of  depthc
    h_0   = (depthc * 0.67)            !0.50 of depthc

    if(ql .gt. 0.0 .or. qup .gt. 0.0 .or. qdp .gt. 0.0) then  !only solve if there's water to flux
110 continue
        Qj_0 = 0.0
        WPC = 0.0
        AREAC = 0.0
        iter = 0

        do while (rerror .gt. 0.01 .and. aerror .ge. mindepth .and. iter .le. maxiter)

            call secant_h0(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
                qdp, ql, qup, quc, h_0, Qj_0, C1, C2, C3, C4)
      !subroutine secant_h0(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
                !qdp, ql, qup, quc, h_0, Qj_0)

            call secant_h(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
                qdp, ql, qup, quc, h, Qj, C1, C2, C3, C4)
      !subroutine secant_h(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
                !qdp, ql, qup, quc, h, Qj)

            if(Qj_0-Qj .ne. 0.0) then
                h_1 = h - ((Qj * (h_0 - h))/(Qj_0 - Qj)) !update h, 3rd estimate

                if(h_1 .lt. 0.0) then
                    h_1 = h
                endif
            else
                h_1 = h
            endif

            if(h .gt. 0.0) then
                rerror = abs((h_1 - h)/h) !relative error is new estimate and 2nd estimate
                aerror = abs(h_1 -h)      !absolute error
            else
                rerror = 0.0
                aerror = 0.9
            endif

            h_0  = max(0.0,h)
            h    = max(0.0,h_1)
            iter = iter + 1
                        !write(41,"(3i5,2x,8f15.4)") k, i, iter, dmy1, Qj_0, dmy2, Qj, h_0, h, rerror, aerror
                        !write(42,*) k, i, iter, dmy1, Qj_0, dmy2, Qj, h_0, h, rerror, aerror
            if( h .lt. mindepth) then  ! exit loop if depth is very small
                goto 111
            endif
        end do !*do while (rerror .gt. 0.01 .and. ....
111    continue

        if(iter .ge. maxiter) then
            tries = tries + 1

            if(tries .le. 4) then  ! expand the search space
                h     =  h * 1.33
                h_0   =  h_0 * 0.67
                maxiter = maxiter + 25 !and increase the number of allowable iterations
                goto 110
            endif
                    !print*, "Musk Cunge WARNING: Failure to converge"
                    !print*, 'RouteLink index:', idx + linkls_s(my_id+1) - 1
                    !print*, "id,err,iters,tries",PC*ncc))/(WP+WPC))) * &
                    !        (AREA+AREAC) * (R**(2./3.)) * sqrt(s0)) idx, rerror, iter, tries
                    !print*, "Ck,X,dt,Km",Ck,X,dt,Km
                    !print*, "s0,dx,h",s0,dx,h
                    !print*, "qup,quc,qdp,ql", qup,quc,qdp,ql
                    !print*, "bfd,bw,tw,twl", bfd,bw,tw,twl
                    !print*, "Qmc,Qmn", (C1*qup)+(C2*quc)+(C3*qdp) + C4,((1/(((WP*n)+(WPC*ncc))/(WP+WPC))) * &
                    !        (AREA+AREAC) * (R**(2./3.)) * sqrt(s0))
        endif

        !*yw added for test
        !*DY and LKR Added to update for channel loss
        if(((C1*qup)+(C2*quc)+(C3*qdp) + C4) .lt. 0.0) then
            if( (C4 .lt. 0.0) .and. (abs(C4) .gt. (C1*qup)+(C2*quc)+(C3*qdp)) )  then ! channel loss greater than water in chan
                qdc = 0.0
                !qdc = -111.1
            else
                qdc = MAX( ( (C1*qup)+(C2*quc) + C4),((C1*qup)+(C3*qdp) + C4) )
                !qdc = -222.2
            endif
        else
            qdc = ((C1*qup)+(C2*quc)+(C3*qdp) + C4) !-- pg 295 Bedient huber
            !write(*,*)"C1", C1, "qup", qup, "C2", C2, "quc", quc, "C3", C3, "qdp", qdp, "C4", C4
            !qdc = -333.3
        endif

        twl = bw + (2.0*z*h)
        R = (h*(bw + twl) / 2.0) / (bw + 2.0*(((twl - bw) / 2.0)**2.0 + h**2)**0.5)
        velc = (1./n) * (R **(2.0/3.0)) * sqrt(s0)  !*average velocity in m/s
        depthc = h
    else   !*no flow to route
        qdc = 0.0
        !qdc = -444.4
        depthc = 0.0
    end if !*if(ql .gt. 0.0 .or. ...

end subroutine muskingcungenwm
!**---------------------------------------------------**!
!*                                                     *!
!*                  NEXT SUBROUTINE                    *!
!*                                                     *!
!**---------------------------------------------------**!
subroutine secant_h0(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
    qdp, ql, qup, quc, h_0, Qj_0, C1, C2, C3, C4)

    implicit none

    real, intent(in) :: z, bw, bfd, twcc, s0, n, ncc
    real, intent(in) :: dt, dx
    real, intent(in) :: qdp, ql, qup, quc
    real, intent(in) :: h_0  !, refQj_0
    real, intent(out) :: Qj_0, C1, C2, C3, C4
    real :: twl, AREA, AREAC, WP, WPC, R, Ck, Km, X, D

    !**top surface water width of the channel inflow
    twl = bw + 2.0*z*h_0

    !**hydraulic radius, R
    if(h_0 .gt. bfd) then !**water outside of defined channel
        AREA =  (bw + bfd * z) * bfd
        AREAC = (twcc * (h_0 -bfd)) !**assume compound component is rect. chan, that's 3 times the tw
        WP = (bw + 2.0 * bfd * sqrt(1.0 + z*z))
        WPC = twcc + (2.0 * (h_0-bfd)) !**WPC is 2 times the tw
        R   = (AREA + AREAC)/(WP +WPC)  !**hydraulic radius
        !print *, "warning: compound channel activated", h_0, bfd
    else
        AREA = (bw + h_0 * z ) * h_0
        WP = (bw + 2.0 * h_0 * sqrt(1.0 + z*z))
        WPC = 0.0
        if(WP .gt. 0.0) then
            R = AREA/ WP
        else
            R = 0.0
        endif
    endif

    !**kinematic celerity, c
    if(h_0 .gt. bfd) then
    !*water outside of defined channel weight the celerity by the contributing area, and
    !*assume that the mannings of the spills is 2x the manning of the channel
        Ck = max(0.0,((sqrt(s0)/n)*((5./3.)*R**(2./3.) - &
            ((2./3.)*R**(5./3.)*(2.0*sqrt(1.0 + z*z)/(bw+2.0*bfd*z))))*AREA &
            + ((sqrt(s0)/(ncc))*(5./3.)*(h_0-bfd)**(2./3.))*AREAC)/(AREA+AREAC))
    else
        if(h_0 .gt. 0.0) then
            Ck = max(0.0,(sqrt(s0)/n)*((5./3.)*R**(2./3.) - &
                ((2./3.)*R**(5./3.)*(2.0*sqrt(1.0 + z*z)/(bw+2.0*h_0*z)))))
        else
            Ck = 0.0
        endif
    endif

    !**MC parameter, K
    if(Ck .gt. 0.000000) then
        Km = max(dt,dx/Ck)
    else
        Km = dt
    endif

    !**MC parameter, X
    if(h_0 .gt. bfd) then !water outside of defined channel
        X = min(0.5,max(0.0,0.5*(1-(Qj_0/(2.0*twcc*s0*Ck*dx)))))
        !X = min(0.5,max(0.0,0.5*(1-(refQj_0/(twcc*s0*Ck*dx)))))
    else
        if(Ck .gt. 0.0) then
            X = min(0.5,max(0.0,0.5*(1-(Qj_0/(2.0*twl*s0*Ck*dx)))))
            !X = min(0.5,max(0.0,0.5*(1-(refQj_0/(twl*s0*Ck*dx)))))
        else
            X = 0.5
        endif
    endif

    !write(45,"(3i5,2x,4f10.3)") gk, gi, idx, h_0, Ck, Km, X
    D = (Km*(1.000 - X) + dt/2.0000)              !--seconds
    if(D .eq. 0.0) then
        !print *, "FATAL ERROR: D is 0 in MUSKINGCUNGE", Km, X, dt,D
        !call hydro_stop("In MUSKINGCUNGE() - D is 0.")
    endif

    C1 =  (Km*X + dt/2.000000)/D
    C2 =  (dt/2.0000 - Km*X)/D
    C3 =  (Km*(1.00000000-X)-dt/2.000000)/D
    C4 =  (ql*dt)/D

    if((WP+WPC) .gt. 0.0) then  !avoid divide by zero
        Qj_0 =  ((C1*qup)+(C2*quc)+(C3*qdp) + C4) - ((1/(((WP*n)+(WPC*ncc))/(WP+WPC))) * &
                (AREA+AREAC) * (R**(2./3.)) * sqrt(s0)) !f0(x)
    endif

end subroutine secant_h0
!**---------------------------------------------------**!
!*                                                     *!
!*                  NEXT SUBROUTINE                    *!
!*                                                     *!
!**---------------------------------------------------**!
subroutine secant_h(z, bw, bfd, twcc, s0, n, ncc, dt, dx, &
    qdp, ql, qup, quc, h, Qj, C1, C2, C3, C4)

    implicit none

    real, intent(in) :: z, bw, bfd, twcc, s0, n, ncc
    real, intent(in) :: dt, dx
    real, intent(in) :: qdp, ql, qup, quc
    real, intent(in) :: h
    real, intent(out) :: Qj, C1, C2, C3, C4
    real :: twl, AREA, AREAC, WP, WPC, R, Ck, Km, X, D

    !--upper interval -----------
    twl = bw + 2.0*z*h  !--top width of the channel inflow

    if(h .gt. bfd) then !water outside of defined channel
        AREA =  (bw + bfd * z) * bfd
        AREAC = (twcc * (h-bfd)) !assume compound component is rect. chan, that's 3 times the tw
        WP = (bw + 2.0 * bfd * sqrt(1.0 + z*z))
        WPC = twcc + (2.0*(h-bfd)) !the additional wetted perimeter
        R   = (AREA + AREAC)/(WP +WPC)
        !print *, "warning: compound channel activated", h, bfd
    else
        AREA = (bw + h * z ) * h
        WP = (bw + 2.0 * h * sqrt(1.000000 + z*z))
        WPC = 0.0
        if(WP .gt. 0.0) then
            R = AREA/WP
        else
            R = 0.0
        endif
    endif

    if(h .gt. bfd) then !water outside of defined channel, assumed rectangular, 3x TW and n = 3x
        Ck = max(0.0,((sqrt(s0)/n)*((5./3.)*R**(2./3.) - &
            ((2./3.)*R**(5./3.)*(2.0*sqrt(1.0 + z*z)/(bw + 2.0*bfd*z))))*AREA &
            + ((sqrt(s0)/(ncc))*(5./3.)*(h-bfd)**(2./3.))*AREAC)/(AREA+AREAC))
    else
        if(h .gt. 0.0) then !avoid divide by zero
            Ck = max(0.0,(sqrt(s0)/n)*((5./3.)*R**(2./3.) - &
                ((2./3.)*R**(5./3.)*(2.0 * sqrt(1.0 + z*z)/(bw + 2.0*h*z)))))
        else
            Ck = 0.0
        endif
    endif

    if(Ck .gt. 0.0) then
        Km = max(dt,dx/Ck)
    else
        Km = dt
    endif

    if(h .gt. bfd) then !water outside of defined channel
        X = min(0.5,max(0.25,0.5*(1-(((C1*qup)+(C2*quc)+(C3*qdp) + C4)/(2*twcc*s0*Ck*dx)))))
    else
        if(Ck .gt. 0.0) then
            X = min(0.5,max(0.25,0.5*(1-(((C1*qup)+(C2*quc)+(C3*qdp) + C4)/(2*twl*s0*Ck*dx)))))
        else
            X = 0.5
        endif
    endif

    !write(45,"(3i5,2x,4f10.3)") gk, gi, idx, h, Ck, Km, X
    D = (Km*(1 - X) + dt/2)              !--seconds
    if(D .eq. 0.0) then
        !print *, "FATAL ERROR: D is 0 in MUSKINGCUNGE", Km, X, dt,D
        !call hydro_stop("In MUSKINGCUNGE() - D is 0.")
    endif

    C1 =  (Km*X + dt/2.000000)/D
    C2 =  (dt/2.000000 - Km*X)/D
    C3 =  (Km*(1.000000-X)-dt/2.000000)/D
    C4 =  (ql*dt)/D

    if( (C4 .lt. 0.0) .and. (abs(C4) .gt. (C1*qup)+(C2*quc)+(C3*qdp)))  then
        C4 = -((C1*qup)+(C2*quc)+(C3*qdp))
    endif

    if((WP+WPC) .gt. 0.0) then
        Qj =  ((C1*qup)+(C2*quc)+(C3*qdp) + C4) - ((1.0000000/(((WP*n)+(WPC*ncc))/(WP+WPC))) * &
                (AREA+AREAC) * (R**(2./3.)) * sqrt(s0)) !f(x)
    endif

end subroutine secant_h

