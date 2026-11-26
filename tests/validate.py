import hashlib
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

class Portfolio(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.anchors = set()
        self.headings = 0
        self.lang = None
        self.images = []
        self.previews = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "img":
            self.images.append(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "h1":
            self.headings += 1
        if element_id := attrs.get("id"):
            assert element_id not in self.ids, f"Duplicate ID: {element_id}"
            self.ids.add(element_id)
        if tag == "a" and (href := attrs.get("href", "")).startswith("#"):
            self.anchors.add(href[1:])
        if tag == "a" and attrs.get("class") == "project-preview":
            self.previews.append(attrs)

html = Path("index.html").read_text(encoding="utf-8")
assert html.lower().startswith("<!doctype html>"), "Missing HTML doctype"
page = Portfolio()
page.feed(html)
page.close()
assert page.lang == "ko" and page.headings == 1, "Expected a Korean page with one h1"
assert {"main", "work"} <= page.ids, "Missing page or work section"
assert not (page.anchors - page.ids), f"Broken anchors: {page.anchors - page.ids}"

hero, *posters = page.images
assert hero.get("alt", "").strip()
size = (int(hero["width"]), int(hero["height"]))
assert size == (1120, 1024)
def check_image(path, width):
    asset = Path(path)
    assert asset.parent == Path("assets") and asset.is_file(), asset
    fingerprint = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
    assert asset.name == f"hero-{fingerprint}.webp", asset
    with Image.open(asset) as image:
        image.load()
        assert image.format == "WEBP" and image.width == width
        assert image.height * size[0] == image.width * size[1]

candidates = {int(w.removesuffix("w")): name for name, w in (v.split() for v in hero["srcset"].split(","))}
assert candidates[size[0]] == hero["src"] and min(candidates) < size[0]
for width, path in candidates.items():
    check_image(path, width)

projects = {"devflow", "infra-portal", "sentinel", "qc-studio", "atlas", "as-field"}
media = Path("assets/projects")
assert {image["src"] for image in posters} == {(media / f"{name}.webp").as_posix() for name in projects}
assert {link["href"] for link in page.previews} == {(media / f"{name}.mp4").as_posix() for name in projects}
assert len(posters) == len(page.previews) == len(projects)
for poster, preview in zip(posters, page.previews):
    image_path, video_path = Path(poster["src"]), Path(preview["href"])
    assert image_path.stem == video_path.stem
    assert poster["loading"] == "lazy" and poster["alt"].strip()
    assert preview["aria-label"].strip()
    with Image.open(image_path) as image:
        image.load()
        assert image.format == "WEBP" and image.size == (int(poster["width"]), int(poster["height"]))
    with video_path.open("rb") as video:
        assert video.read(8)[4:] == b"ftyp"
