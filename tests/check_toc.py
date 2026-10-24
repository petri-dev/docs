"""Run after `mkdocs build --strict`; requires Playwright and its Chromium browser."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(
    ("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "site"))
)
Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 600})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Syntax highlighting is unrelated to scroll tracking; keep this check offline.
        page.route(
            "https://cdnjs.cloudflare.com/**",
            lambda route: route.fulfill(
                content_type="text/javascript"
                if route.request.url.endswith(".js")
                else "text/css",
                body="window.hljs = { highlightAll() {} };"
                if route.request.url.endswith(".js")
                else "",
            ),
        )

        def expect_section(anchor):
            page.wait_for_function(
                """anchor => {
              const links = document.querySelectorAll('.bs-sidebar a.active');
              return links.length === 1 && links[0].hash === anchor
                && links[0].getAttribute('aria-current') === 'location';
            }""",
                arg=anchor,
            )

        page.goto(base, wait_until="networkidle")
        top_nav = page.locator(".petri-top-nav")
        assert top_nav.locator(".dropdown-toggle, .dropdown-menu").count() == 0
        # Header edges stay aligned as the viewport grows, including around the mobile breakpoint.
        for route, theme in (("/", "light"), ("/", "dark"), ("/quickstart/", "light"), ("/quickstart/", "dark")):
            page.goto(base + route, wait_until="networkidle")
            page.evaluate("theme => document.documentElement.dataset.bsTheme = theme", theme)
            for width in (320, 390, 768, 991, 992, 1024, 1280, 1440, 1920, 2560, 3840):
                page.set_viewport_size({"width": width, "height": 900})
                bounds = page.evaluate("""() => {
                    const header = document.querySelector('body > .navbar');
                    const container = header.querySelector(':scope > .container');
                    const brand = header.querySelector('.navbar-brand').getBoundingClientRect();
                    const control = header.querySelector(innerWidth < 992 ? '.navbar-toggler' : '#theme-menu').getBoundingClientRect();
                    const padding = parseFloat(getComputedStyle(container).paddingLeft);
                    const links = [...header.querySelectorAll('.petri-top-nav .nav-link')].map(link => link.getBoundingClientRect());
                    const search = header.querySelector('[aria-label="Search documentation"]').getBoundingClientRect();
                    return {
                        fluid: Math.abs(container.getBoundingClientRect().width - document.documentElement.clientWidth) < 1,
                        left: Math.abs(brand.left - padding) < 1,
                        right: Math.abs(document.documentElement.clientWidth - control.right - padding) < 1,
                        singleRow: links.every(link => Math.abs(link.top - links[0].top) < 1) && links.at(-1).right <= search.left,
                        overflow: document.documentElement.scrollWidth > innerWidth,
                    };
                }""")
                assert bounds["fluid"] and bounds["left"] and bounds["right"], (theme, width, bounds)
                assert not bounds["overflow"], (theme, width, bounds)
                if width >= 992:
                    assert bounds["singleRow"], (theme, width, bounds)
                    expect(page.get_by_role("button", name="Toggle navigation", exact=True)).not_to_be_visible()
                else:
                    toggle = page.get_by_role("button", name="Toggle navigation", exact=True)
                    toggle.click()
                    expect(page.locator("#navbar-collapse")).to_have_class("navbar-collapse collapse show")
                    expect(top_nav.get_by_role("link", name="Contributing", exact=True)).to_be_visible()
                    expect(page.get_by_role("button", name="Search documentation", exact=True)).to_be_visible()
                    toggle.click()
                    expect(top_nav).not_to_be_visible()
        page.set_viewport_size({"width": 1280, "height": 600})
        page.evaluate("document.documentElement.dataset.bsTheme = 'light'")
        sections = {
            "Get started": "getting-started",
            "Concepts": "concepts",
            "Guides": "guides",
            "Operations": "operations",
            "Reference": "reference",
            "Contributing": "contributing",
        }
        for title, route in sections.items():
            top_nav.get_by_role("link", name=title, exact=True).click()
            expect(page).to_have_url(base + f"/{route}/")
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
            expect(page.get_by_role("navigation", name=f"{title} chapters")).to_be_visible()
            expect(top_nav.get_by_role("link", name=title, exact=True)).to_have_attribute("aria-current", "page")
            assert page.locator(".petri-section-index a").count() > 0
            assert page.locator(".petri-chapters details:not([open])").count() == 0

        top_nav.get_by_role("link", name="Get started", exact=True).click()
        quickstarts = page.locator(".petri-chapters details").filter(has=page.locator("summary", has_text="Quickstarts"))
        expect(quickstarts.get_by_role("link")).to_have_text([
            "Your first environment", "Run the API server locally",
        ])
        quickstarts.get_by_role("link", name="Run the API server locally", exact=True).click()
        expect(page).to_have_url(base + "/local-quickstart/")
        expect(top_nav.get_by_role("link", name="Get started", exact=True)).to_have_class("nav-link active")
        page.locator("main").get_by_role("link", name="Manage environments through the HTTP API", exact=True).click()
        expect(page).to_have_url(base + "/getting-started/http-api/")
        expect(top_nav.get_by_role("link", name="Guides", exact=True)).to_have_class("nav-link active")
        api_chapter = page.locator(".petri-chapters details[open]").filter(has=page.locator("summary", has_text="API server"))
        expect(api_chapter.locator("summary")).to_have_text("API server")
        expect(api_chapter.locator('a[aria-current="page"]')).to_have_text("Manage environments through the HTTP API")

        top_nav.get_by_role("link", name="Guides", exact=True).click()
        chapter = page.locator(".petri-chapters details").filter(has=page.locator("summary", has_text="Shared infrastructure"))
        provider_link = chapter.get_by_role("link", name="Write a shared-component provider")
        expect(provider_link).to_be_visible()
        chapter.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(provider_link).not_to_be_visible()
        page.keyboard.press("Space")
        expect(provider_link).to_be_visible()
        provider_link.click()
        expect(page).to_have_url(base + "/guides/provider-authoring/")
        expect(provider_link).to_have_attribute("aria-current", "page")
        expect(provider_link).to_be_visible()
        assert page.locator(".petri-chapters details:not([open])").count() == 0
        expect(top_nav.get_by_role("link", name="Guides", exact=True)).to_have_class("nav-link active")

        # Both navigation levels remain usable on a narrow screen.
        page.set_viewport_size({"width": 390, "height": 700})
        page.get_by_role("button", name="Toggle navigation", exact=True).click()
        top_nav.get_by_role("link", name="Reference", exact=True).click()
        expect(page).to_have_url(base + "/reference/")
        page.get_by_role("button", name="Chapters", exact=True).click()
        page.locator(".petri-chapters").get_by_role("link", name="EphemeralEnvironment", exact=True).click()
        expect(page).to_have_url(base + "/reference/kubernetes/ephemeral-environment/")
        page.get_by_role("button", name="Chapters", exact=True).click()
        expect(page.locator('.petri-chapters a[aria-current="page"]')).to_have_text("EphemeralEnvironment")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.set_viewport_size({"width": 1280, "height": 600})

        page.goto(base + "/local-quickstart/", wait_until="networkidle")
        expect_section("#run-the-api-server-locally")
        for anchor in ("check-the-existing-cluster", "run-the-api-server"):
            page.locator(f"main #{anchor}").evaluate("""heading => {
              const header = document.querySelector('body > .navbar');
              window.scrollTo(0, scrollY + heading.getBoundingClientRect().top
                - header.getBoundingClientRect().bottom - 8);
            }""")
            expect_section("#" + anchor)

        # Keep the long section selected after its heading has left the viewport.
        page.evaluate("window.scrollBy(0, 150)")
        expect_section("#run-the-api-server")
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        expect_section("#cleanup")
        page.evaluate("window.scrollTo(0, 0)")
        expect_section("#run-the-api-server-locally")
        page.locator('.bs-sidebar a[href="#run-the-api-server"]').click()
        expect_section("#run-the-api-server")
        # Load the deep link in a fresh document rather than interrupting anchor scrolling.
        page.goto(base, wait_until="networkidle")
        page.goto(
            base + "/local-quickstart/#check-the-existing-cluster", wait_until="networkidle"
        )
        expect_section("#check-the-existing-cluster")
        page.set_viewport_size({"width": 390, "height": 600})
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        expect_section("#cleanup")
        page.set_viewport_size({"width": 1280, "height": 600})
        for route, first, last in (
            ("quickstart", "#quickstart", "#cleanup"),
            ("learn", "#the-concept-of-petri", "#try-it-locally"),
            ("operator", "#operator", "#installation-and-examples"),
            ("apiserver", "#api-server", "#github-actions-oidc"),
        ):
            page.goto(base + f"/{route}/", wait_until="networkidle")
            expect_section(first)
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            expect_section(last)
        page.goto(base, wait_until="networkidle")
        assert page.locator(".bs-sidebar").count() == 0
        expect(page.locator(".lab-hero")).to_be_visible()
        assert page.locator(".petri-architecture").count() == 0
        assert page.locator(".lab-hero-actions .lab-button").count() == 2
        page.get_by_role("link", name="Learn More", exact=True).click()
        expect(page).to_have_url(base + "/learn/")
        expect(
            page.get_by_role("heading", name="Core concepts", exact=True)
        ).to_be_visible()
        assert page.get_by_role("heading", name="FAQ", exact=True).count() == 1
        questions = page.locator("details.petri-faq")
        assert questions.count() == 6
        assert page.locator("details.petri-faq[open]").count() == 0
        questions.nth(0).locator("summary").click()
        questions.nth(1).locator("summary").click()
        expect(questions.nth(0).locator("p")).to_be_visible()
        expect(questions.nth(1).locator("p")).to_be_visible()
        questions.nth(0).locator("summary").focus()
        page.keyboard.press("Enter")
        expect(questions.nth(0).locator("p")).not_to_be_visible()
        expect(questions.nth(1).locator("p")).to_be_visible()
        page.keyboard.press("Space")
        expect(questions.nth(0).locator("p")).to_be_visible()
        page.get_by_role("link", name="View the architecture", exact=True).click()
        expect(page).to_have_url(base + "/architecture/")
        assert page.locator(".bs-sidebar").count() == 0
        expect(page.locator(".petri-blueprint-header")).to_be_visible()
        expect(page.get_by_label("Diagram legend")).to_be_visible()
        diagram = page.get_by_role(
            "navigation", name="Petri architecture and component documentation"
        )
        nodes = diagram.locator("a.petri-node")
        assert nodes.count() == 7
        assert diagram.locator(".petri-namespace").count() == 1
        destinations = nodes.evaluate_all(
            "links => links.map(link => new URL(link.getAttribute('href'), document.baseURI).href)"
        )
        for theme in ("light", "dark"):
            page.evaluate(
                "theme => document.documentElement.dataset.bsTheme = theme", theme
            )
            for width in (1440, 1024, 768, 390):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                for node in nodes.all():
                    node.scroll_into_view_if_needed()
                    bounds = node.bounding_box()
                    assert bounds and bounds["width"] > 100 and bounds["height"] >= 44
                    assert bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= width
                    assert node.evaluate(
                        "el => el.querySelector('text').getBBox().width < el.querySelector('rect').getBBox().width - 12"
                    )
        page.set_viewport_size({"width": 1280, "height": 600})
        nodes.first.focus()
        page.keyboard.press("Tab")
        expect(nodes.nth(1)).to_be_focused()
        page.keyboard.press("Enter")
        expect(page).to_have_url(destinations[1])
        for destination in destinations:
            response = page.goto(destination, wait_until="networkidle")
            assert response is None or response.ok
            assert page.evaluate(
                "!location.hash || !!document.getElementById(decodeURIComponent(location.hash.slice(1)))"
            )
        for route in ("/", "/quickstart/", "/architecture/"):
            page.goto(base + route, wait_until="networkidle")
            modal = page.locator("#mkdocs_search_modal")
            query = page.locator("#mkdocs-search-query")
            page.keyboard.press("k")
            expect(modal).not_to_be_visible()
            for shortcut in ("Meta+k", "Control+k"):
                page.keyboard.press(shortcut)
                expect(query).to_be_focused()
                query.fill("nginx")
                page.keyboard.press(shortcut)
                expect(query).to_be_focused()
                expect(query).to_have_value("nginx")
                assert page.locator(".modal-backdrop").count() == 1
                page.keyboard.press("Escape")
                expect(modal).not_to_be_visible()
                expect(
                    page.get_by_role("button", name="Search documentation", exact=True)
                ).to_be_focused()
        assert not errors, errors
        browser.close()
        print(
            "Navigation checks passed: section links, landing pages, collapsible chapters, active paths, architecture, TOC, mobile, keyboard, and search."
        )
finally:
    server.shutdown()
    server.server_close()
