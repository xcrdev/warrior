'''
Created on May 30, 2011

@author: xavier
'''
#
# line segment intersection using vectors
# see Computer Graphics by F.S. Hill
#
from numpy import *
def perp( a ) :
    b = empty_like(a)
    b[0] = -a[1]
    b[1] = a[0]
    return b

# line segment a given by endpoints a1, a2
# line segment b given by endpoints b1, b2
# return 
def seg_intersect(a1,a2, b1,b2) :
    da = a2-a1
    db = b2-b1
    dp = a1-b1
    dap = perp(da)
    denom = dot( dap, db)
    num = dot( dap, dp )
    return (num / denom)*db + b1

p1 = array( [0.0, 0.0] )
p2 = array( [1.0, 0.0] )

p3 = array( [4.0, -5.0] )
p4 = array( [4.0, 2.0] )

print seg_intersect( p1,p2, p3,p4)

p1 = array( [2.0, 2.0] )
p2 = array( [4.0, 3.0] )

p3 = array( [6.0, 0.0] )
p4 = array( [6.0, 3.0] )

print seg_intersect( p1,p2, p3,p4)
