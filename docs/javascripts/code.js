(() => {
  const icons = {
    copy: "M9 9h11v11H9z M5 15H3V3h12v2",
    copied: "m5 12 4 4L19 6",
    error: "M12 8v5 M12 17h.01 M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18",
  };
  for (const code of document.querySelectorAll("main pre > code")) {
    const text = code.textContent;
    const pre = code.parentElement;
    const block = document.createElement("div");
    block.className = "lab-code-block";
    pre.before(block);
    block.append(pre);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "lab-code-copy";
    button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path/></svg>';
    const status = document.createElement("span");
    status.className = "visually-hidden";
    status.setAttribute("role", "status");
    block.append(status);
    function feedback(state, label) {
      button.dataset.state = state;
      button.dataset.label = label;
      button.setAttribute("aria-label", label);
      button.querySelector("path").setAttribute("d", icons[state]);
      status.textContent = state === "copy" ? "" : label;
    }
    feedback("copy", "Copy code");
    block.prepend(button);
    let reset;
    button.addEventListener("click", async () => {
      clearTimeout(reset);
      try {
        await navigator.clipboard.writeText(text);
        feedback("copied", "Copied!");
      } catch {
        feedback("error", "Copy failed. Select text to copy.");
      }
      reset = setTimeout(() => feedback("copy", "Copy code"), 2000);
    });

    if (!code.matches(".language-bash, .language-sh, .language-shell")) continue;
    let continued = false;
    let heredoc = null;
    let quote = null;
    // ponytail: simple commands, multiline quotes, and one heredoc. Use explicit
    // prompt metadata if docs need compound scripts or nested shell substitutions.
    code.dataset.prompts = text.split("\n").map(line => {
      if (heredoc) {
        const candidate = heredoc[1] ? line.replace(/^\t+/, "") : line;
        if (candidate === heredoc[3]) heredoc = null;
        return "";
      }
      const prompt = !continued && !quote && line.trim() && !line.trimStart().startsWith("#") ? "$" : "";
      continued = false;
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === "\\" && quote !== "'") {
          continued = i === line.length - 1;
          i++;
        } else if (quote) {
          if (char === quote) quote = null;
        } else if (char === "#" && (i === 0 || /\s/.test(line[i - 1]))) {
          break;
        } else if (char === "'" || char === '"') {
          quote = char;
        } else if (char === "<" && line[i - 1] !== "<") {
          const match = line.slice(i).match(/^<<(-?)\s*(['"]?)([A-Za-z_]\w*)\2/);
          if (match) {
            heredoc = match;
            i += match[0].length - 1;
          }
        }
      }
      return prompt;
    }).join("\n");
  }
})();
