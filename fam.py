#!/bin/env python3
import argparse, base64, html, io, os, sys, zipfile
from collections import defaultdict
try:
    from PIL import Image
except ImportError:
    "PILlow import failed; please use `pip install pillow` to install it."
    sys.exit(1)

parser = argparse.ArgumentParser(description='Generate standalone .html with thumbnails of fam.crf textures.')
parser.add_argument('crf_path', metavar='fam_path',
                    help='path to fam.crf or fam subdirectory')
parser.add_argument('html_path', metavar='textures.html',
                    help='html file to generate')
parser.add_argument('--size', metavar='128', type=int, default=128,
                    help='thumbnail size')
parser.add_argument('--title', metavar='"Textures"', default="Textures",
                    help='html page title')
args = parser.parse_args()

crf_path = args.crf_path
output_filename = args.html_path
page_title = args.title
thumbnail_size = (args.size,args.size)
thumbnail_jpeg = True
background_color = (255,255,255)

if os.path.isdir(crf_path):
    # Read a directory
    def file_listing():
        fam_subdirs = [e.name
            for e in os.scandir(crf_path)
            if e.is_dir()]
        files = []
        for d in fam_subdirs:
            files.extend(os.path.join(d, e.name)
                for e in os.scandir(os.path.join(crf_path, d))
                if e.is_file())
        return sorted(files, key=(lambda s: s.lower()))
    def open_file(name):
        return open(os.path.join(crf_path, name), 'rb')
elif (os.path.isfile(crf_path)
    and (crf_path.lower().endswith('.crf')
         or crf_path.lower().endswith('.zip'))):
    # Read a crf/zip file
    crf = zipfile.ZipFile(crf_path)
    def file_listing():
        return sorted(crf.namelist(), key=(lambda s: s.lower()))
    def open_file(name):
        return crf.open(name, 'r')

fams = defaultdict(list)
for file_path in file_listing():
    parts = os.path.split(file_path.lower())
    fam, filename = parts
    if not fam or not filename or ('/' in fam or '\\' in fam):
        print(f"skipping {file_path}", file=sys.stderr)
        continue
    name, ext = os.path.splitext(filename)
    if (not ext in ('.pcx', '.gif', '.png', '.jpg')):
        print(f"skipping {file_path}", file=sys.stderr)
        continue
    if filename=='full.pcx':
        print(f"skipping {file_path}", file=sys.stderr)
        continue
    print(f"converting {file_path}", file=sys.stderr)
    with open_file(file_path) as texf:
        with Image.open(texf) as im:
            # TODO - transparent palette index?
            width, height = im.size
            im = im.convert('RGBA')
            # thumbnail and (if necessary) flatten the image
            im.thumbnail(thumbnail_size, resample=Image.BILINEAR, reducing_gap=None)
            if thumbnail_jpeg:
                bg = Image.new('RGBA', im.size, background_color)
                im = Image.alpha_composite(bg, im)
            # save the image
            im = im.convert('RGB')
            imagef = io.BytesIO()
            if thumbnail_jpeg:
                im.save(imagef, 'JPEG', quality=80)
            else:
                im.save(imagef, 'PNG')
    content_type = ("image/jpg" if thumbnail_jpeg else "image/png")
    encoded_image = base64.b64encode(imagef.getvalue()).decode('ascii')
    uri = f"data:{content_type};base64,{encoded_image}"
    fams[fam].append((name, ext, width, height, uri))

sections = []
escape = html.escape
for fam, textures in sorted(fams.items()):
    cells = []
    for (name, ext, width, height, uri) in textures:
        cell = (
             "<div class='texture'>\n"
            f"<div class='image'><img src='{uri}'></div>\n"
            f"<div class='caption'>{escape(name)} - {width}x{height} {escape(ext)}</div>\n"
             "</div>\n"
            )
        cells.append(cell)
    cells = "".join(cells)
    section = (
         "<section>\n"
        f"<h2>{escape(fam)}</h2>\n"
        f"<div class='fam'>{cells}</div>\n"
         "</section>\n"
        )
    sections.append(section)
sections = "".join(sections)
page = ("""\
<!DOCTYPE html>
<html>
<head>
"""
f"<title>{escape(page_title)}</title>"
"""\
<style>
body {
    background-color: #2f3136;
    color: #fff;
    font-family: Arial,sans-serif;
}
h1 {
    color: #fff;
    font-size: 18px;
    font-weight: bold;
}
h2 {
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    text-transform: capitalize;
}

.fam {
    display: flex;
    flex-wrap: wrap;
    flex-direction: row;
}
.texture {
    flex: 0 0 auto;
    padding-right: 4px;
    padding-bottom: 4px;
}
img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}
.caption {
    color: #8e9297;
    font-size: 10px;
}
.image {
"""
f"    width: {thumbnail_size[0]}px;"
f"    height: {thumbnail_size[1]}px;"
"""
}
.texture {
"""
f"    width: {thumbnail_size[0]}px;"
"""
}
</style>
</head>
<body>
"""
f"<h1>{escape(page_title)}</h1>{sections}"
"""\
</body>
</html>
""")
with open(output_filename, 'w') as f:
    f.write(page)
