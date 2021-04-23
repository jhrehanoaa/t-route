#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 21:49:26 2021

@author: Camaron.George
"""
import glob
import numpy as np
import netCDF4 as nc
import os
cwd = os.getcwd()
cwd = cwd + "/coastal_download"

area = 'EastGulf'
storm = 'Michael'
length = 'medium'
tstep = 3600.0*3

path = '/home/jacob.hreha/github/troute/t-route/notebooks/coastal_download/'
idPath = '/home/jacob.hreha/github/troute/t-route/notebooks/coastal_download/'

soelems = []
soids = []
sielems = []
siids = []
import pdb; pdb.set_trace()
with open(idPath+'nwmReaches.csv') as f:
    nso = int(f.readline())
    for i in range(nso):
        line = f.readline()
        soelems.append(int(line.split()[0]))
        soids.append(int(line.split()[1]))
    next(f)
    nsi = int(f.readline())
    for i in range(nsi):
        line = f.readline()
        sielems.append(int(line.split()[0]))
        siids.append(int(line.split()[1]))

rows = len(glob.glob(path+'nwm*channel*'))
vsource = np.zeros((rows,len(soids)))
vsink = np.zeros((rows,len(siids)))

file = glob.glob(path+'*analysis*channel*')
data = nc.Dataset(file[0],'r')

featureID = data.variables['feature_id'][:]
streamflow = data.variables['streamflow'][:]

source = []
for i in soids:
    source.append(np.where(featureID == i)[0][0])

vsource[0,:] = streamflow.data[source]

sink = []
for i in siids:
    sink.append(np.where(featureID == i)[0][0])

vsink[0,:] = streamflow.data[sink]

files = glob.glob(path+'nwm*'+length+'*channel*')
files.sort()
row = 1
for file in files:

    data = nc.Dataset(file,'r')

    streamflow = data.variables['streamflow'][:]

    vsource[row,:] = streamflow.data[source]
    vsink[row,:] = streamflow.data[sink]
    row+=1

I = np.where(vsource == -999900.0)
vsource = np.delete(vsource,I[1],axis=1)
soelems = np.delete(soelems,I[1])

I = np.where(vsink == -999900.0)
vsink = np.delete(vsink,I[1],axis=1)
sielems = np.delete(sielems,I[1])

t = 0.0
o = open(idPath+'vsource.th','w')
for i in range(vsource.shape[0]):
    o.write(str(t)+'\t')
    for j in range(vsource.shape[1]):
        if j != vsource.shape[1]-1:
            o.write(str(vsource[i,j])+'\t')
        else:
            o.write(str(vsource[i,j])+'\n')
    t+=tstep
o.close()

t = 0.0
o = open(idPath+'vsink.th','w')
for i in range(vsink.shape[0]):
    o.write(str(t)+'\t')
    for j in range(vsink.shape[1]):
        if j != vsink.shape[1]-1:
            o.write(str(vsink[i,j])+'\t')
        else:
            o.write(str(vsink[i,j])+'\n')
    t+=tstep
o.close()

o = open(idPath+'source_sink.in','w')
o.write(str(len(soelems))+'\n')
for i in range(len(soelems)):
    o.write(str(soelems[i])+'\n')
o.write('\n'+'0'+'\n')
o.close()

t = 0
o = open(idPath+'msource.th','w')
for i in range(vsource.shape[0]):
    o.write(str(t)+'\t')
    for j in range(len(soelems)):
        o.write('-9999\t')
    for j in range(len(sielems)):
        if j != len(sielems)-1:
            o.write('0\t')
        else:
            o.write('0\n')
    t+=tstep
o.close()
