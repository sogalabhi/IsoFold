import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import brentq
plt.rcParams.update({'font.family':'STIXGeneral','mathtext.fontset':'stix','font.size':13})
A0,s0=3.0,1.6; A1,s1,c1=2.3,1.2,-0.6
f0=lambda x:A0*np.exp(-x**2/(2*s0**2)); d0=lambda x:-x/s0**2*f0(x)
f1=lambda x:A1*np.exp(-x**2/(2*s1**2))+c1; d1=lambda x:-x/s1**2*(f1(x)-c1)
x=np.linspace(-4.2,4.2,600)
fig,ax=plt.subplots(figsize=(9,5.2))
ax.plot(x,f0(x),color='#b5462f',lw=3); ax.plot(x,f1(x),color='#2a74a8',lw=3)
al=np.radians(40); m=-np.tan(al)
xp=brentq(lambda t:d0(t)-m,0.01,s0); xq=brentq(lambda t:d1(t)-m,0.01,s1)
P=np.array([xp,f0(xp)]); Q=np.array([xq,f1(xq)])
# tangent lines
for X,c in ((P,'#1b7f5a'),(Q,'#1b7f5a')):
    tt=np.linspace(-0.9,0.9,2); u=np.array([1,m])/np.hypot(1,m)
    ax.plot(X[0]+tt*u[0]*1.6,X[1]+tt*u[1]*1.6,color=c,lw=1.3)
ax.plot(*zip(P,Q),color='#1b7f5a',lw=1.6,ls='--')
for X,l,dx,dy in ((P,'$p$',0.08,0.12),(Q,'$q$',-0.28,-0.25)):
    ax.plot(*X,'o',color='#1b7f5a',ms=6); ax.text(X[0]+dx,X[1]+dy,l,fontsize=15)
# hinge & axial trace
H=(0,f0(0)); G=(0,f1(0))
ax.plot([0,0],[G[1]-0.5,H[1]+0.5],color='#444',lw=1,ls=(0,(6,4)))
for X,l,dx in ((H,'$H$',-0.32),(G,'$G$',-0.32)):
    ax.plot(*X,'o',color='#222',ms=6); ax.text(X[0]+dx,X[1]+0.12,l,fontsize=15)
ax.text(0.1,H[1]+0.42,'axial trace',fontsize=12,color='#444')
# reference tangent at H and alpha arc
ax.plot([0,1.6],[H[1],H[1]],color='#222',lw=1)
ax.plot([P[0]-0.0,P[0]+1.2],[P[1],P[1]+1.2*m],color='#1b7f5a',lw=0)
ang=np.linspace(-al,0,30); r=1.1
ax.plot(r*np.cos(ang),H[1]+r*np.sin(ang),color='#222',lw=1)
ax.plot([0,1.45*np.cos(al)],[H[1],H[1]-1.45*np.sin(al)],color='#222',lw=0.8,ls=':')
ax.text(1.15,H[1]-0.42,r'$\alpha$',fontsize=15)
# t_alpha: perpendicular between the two parallel tangent lines, drawn from q
n=np.array([np.tan(al),1.0]); n/=np.linalg.norm(n)   # unit normal pointing up-right
dist=np.dot(P-Q,n); F=Q+dist*n
ax.annotate('',xy=F,xytext=Q,arrowprops=dict(arrowstyle='<->',color='#7a3e9d',lw=1.4))
ax.text((Q[0]+F[0])/2+0.12,(Q[1]+F[1])/2-0.05,r'$t_\alpha$',fontsize=15,color='#7a3e9d')
# T_alpha: vertical between the two tangent lines, at x = xq + 0.9
xx=Q[0]+1.05; yb=Q[1]+m*(xx-Q[0]); yt=P[1]+m*(xx-P[0])
ax.annotate('',xy=(xx,yt),xytext=(xx,yb),arrowprops=dict(arrowstyle='<->',color='#a06a00',lw=1.4))
ax.annotate(r'$T_\alpha$ (measured parallel to the axial trace)',xy=(xx+0.03,(yt+yb)/2),xytext=(2.35,2.55),fontsize=12,color='#a06a00',arrowprops=dict(arrowstyle='-',color='#a06a00',lw=0.8))
# inflection points (left limb)
for fx,sx,lab in ((f0,s0,'$I$'),(f1,s1,'$I$')):
    ax.plot(-sx,fx(-sx),'o',color='#8a6d00',ms=6); ax.text(-sx-0.3,fx(-sx)+0.05,lab,fontsize=15)
ax.text(-3.9,0.75,'limb',fontsize=13); ax.text(3.35,0.75,'limb',fontsize=13)
ax.text(-4.2,3.45,r'$S_0$ outer boundary (extrados)',fontsize=12,color='#b5462f')
ax.text(-4.2,3.1,r'$S_1$ inner boundary (intrados)',fontsize=12,color='#2a74a8')
ax.annotate('dip isogon $pq$',xy=((P[0]+Q[0])/2,(P[1]+Q[1])/2),xytext=(-1.15,0.45),fontsize=12,color='#1b7f5a',arrowprops=dict(arrowstyle='-',color='#1b7f5a',lw=0.8))
ax.set_xlim(-4.3,4.4); ax.set_ylim(-1.0,3.9); ax.set_aspect('equal'); ax.axis('off')
fig.tight_layout(); D='/home/abhijith/coding/major-project/IsoFold/report_draft/figures/'; fig.savefig(D+'fold_geometry_notation.png',dpi=200,facecolor='white',bbox_inches='tight'); fig.savefig(D+'fold_geometry_notation.svg',facecolor='white',bbox_inches='tight')
print(P,Q,dist)
