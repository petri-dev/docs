"""Run after `mkdocs build --strict`; requires Playwright and Chromium."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


root = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "site")))
Thread(target=server.serve_forever, daemon=True).start()

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()
        page.route("https://cdnjs.cloudflare.com/**", lambda route: route.fulfill(
            content_type="text/javascript" if route.request.url.endswith(".js") else "text/css",
            body="window.hljs = { highlightAll() {} };" if route.request.url.endswith(".js") else "",
        ))
        base = f"http://127.0.0.1:{server.server_port}"
        # Reviewed command-start line numbers for every published code block.
        # None means a data block (JSON/YAML), which must have no shell prompts.
        starts = {
            "quickstart": [[1, 2, 5], [1], [1, 4, 6], [1, 2], [1], [1], [1, 4], [1, 2], [1], [1, 2, 3], [1, 2]],
            "local-quickstart": [[1, 2], [1], [1, 2], [1], [1, 2], [1], [1], None, [1], [1], [1], [1], [1, 2, 3]],
            "operator/index": [[1]],
            "apiserver/index": [[1], None],
            "getting-started/http-api": [[1, 2], [1, 2], [1], [1], None, [1], [1], [1], None, [1], [1], [1, 2], [1], None],
        }
        sources = {
            source.relative_to(root / "docs").with_suffix("").as_posix()
            for source in (root / "docs").rglob("*.md")
            if "```" in source.read_text()
        }
        assert sources == set(starts), "Review prompt positions when adding or removing pages with code blocks"
        for source, expected in starts.items():
            route = source.removesuffix("/index")
            page.goto(base + f"/{route}/", wait_until="networkidle")
            codes = page.locator("main pre > code")
            assert codes.count() == len(expected), source
            for code, command_lines in zip(codes.all(), expected):
                prompts = code.get_attribute("data-prompts")
                if command_lines is None:
                    assert prompts is None, source
                else:
                    assert prompts is not None, source
                    assert len(prompts.split("\n")) == len(code.text_content().split("\n")), source
                    actual = [line for line, prompt in enumerate(prompts.split("\n"), 1) if prompt == "$"]
                    assert actual == command_lines, (source, code.text_content(), actual, command_lines)

        # The reported multiline JSON command must copy without display prompts.
        json_command = page.locator(".lab-code-block").filter(has_text='"ttl": "1h"').filter(has=page.locator("code.language-bash"))
        json_command.get_by_role("button").click()
        expect(json_command.get_by_role("status")).to_have_text("Copied!")
        assert page.evaluate("navigator.clipboard.readText()") == json_command.locator("code").text_content()

        page.goto(base + "/quickstart/", wait_until="networkidle")
        assert page.locator(".lab-code-copy").count() == page.locator("main pre > code").count()

        block = page.locator(".lab-code-block").filter(has_text="kind create cluster")
        code = block.locator("code")
        original = code.text_content()
        assert code.get_attribute("data-prompts").splitlines()[:5] == ["$", "$", "", "", "$"]
        assert code.evaluate("el => getComputedStyle(el, '::before').userSelect") == "none"
        selected = code.evaluate("""el => {
            const range = document.createRange();
            range.selectNodeContents(el);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            return selection.toString();
        }""")
        assert selected.rstrip("\n") == original.rstrip("\n"), "Selection must contain only the original source"
        button = block.get_by_role("button")
        page.mouse.move(0, 0)
        expect(button).to_have_css("opacity", "0")
        block.hover()
        expect(button).to_have_css("opacity", "1")
        page.mouse.move(0, 0)
        button.focus()
        expect(button).to_have_css("opacity", "1")
        page.keyboard.press("Enter")
        page.wait_for_function("() => document.querySelector('.lab-code-copy').dataset.state === 'copied'")
        assert page.evaluate("navigator.clipboard.readText()") == original
        expect(block.get_by_role("status")).to_have_text("Copied!")

        template = page.locator("code.language-bash").filter(has_text="kind: EnvironmentTemplate")
        prompts = template.get_attribute("data-prompts").splitlines()
        assert prompts[0] == "$"
        assert all(prompt == "" for prompt in prompts[1:]), "No prompts inside the YAML heredoc"
        template.locator("xpath=../..").get_by_role("button").click()
        expect(template.locator("xpath=../..").get_by_role("status")).to_have_text("Copied!")
        assert page.evaluate("navigator.clipboard.readText()") == template.text_content()

        page.evaluate("() => { navigator.clipboard.writeText = async () => { throw new Error('Denied'); }; }")
        button.click()
        page.wait_for_function("() => document.querySelector('.lab-code-copy').dataset.state === 'error'")

        page.goto(base + "/apiserver/", wait_until="networkidle")
        yaml = page.locator("code.language-yaml")
        assert yaml.count() > 0
        assert yaml.get_attribute("data-prompts") is None

        for theme in ("light", "dark"):
            page.evaluate("theme => document.documentElement.dataset.bsTheme = theme", theme)
            page.set_viewport_size({"width": 390, "height": 700})
            copy = page.locator(".lab-code-copy").first
            copy.scroll_into_view_if_needed()
            bounds = copy.bounding_box()
            assert bounds and bounds["x"] >= 0 and bounds["x"] + bounds["width"] <= 390
        touch = browser.new_context(has_touch=True, is_mobile=True, viewport={"width": 390, "height": 700})
        touch.route("https://cdnjs.cloudflare.com/**", lambda route: route.abort())
        mobile = touch.new_page()
        mobile.goto(base + "/quickstart/", wait_until="networkidle")
        expect(mobile.locator(".lab-code-copy").first).to_have_css("opacity", "1")
        assert mobile.locator(".lab-code-copy").first.bounding_box()["height"] >= 44

        # Quotes in comments/heredocs and escaped quotes must not leak into the next command.
        fixture = r'''# A comment with unmatched ' and "
printf '%s\n' 'first
second "quoted"
third'
printf '%s\n' "first \"quoted\"
second"
printf '%s\n' 'literal <<EOF'
cat <<'EOF'
raw 'quotes " \
EOF
printf '%s\n' done
'''
        page.set_content('<main><pre><code class="language-bash"></code></pre></main>')
        page.locator("code").evaluate("(code, text) => code.textContent = text", fixture)
        page.add_script_tag(path=str(root / "docs/javascripts/code.js"))
        prompts = page.locator("code").get_attribute("data-prompts").split("\n")
        assert [line for line, prompt in enumerate(prompts, 1) if prompt == "$"] == [2, 5, 7, 8, 11]
        browser.close()
        print(f"Code block checks passed: all {sum(map(len, starts.values()))} published blocks, multiline quotes, heredocs, selection, clipboard, keyboard, failure, and mobile themes.")
finally:
    server.shutdown()
    server.server_close()
