"""Prepare a private Type1 CM extension fallback from Matplotlib's BaKoMa font.

Tectonic's cached single-byte math path on this host requires Type1 outlines.
The generated font is a build artifact, never committed or separately distributed.
"""
from pathlib import Path
from fontTools import t1Lib
from fontTools.misc.psCharStrings import T1CharString
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont


class Type1Pen(BasePen):
    def __init__(self, glyphs, width):
        super().__init__(glyphs)
        self.program = [0, round(width), 'hsbw']
        self.point = (0, 0)
        self.start = (0, 0)

    def _moveTo(self, point):
        self.program += [round(point[0] - self.point[0]), round(point[1] - self.point[1]), 'rmoveto']
        self.point = self.start = point

    def _lineTo(self, point):
        self.program += [round(point[0] - self.point[0]), round(point[1] - self.point[1]), 'rlineto']
        self.point = point

    def _curveToOne(self, p1, p2, p3):
        points = [self.point, p1, p2, p3]
        for a, b in zip(points, points[1:]):
            self.program += [round(b[0] - a[0]), round(b[1] - a[1])]
        self.program.append('rrcurveto')
        self.point = p3

    def _closePath(self):
        self.program.append('closepath')
        # Type1 closepath retains the current point for subsequent relative moves.

    def _endPath(self):
        pass


def prepare(source, destination):
    font = TTFont(source)
    glyphs = font.getGlyphSet()
    scale = 1000 / font['head'].unitsPerEm
    charstrings = {}
    for name in font.getGlyphOrder():
        width = font['hmtx'].metrics[name][0] * scale
        pen = Type1Pen(glyphs, width)
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, scale, 0, 0)))
        pen.program.append('endchar')
        charstrings[name] = T1CharString(program=pen.program, subrs=[])
    encoding = ['.notdef'] * 256
    for index, name in font.getBestCmap().items():
        if index < 128:
            encoding[index] = name
    low = ('parenleftbig parenrightbig bracketleftbig bracketrightbig floorleftbig floorrightbig '
           'ceilingleftbig ceilingrightbig braceleftbig bracerightbig angbracketleftbig angbracketrightbig '
           'vextendsingle vextenddouble slashbig backslashbig parenleftBig parenrightBig parenleftbigg '
           'parenrightbigg bracketleftbigg bracketrightbigg floorleftbigg floorrightbigg ceilingleftbigg '
           'ceilingrightbigg braceleftbigg bracerightbigg angbracketleftbigg angbracketrightbigg slashbigg backslashbigg').split()
    encoding[:32] = low
    encoding[32], encoding[127] = 'parenleftBigg', 'arrowdblbt'
    head = font['head']
    result = t1Lib.T1Font.__new__(t1Lib.T1Font)
    result.encoding = 'ascii'
    result.font = {
        'FontName': 'ReportCMEXFallback', 'FontType': 1, 'PaintType': 0,
        'FontMatrix': [.001, 0, 0, .001, 0, 0],
        'FontBBox': [round(getattr(head, k) * scale) for k in ['xMin', 'yMin', 'xMax', 'yMax']],
        'Encoding': encoding,
        'FontInfo': {'FullName': 'Report CM extension fallback', 'FamilyName': 'Computer Modern',
                     'Notice': 'Private format conversion of Matplotlib BaKoMa CMEX10; original font copyright retained.'},
        'Private': {'RD': t1Lib.RD_value, 'ND': t1Lib.ND_values[0], 'NP': t1Lib.PD_values[0],
                    'lenIV': 4, 'BlueValues': [], 'Subrs': []},
        'CharStrings': charstrings,
    }
    result.saveAs(str(destination), 'PFB')
    # Reparse the binary to ensure that the generated file is well formed.
    parsed = t1Lib.T1Font(str(destination)); parsed.parse()
    assert len(parsed.font['CharStrings']) == len(charstrings)


if __name__ == '__main__':
    import matplotlib
    root = Path(__file__).resolve().parents[1]
    prepare(Path(matplotlib.get_data_path()) / 'fonts/ttf/cmex10.ttf', root / 'report-cmex.pfb')
