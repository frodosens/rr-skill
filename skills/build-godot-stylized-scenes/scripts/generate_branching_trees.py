#!/usr/bin/env python3
"""Bake deterministic branching trees to standalone glTF 2 binary files.

Python 3 standard library only. This authoring tool is NEVER loaded by Godot.
Y-up, metres, ground-level origin, two opaque identity meshes. No textures,
external sources, animation, collision mesh, shader, or runtime growth code.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import random
import struct
from bundle_paths import fresh_output

Vec = tuple[float, float, float]

def add(a: Vec, b: Vec) -> Vec:
    return tuple(a[i] + b[i] for i in range(3))
def sub(a: Vec, b: Vec) -> Vec:
    return tuple(a[i] - b[i] for i in range(3))
def mul(a: Vec, s: float) -> Vec:
    return tuple(v * s for v in a)
def length(a: Vec) -> float:
    return math.sqrt(sum(v*v for v in a))
def norm(a: Vec) -> Vec:
    return mul(a, 1.0 / max(length(a), 1e-9))
def cross(a: Vec, b: Vec) -> Vec:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def lerp(a: Vec, b: Vec, t: float) -> Vec:
    return add(mul(a, 1-t), mul(b, t))
def linear(c: float) -> float:
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4

def color(rgb: Vec) -> Vec:
    return tuple(linear(min(1, max(0, v))) for v in rgb)

@dataclass
class Mesh:
    name: str
    vertices: list = field(default_factory=list)
    normals: list = field(default_factory=list)
    colors: list = field(default_factory=list)
    indices: list = field(default_factory=list)

    def triangle(self, a: Vec, b: Vec, c: Vec, rgb: Vec):
        n = norm(cross(sub(b, a), sub(c, a)))
        if length(cross(sub(b, a), sub(c, a))) < 1e-8:
            raise ValueError('Degenerate triangle')
        i = len(self.vertices)
        self.vertices.extend((a, b, c))
        self.normals.extend((n, n, n))
        self.colors.extend((color(rgb),)*3)
        self.indices.extend((i, i+1, i+2))

    @property
    def triangles(self):
        return len(self.indices)//3

    def tube(self, points: list[Vec], radii: list[float], sides: int, rgb: Vec, rng):
        # Rings follow each internode's tangent. The trunk grows upward with
        # seeded lateral perturbations; branches have upward phototropism.
        rings = []
        for i, p in enumerate(points):
            tangent = norm(sub(points[min(i+1, len(points)-1)], points[max(0, i-1)]))
            if i == 0 and abs(p[1]) < 1e-7:
                tangent = (0, 1, 0)  # Planar foot sits exactly on the ground.
            u = norm(cross(tangent, (0, 0, 1)))
            v = norm(cross(tangent, u))
            rings.append([add(p, add(mul(u, radii[i]*math.cos(j*math.tau/sides)), mul(v, radii[i]*math.sin(j*math.tau/sides)))) for j in range(sides)])
        for i in range(len(points)-1):
            for j in range(sides):
                k = (j+1) % sides
                a,b,c,d = rings[i][j],rings[i][k],rings[i+1][j],rings[i+1][k]
                # Ring winding produces outward glTF CCW faces.
                shade = 0.86 + 0.18*rng.random()
                if rgb[0] > .6 and (i+j*3) % 7 == 0:
                    shade *= .54  # Sparse birch bark markings, baked in color.
                col = mul(rgb, shade)
                self.triangle(a, b, c, col)
                self.triangle(b, d, c, col)
        for j in range(sides):
            k = (j+1) % sides
            self.triangle(points[0], rings[0][k], rings[0][j], mul(rgb,.7))
            self.triangle(points[-1], rings[-1][j], rings[-1][k], rgb)

    def crown(self, center: Vec, scale: Vec, rng, base_rgb: Vec, low=False, yaw=None):
        # Irregular flattened foliage lobes form a broken canopy, rather than
        # cone stacks. Closed opaque volumes keep mobile overdraw bounded.
        if low:
            verts=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
            faces=[(0,2,4),(4,2,1),(1,2,5),(5,2,0),(4,3,0),(1,3,4),(5,3,1),(0,3,5)]
        else:
            p=(1+math.sqrt(5))/2
            verts=[(-1,p,0),(1,p,0),(-1,-p,0),(1,-p,0),(0,-1,p),(0,1,p),(0,-1,-p),(0,1,-p),(p,0,-1),(p,0,1),(-p,0,-1),(-p,0,1)]
            faces=[(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
        rot=rng.random()*math.tau if yaw is None else yaw
        transformed=[]
        for vertex in verts:
            x,y,z=norm(vertex)
            x,z=x*math.cos(rot)-z*math.sin(rot),x*math.sin(rot)+z*math.cos(rot)
            irregular=0.88+rng.random()*.24
            transformed.append(add(center,(x*scale[0]*irregular,y*scale[1]*irregular,z*scale[2]*irregular)))
        for face in faces:
            a,b,c=[transformed[i] for i in face]
            outward=norm(sub(mul(add(add(a,b),c),1/3),center))
            shade=.86+.13*rng.random()+.13*max(-.5,outward[1])
            self.triangle(a,b,c,mul(base_rgb,shade))


def grow(seed: int, species: str, low: bool=False):
    """Seeded branching growth with apical dominance, taper and tropism.

    Each growth axis is a small sequence of internodes. At six trunk nodes,
    lateral buds grow outward then curve toward light. Each lateral axis forks
    twice, and daughter radii scale by 0.57. The trunk retains apical dominance.
    Baking converts this skeleton into tapered low-sided tubes and foliage.
    """
    rng = random.Random(seed)
    bark_rng=random.Random(seed+4)
    bark=Mesh('Branches'); leaf=Mesh('Foliage')
    birch=species=='birch'
    height=7.5 if birch else 7.25
    bark_color=(.76,.73,.63) if birch else (.31,.24,.17)
    leaf_color=(.43,.59,.19) if birch else (.26,.48,.20)
    spread=1.67 if birch else 2.15
    oak=species=='oak'
    cypress=species=='cypress'
    if oak:
        height=5.9; spread=3.2; bark_color=(.34,.26,.18); leaf_color=(.30,.45,.16)
    elif cypress:
        height=7.7; spread=.65; bark_color=(.39,.27,.18); leaf_color=(.22,.39,.28)
    trunk=[]
    count=8
    for i in range(count):
        t=i/(count-1)
        trunk.append((.12*math.sin(t*4.8)+.09*t, height*t, .10*math.sin(t*6.4)))
    radii=[(.38 if oak else .18 if cypress else .20 if birch else .26)*(1-i/(count-1))**1.25+.025 for i in range(count)]
    radii[0]*=1.4
    if low:
        idx=[0,1,3,5,7]
        bark.tube([trunk[i] for i in idx],[radii[i] for i in idx],4,bark_color,bark_rng)
    else:
        bark.tube(trunk,radii,6,bark_color,bark_rng)
    crowns=[]
    skeleton=[]
    for j in range(6):
        t=.31+j*.094
        u=t*(count-1); k=int(u)
        start=lerp(trunk[k],trunk[min(k+1,count-1)],u-k)
        angle=j*2.399963229728653 + rng.uniform(-.16,.16)
        reach=spread*(1.12-.50*j/5)*rng.uniform(.88,1.1)
        rise=(1.25 if oak else 1.05 if cypress else 2.20 if birch else 1.65)*rng.uniform(.9,1.1)
        direction=(math.cos(angle),0,math.sin(angle))
        points=[start]
        for seg in range(1,4):
            q=seg/3
            # Quadratic rise bends the terminal toward the light.
            points.append(add(start,add(mul(direction,reach*q),(0,rise*(.58*q+.42*q*q),0))))
        radius=(.17 if oak else .065 if cypress else .105 if birch else .125)*(1-.32*j/5)
        if low:
            bark.tube([points[i] for i in (0,2,3)],[radius,radius*.52,.025],3,bark_color,bark_rng)
        else:
            bark.tube(points,[radius,radius*.78,radius*.48,.023],4,bark_color,bark_rng)
        skeleton.append({'parent':'trunk','points':points,'radius':radius})
        for fork in range(2):
            origin=points[1+fork]
            fork_angle=angle+(-.62 if fork==0 else .70)
            outward=(math.cos(fork_angle),0,math.sin(fork_angle))
            extent=reach*(.54 if fork==0 else .46)
            mid=add(origin,add(mul(outward,extent*.55),(0,.38,0)))
            end=add(origin,add(mul(outward,extent),(0,.95 if birch else .72,0)))
            if not low:
                bark.tube([origin,mid,end],[radius*.57,radius*.36,.014],3,bark_color,bark_rng)
            skeleton.append({'parent':j,'points':[origin,mid,end],'radius':radius*.57})
            size=(.99,.80,.90) if birch else (1.25,.62,1.06)
            if oak:
                size=(1.55,.9,1.4)
            elif cypress:
                size=(.59,1.25,.59)
            if low:
                crowns.append((end,size))
            else:
                crowns.append((add(end,(0,.15,0)),size))
                # Offset the second lobe: branch crowns stay asymmetric.
                offset=add(mul(outward,.32),(0,.35,.11))
                crowns.append((add(end,offset),mul(size,.82)))
    # Apical crown fills the leader and keeps a slender, irregular summit.
    top=add(trunk[-1],(0,-.23,0))
    top_size=(.58,1.1,.57) if cypress else (1.32,.90,1.23) if oak else (.87,.77,.84) if birch else (1.12,.70,1.03)
    crowns.append((top,top_size))
    if not low:
        crowns.append((add(top,(.34,-.36,-.27)),(.49,.9,.49) if cypress else (.82,.58,.85)))
    for center,size in crowns:
        leaf.crown(center,size,rng,leaf_color,low)
    all_vertices=bark.vertices+leaf.vertices
    minimum=[min(v[i] for v in all_vertices) for i in range(3)]
    maximum=[max(v[i] for v in all_vertices) for i in range(3)]
    stats={'species':species,'seed':seed,'lod':'far' if low else 'near','triangles':bark.triangles+leaf.triangles,'branch_triangles':bark.triangles,'foliage_triangles':leaf.triangles,'mesh_count':2,'material_count':2,'texture_count':0,'bounds_min':minimum,'bounds_max':maximum,'height_m':maximum[1]-minimum[1],'axes':{'primary':1,'lateral':6,'daughter':12},'foliage_lobes':len(crowns),'coordinate_system':'right-handed Y-up; metres; ground-level origin'}
    assert stats['triangles'] <= (350 if low else 1200),stats
    assert 6.5 <= stats['height_m'] <= 10,stats
    return [bark,leaf],stats



def grow_spruce(seed: int, low: bool=False):
    """Bake six radial branch whorls and a tapered apical leader.

    Spruce growth uses four lateral buds per whorl rather than the alternating
    bifurcating broadleaf architecture. Mature limbs droop before their tips
    turn upward; foliage sprays widen toward the lower, older branches.
    """
    rng=random.Random(seed); bark_rng=random.Random(seed+4)
    bark=Mesh('Branches'); leaf=Mesh('Foliage')
    bark_color=(.35,.28,.19); leaf_color=(.22,.43,.34)
    height=8.1
    trunk=[(.05*math.sin(i*.8),height*i/7,.04*math.sin(i*.9)) for i in range(8)]
    radii=[.24*(1-i/7)**1.2+.02 for i in range(8)];radii[0]*=1.35
    idx=[0,2,4,6,7] if low else list(range(8))
    bark.tube([trunk[i] for i in idx],[radii[i] for i in idx],4 if low else 6,bark_color,bark_rng)
    crown_count=0
    for tier in range(6):
        y=1.45+tier*1.07
        reach=2.55-tier*.35
        for branch in range(4):
            angle=branch*math.tau/4+tier*.63+rng.uniform(-.12,.12)
            radial=(math.cos(angle),0,math.sin(angle))
            start=(.04*math.sin(tier),y,.035*math.cos(tier))
            mid=add(start,add(mul(radial,reach*.52),(0,-.12,0)))
            end=add(start,add(mul(radial,reach),(0,.16,0)))
            if not low:
                r=.08*(1-tier*.11)
                bark.tube([start,mid,end],[r,r*.58,.012],3,bark_color,bark_rng)
            center=add(start,add(mul(radial,reach*.57),(0,.27,0)))
            leaf.crown(center,(reach*.72,.45 if tier<4 else .38,.65-tier*.045),rng,leaf_color,low,yaw=angle)
            crown_count+=1
    leaf.crown((0,7.65,0),(.59,1.05,.56),rng,leaf_color,low)
    crown_count+=1
    vertices=bark.vertices+leaf.vertices
    minimum=[min(v[i] for v in vertices) for i in range(3)]
    maximum=[max(v[i] for v in vertices) for i in range(3)]
    stats={'species':'spruce','seed':seed,'lod':'far' if low else 'near','triangles':bark.triangles+leaf.triangles,'branch_triangles':bark.triangles,'foliage_triangles':leaf.triangles,'mesh_count':2,'material_count':2,'texture_count':0,'bounds_min':minimum,'bounds_max':maximum,'height_m':maximum[1]-minimum[1],'axes':{'primary':1,'lateral':24,'daughter':0},'foliage_lobes':crown_count,'coordinate_system':'right-handed Y-up; metres; ground-level origin'}
    assert stats['triangles'] <= (350 if low else 1200),stats
    assert 7 <= stats['height_m'] <= 10,stats
    return [bark,leaf],stats


def finished_tree(bark, leaf, species, seed, low, axes, lobes):
    vertices=bark.vertices+leaf.vertices
    minimum=[min(v[i] for v in vertices) for i in range(3)]
    maximum=[max(v[i] for v in vertices) for i in range(3)]
    stats={'species':species,'seed':seed,'lod':'far' if low else 'near','triangles':bark.triangles+leaf.triangles,'branch_triangles':bark.triangles,'foliage_triangles':leaf.triangles,'mesh_count':2,'material_count':2,'texture_count':0,'bounds_min':minimum,'bounds_max':maximum,'height_m':maximum[1]-minimum[1],'axes':axes,'foliage_lobes':lobes,'coordinate_system':'right-handed Y-up; metres; ground-level origin'}
    budget=(450 if low else 2200) if species=='cherry' else (350 if low else 1200)
    assert stats['triangles'] <= budget,stats
    assert minimum[1]>=-1e-6 and 5 <= stats['height_m'] <= 11,stats
    return [bark,leaf],stats


def pendant(mesh, top, width, drop, rng, rgb, low):
    """Closed hanging foliage curtain, tapered into a long downward point."""
    count=4 if low else 5
    ring=[]
    for i in range(count):
        angle=i*math.tau/count
        ring.append(add(top,(math.cos(angle)*width,.10*rng.uniform(-1,1),math.sin(angle)*width*.65)))
    apex=add(top,(0,.42,0));tip=add(top,(.12,-drop,0))
    if low:
        for i in range(count):
            j=(i+1)%count
            mesh.triangle(apex,ring[j],ring[i],rgb)
            mesh.triangle(tip,ring[i],ring[j],mul(rgb,.83))
    else:
        lower=[add(top,((p[0]-top[0])*.5,-drop*.48,(p[2]-top[2])*.5)) for p in ring]
        for i in range(count):
            j=(i+1)%count
            mesh.triangle(apex,ring[j],ring[i],mul(rgb,1.05))
            mesh.triangle(ring[i],ring[j],lower[i],rgb)
            mesh.triangle(ring[j],lower[j],lower[i],mul(rgb,.91))
            mesh.triangle(tip,lower[i],lower[j],mul(rgb,.80))


def grow_willow(seed, low=False):
    """Weeping growth: lifted primary forks, gravity-bent terminal shoots."""
    rng=random.Random(seed);brng=random.Random(seed+7)
    bark=Mesh('Branches');leaf=Mesh('Foliage');bcol=(.40,.32,.20)
    trunk=[(0,0,0),(.05,.55,0),(.12,1.6,.03),(.27,2.8,.08),(.32,3.8,.16),(.20,4.8,.18),(.12,5.5,.12)]
    radii=[.40,.29,.24,.20,.15,.09,.025]
    idx=[0,2,4,6] if low else list(range(7))
    bark.tube([trunk[i] for i in idx],[radii[i] for i in idx],4 if low else 6,bcol,brng)
    for branch in range(6):
        angle=branch*2.3999632297
        outward=(math.cos(angle),0,math.sin(angle))
        start=trunk[2+branch%4]
        end=add(start,add(mul(outward,2.35+rng.random()*.35),(0,2.8-(start[1]-1.6)*.48,0)))
        mid=lerp(start,end,.55)
        bark.tube([start,add(mid,(0,.32,0)),end],[.14,.085,.035],3 if low else 4,bcol,brng)
        leaf.crown(add(end,(0,.28,0)),(1.24,.50,1.09),rng,(.52,.59,.21),low)
        for child in range(3):
            direction=(math.cos(angle+(child-1)*.50),0,math.sin(angle+(child-1)*.50))
            top=add(end,add(mul(direction,.65+child*.17),(0,-.10-child*.13,0)))
            drop=1.9+rng.random()*.65
            if not low:
                tip=add(top,(.10,-drop*.91,0))
                bark.tube([end,top,tip],[.035,.025,.008],3,bcol,brng)
            col=(.49+rng.random()*.09,.59+rng.random()*.06,.18+rng.random()*.07)
            pendant(leaf,top,.54 if child!=1 else .63,drop,rng,col,low)
    return finished_tree(bark,leaf,'willow',seed,low,{'primary':1,'lateral':6,'daughter':18},24)


def grow_maple(seed, low=False):
    """A short main stem divides into three co-dominant maple leaders."""
    rng=random.Random(seed);brng=random.Random(seed+7)
    bark=Mesh('Branches');leaf=Mesh('Foliage');bcol=(.33,.23,.17)
    points=[(0,0,0),(.02,.45,0),(.10,1.25,.08),(.14,2.2,.12),(.14,2.65,.12)]
    idx=[0,1,3,4] if low else list(range(5))
    radii=[.45,.31,.27,.24,.21]
    bark.tube([points[i] for i in idx],[radii[i] for i in idx],4 if low else 6,bcol,brng)
    palette=[(.81,.29,.07),(.72,.18,.05),(.90,.40,.09),(.87,.24,.09)]
    for leader in range(3):
        angle=leader*math.tau/3+.23
        direction=(math.cos(angle),0,math.sin(angle));start=points[-1]
        axis=[add(start,add(mul(direction,2.0*(i/4)**.9),(0,3.8*i/4,0))) for i in range(5)]
        if low:
            bark.tube([axis[i] for i in (0,2,4)],[.20,.12,.027],3,bcol,brng)
        else:
            bark.tube(axis,[.20,.17,.12,.07,.027],5,bcol,brng)
        for j in range(4):
            origin=axis[1+j%3]
            a=angle+(-.6 if j%2==0 else .65)
            radial=(math.cos(a),0,math.sin(a))
            tip=add(origin,add(mul(radial,1.35-.15*(j%2)),(0,1.2+.18*j,0)))
            if not low:
                bark.tube([origin,lerp(origin,tip,.55),tip],[.085,.045,.014],4,bcol,brng)
            base=palette[(leader+j)%len(palette)]
            leaf.crown(tip,(1.15,.92,1.05),rng,base,low)
            leaf.crown(add(tip,add(mul(radial,.45),(0,.38,0))),(.86,.72,.92),rng,mul(base,1.06),low)
    return finished_tree(bark,leaf,'maple',seed,low,{'primary':3,'lateral':12,'daughter':0},24)


def needle_pad(mesh, center, size, rng, rgb, low):
    """A closed, flattened needle spray with a jagged perimeter, not a ball."""
    count=4 if low else 8
    ring=[]
    for i in range(count):
        a=i*math.tau/count
        factor=(.78 if i%2 else 1.15)*(1+rng.uniform(-.1,.1))
        ring.append(add(center,(math.cos(a)*size[0]*factor,rng.uniform(-.05,.05),math.sin(a)*size[2]*factor)))
    top=add(center,(.12,size[1],0));bottom=add(center,(0,-size[1]*.6,0))
    for i in range(count):
        j=(i+1)%count
        mesh.triangle(top,ring[j],ring[i],mul(rgb,.94+rng.random()*.13))
        mesh.triangle(bottom,ring[i],ring[j],mul(rgb,.73))


def grow_windswept_pine(seed, low=False):
    """Persistent wind bends the trunk and biases all mature branches leeward."""
    rng=random.Random(seed);brng=random.Random(seed+7)
    bark=Mesh('Branches');leaf=Mesh('Foliage');bcol=(.43,.29,.17);green=(.28,.43,.29)
    trunk=[(.035*i*i,7.35*i/7,.10*math.sin(i*.8)) for i in range(8)]
    radii=[.29*(1-i/7)**1.18+.025 for i in range(8)];radii[0]*=1.3
    idx=[0,2,4,6,7] if low else list(range(8))
    bark.tube([trunk[i] for i in idx],[radii[i] for i in idx],4 if low else 6,bcol,brng)
    crowns=0
    for branch in range(7):
        start=lerp(trunk[2+branch%5],trunk[min(3+branch%5,7)],.35)
        spread=2.5-branch*.17
        side=-1 if branch%2 else 1
        end=add(start,(spread,.85+branch*.045,side*(1.8-branch*.1)))
        mid=add(lerp(start,end,.5),(0,.32,0))
        bark.tube([start,mid,end],[.105,.057,.018],3 if low else 4,bcol,brng)
        for fork in range(1 if low else 2):
            tip=add(end,(.55+fork*.50,.12,side*(.25-fork*.55)))
            if not low:
                bark.tube([mid,lerp(mid,tip,.64),tip],[.04,.026,.009],3,bcol,brng)
            needle_pad(leaf,tip,(1.50,.25,.95),rng,green,low)
            crowns+=1
    for offset in [(0,0,0),(.70,-.25,-.30)]:
        needle_pad(leaf,add(trunk[-1],offset),(1.55,.32,.90),rng,mul(green,1.1),low)
        crowns+=1
    return finished_tree(bark,leaf,'windswept_pine',seed,low,{'primary':1,'lateral':7,'daughter':14},crowns)



def grow_cherry(seed, low=False):
    """Broad cherry with many small, uneven rounded blossom clusters.

    Six layered branches retain visible gaps. Small irregular crown lobes
    follow eighteen shoots instead of using one large sphere or flat flowers.
    This matches the scene's other low-poly trees while keeping a pink crown.
    """
    rng=random.Random(seed);brng=random.Random(seed+7);frng=random.Random(seed+19)
    bark=Mesh('Branches');flower=Mesh('Foliage');bcol=(.42,.31,.29)
    trunk=[(0,0,0),(.05,.45,.02),(.17,1.05,.04),(.12,1.7,.08),(.24,2.35,.10),(.25,2.65,.12)]
    radii=[.36,.27,.23,.19,.15,.11]
    idx=[0,2,4,5] if low else list(range(6))
    bark.tube([trunk[i] for i in idx],[radii[i] for i in idx],4 if low else 5,bcol,brng)
    palette=[(.98,.78,.85),(.95,.70,.80),(1.0,.84,.89),(.97,.75,.83)]
    cluster_count=0
    for branch in range(6):
        angle=branch*2.3999632297+.29+rng.uniform(-.14,.14)
        radial=(math.cos(angle),0,math.sin(angle))
        start=trunk[[2,3,3,4,4,5][branch]]
        reach=(3.05 if branch<3 else 2.35)+rng.uniform(-.20,.30)
        rise=(2.75 if branch<3 else 2.6)+rng.uniform(-.20,.30)
        axis=[start,add(start,add(mul(radial,reach*.30),(0,rise*.43,0))),add(start,add(mul(radial,reach*.66),(0,rise*.75,0))),add(start,add(mul(radial,reach),(0,rise,0)))]
        if low:
            bark.tube([axis[i] for i in (0,2,3)],[.13,.055,.014],3,bcol,brng)
        else:
            bark.tube(axis,[.15,.11,.061,.016],4,bcol,brng)
        for twig in range(3):
            origin=lerp(axis[1],axis[3],.08+twig*.36)
            twig_angle=angle+(-.73 if twig%2==0 else .78)
            direction=(math.cos(twig_angle),0,math.sin(twig_angle))
            end=add(origin,add(mul(direction,1.25+twig*.12),(0,.63+twig*.10,0)))
            mid=add(lerp(origin,end,.5),(0,.13,0))
            if not low:
                bark.tube([origin,mid,end],[.039,.025,.007],3,bcol,brng)
            for bloom in range(3):
                t=.14+bloom*.42
                point=lerp(origin,end,t)
                side=cross(direction,(0,1,0))
                point=add(point,add(mul(side,(-1 if bloom%2 else 1)*(.15+rng.random()*.19)),(0,rng.uniform(-.10,.23),0)))
                size=(.48+rng.random()*.32,.32+rng.random()*.22,.46+rng.random()*.34)
                # Tiny, varied lobes form uneven sprays. The far bake keeps
                # two slightly larger lobes per shoot instead of three.
                if not low or bloom!=1:
                    flower.crown(point,mul(size,1.17 if low else 1.0),frng,palette[(branch+twig+bloom)%4],low)
                    cluster_count+=1
    meshes,stats=finished_tree(bark,flower,'cherry',seed,low,{'primary':6,'lateral':18,'daughter':0},cluster_count)
    stats.update({'blossom_clusters':cluster_count,'canopy_style':'Small irregular rounded blossom clusters of varied sizes along a broad open branch structure.'})
    return meshes,stats


def glb(meshes, extras):
    payload=bytearray(); views=[]; accessors=[]
    def accessor(values,components,typ,fmt):
        while len(payload)%4: payload.append(0)
        offset=len(payload)
        flat=[x for v in values for x in v] if components>1 else values
        payload.extend(struct.pack('<'+fmt*len(flat),*flat))
        views.append({'buffer':0,'byteOffset':offset,'byteLength':len(payload)-offset})
        a={'bufferView':len(views)-1,'componentType':typ,'count':len(values),'type':{1:'SCALAR',3:'VEC3'}[components]}
        if components==3:
            a['min']=[min(v[i] for v in values) for i in range(3)];a['max']=[max(v[i] for v in values) for i in range(3)]
        accessors.append(a)
        return len(accessors)-1
    gltf_meshes=[]
    for mat,mesh in enumerate(meshes):
        pos=accessor(mesh.vertices,3,5126,'f')
        normal=accessor(mesh.normals,3,5126,'f')
        rgb=accessor(mesh.colors,3,5126,'f')
        indices=accessor(mesh.indices,1,5123,'H')
        gltf_meshes.append({'name':mesh.name,'primitives':[{'attributes':{'POSITION':pos,'NORMAL':normal,'COLOR_0':rgb},'indices':indices,'material':mat,'mode':4}]})
    doc={'asset':{'version':'2.0','generator':'Alpine Drive offline branching generator 1.0'},'scene':0,'scenes':[{'nodes':[0,1]}],'nodes':[{'name':m.name,'mesh':i} for i,m in enumerate(meshes)],'meshes':gltf_meshes,'materials':[{'name':m.name+'Opaque','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':1},'alphaMode':'OPAQUE','doubleSided':False} for m in meshes],'buffers':[{'byteLength':len(payload)}],'bufferViews':views,'accessors':accessors,'extras':extras}
    if extras['species']=='cherry':
        # Flower petals are matte, unlike glossy waxed leaves. Bake the glTF
        # material extension so asset previews and runtime share the same look.
        doc['materials'][1]['extensions']={'KHR_materials_specular':{'specularFactor':0.0}}
        doc['extensionsUsed']=['KHR_materials_specular']
    js=json.dumps(doc,separators=(',',':'),sort_keys=True).encode()
    js+=b' '*((-len(js))%4); payload+=b'\0'*((-len(payload))%4)
    return struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(payload))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(payload),0x004E4942)+payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--check',action='store_true',help='Verify deterministic committed outputs without writing')
    args=parser.parse_args()
    args.output = args.output.resolve() if args.check else fresh_output(args.output)
    rows=[]
    for species,seed in [('alder',1729),('birch',3253),('oak',6211),('cypress',8233),('spruce',9851),('willow',10267),('maple',12101),('windswept_pine',14009),('cherry',16411)]:
        for low in (False,True):
            special={'spruce':grow_spruce,'willow':grow_willow,'maple':grow_maple,'windswept_pine':grow_windswept_pine,'cherry':grow_cherry}
            meshes,stats=special[species](seed,low) if species in special else grow(seed,species,low)
            filename=f'branching_{species}_01'+('_lod' if low else '')+'.glb'
            data=glb(meshes,stats)
            stats.update({'file':filename,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
            target=args.output/filename
            if args.check:
                assert target.read_bytes()==data,f'{filename} differs from deterministic generator'
            else:
                args.output.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
            rows.append(stats)
    manifest={'format_version':1,'authoring':'Original deterministic procedural geometry made for Alpine Drive; no third-party source assets, paid providers, fonts, textures or libraries.','license':'Project-owned original assets; no third-party attribution obligations. No separate third-party license is introduced.','generator':'scripts/generate_branching_trees.py','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'runtime':'Only baked GLB meshes are imported. This Python tool never runs in the game.','budget':{'near_max_triangles':1200,'far_max_triangles':350,'species_overrides':{'cherry':{'near_max_triangles':2200,'far_max_triangles':450}},'materials_per_asset':2,'textures':0,'transparent_materials':0},'assets':rows}
    rendered=json.dumps(manifest,indent=2,sort_keys=True)+'\n'
    if args.check:
        assert (args.output/'manifest.json').read_text()==rendered,'Manifest differs'
    else:
        (args.output/'manifest.json').write_text(rendered)
    for row in rows:
        print(f"{row['file']}: {row['triangles']} triangles; {row['height_m']:.2f} m; {row['bytes']} bytes; {row['sha256'][:12]}")
    print('PASS: reproducibility and geometry budgets' if args.check else f'Baked {len(rows)} standalone GLB files offline.')

if __name__=='__main__':
    main()
