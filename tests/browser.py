from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from pypdf import PdfReader


def check_page(browser, url):
    with browser.new_context(viewport={"width": 320, "height": 720}, reduced_motion="reduce") as context:
        page = context.new_page()
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        devtools = context.new_cdp_session(page)
        for minimum in (0, 24):
            devtools.send("Page.setFontSizes", {"fontSizes": {"minimumFontSize": minimum}})
            page.goto(url)
            assert page.locator("nav a").last.bounding_box()["x"] >= 0
            assert page.locator("nav").evaluate("(nav) => nav.getBoundingClientRect().right <= innerWidth")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator(".hero-photo img").evaluate("(image) => image.complete && image.naturalWidth > 0")
        assert all(urlsplit(request).netloc == urlsplit(url).netloc for request in requests)
        for anchor in ("devflow", "auth-infra-portal", "sentinel"):
            page.goto("about:blank")
            page.goto(url + "#" + anchor)
            page.locator("#" + anchor).wait_for(state="visible")
            assert page.locator("#" + anchor).evaluate("(node) => node.getBoundingClientRect().top < innerHeight")
        page.goto(url)
        for opened in (False, True):
            page.locator("details").evaluate("(element, open) => { element.open = open }", opened)
            pdf = PdfReader(BytesIO(page.pdf()))
            text = "".join(sheet.extract_text() or "" for sheet in pdf.pages)
            assert "MCP" in text, "Printed Sentinel story missing"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    handler = partial(SimpleHTTPRequestHandler, directory=root)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server, sync_playwright() as playwright:
        Thread(target=server.serve_forever, daemon=True).start()
        browser = playwright.chromium.launch(channel="chrome")
        try:
            check_page(browser, f"http://127.0.0.1:{server.server_port}/")
        finally:
            browser.close()
            server.shutdown()
