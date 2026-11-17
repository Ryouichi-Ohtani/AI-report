"""Original synthetic targets; no external image copyrights or private data."""
import numpy as np
from PIL import Image, ImageDraw


def landscape(size=64, related=False):
    image = Image.new("RGB", (size, size), (211, 230, 237))
    d = ImageDraw.Draw(image)
    def xy(points):
        return [(round(x*size), round(y*size)) for x,y in points]
    shift = 0.05 if related else 0
    d.ellipse([round((.69+shift)*size), round(.10*size), round((.88+shift)*size), round(.29*size)], fill=(234,103,74))
    d.polygon(xy([(0,.75),(.45,.22),(1,.81)]), fill=(53,85,117))
    d.polygon(xy([(.30,.40),(.45,.22),(.64,.43),(.51,.38),(.45,.41),(.39,.36)]), fill=(247,247,235))
    d.rectangle([0,round(.72*size),size,size], fill=(85,135,143))
    d.polygon(xy([(0,.82),(.23,.61),(.45,1),(0,1)]), fill=(31,72,68))
    d.polygon(xy([(.65,1),(.88,.58),(1,.80),(1,1)]), fill=(48,91,75))
    return np.asarray(image).copy()


def fruit(size=64, related=False):
    image = Image.new("RGB", (size,size), (245,232,202))
    d = ImageDraw.Draw(image)
    s = size
    offset = .04 if related else 0
    d.ellipse([int(.11*s),int(.74*s),int(.91*s),int(.90*s)], fill=(200,182,151))
    d.ellipse([int((.19+offset)*s),int(.28*s),int((.81+offset)*s),int(.81*s)], fill=(206,65,51))
    d.ellipse([int(.22*s),int(.29*s),int(.55*s),int(.67*s)], fill=(231,93,62))
    d.polygon([(int(.49*s),int(.35*s)),(int(.50*s),int(.13*s)),(int(.57*s),int(.12*s)),(int(.54*s),int(.35*s))], fill=(96,71,44))
    d.polygon([(int(.54*s),int(.21*s)),(int(.77*s),int(.08*s)),(int(.80*s),int(.19*s)),(int(.61*s),int(.27*s))], fill=(83,123,64))
    d.ellipse([int(.29*s),int(.38*s),int(.37*s),int(.48*s)], fill=(252,189,137))
    return np.asarray(image).copy()


def gradient(size=64, related=False):
    y, x = np.mgrid[0:1:complex(size), 0:1:complex(size)]
    phase = .06 if related else 0
    red = .2 + .7*x
    green = .3 + .5*y
    blue = .7 - .4*x + .12*np.sin(2*np.pi*(y+phase))
    image = np.clip(np.stack((red,green,blue),axis=2)*255,0,255).astype(np.uint8)
    # A small hard boundary challenges a globally smooth approximation.
    mask = (x-.66)**2 + (y-.30)**2 < .10**2
    image[mask] = (247,232,192)
    return image


TARGETS = {"landscape": landscape, "fruit": fruit, "gradient": gradient}


def add_noise(image, seed=20261117, sigma=22):
    rng = np.random.default_rng(seed)
    return np.clip(image.astype(float)+rng.normal(0,sigma,image.shape),0,255).astype(np.uint8)

