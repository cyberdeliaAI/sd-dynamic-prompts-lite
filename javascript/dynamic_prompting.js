/* global gradioApp, get_uiCurrentTabContent, onUiUpdate, onUiLoaded */
// prettier-ignore
const SDDP_HELP_TEXTS = {
  "sddp-dynamic-prompts-enabled": "Complete documentation is available at https://github.com/adieyal/sd-dynamic-prompts. Please report any issues on GitHub.",
  "sddp-is-combinatorial": "Generate all possible prompt combinations.",
  "sddp-is-fixed-seed": "Use the same seed for all prompts in this batch",
  "sddp-no-image-generation": "Disable image generation. Useful if you only want to generate text prompts. (1 image will still be generated to keep Auto1111 happy.).",
  "sddp-unlink-seed-from-prompt": "If this is set, then random prompts are generated, even if the seed is the same.",
};

class SDDPTreeView {
  constructor(data, node) {
    this.handlers = {};
    this.node = node;
    this.data = data;
    this.render();
  }

  render = () => {
    const container = this.node;
    container.innerHTML = "";
    this.data.forEach((item) => container.appendChild(this.renderNode(item)));
    [...container.querySelectorAll(".tree-leaf-text,.tree-expando")].forEach(
      (node) => node.addEventListener("click", this.handleClickEvent),
    );
  };

  renderNode = (item) => {
    const leaf = document.createElement("div");
    const content = document.createElement("div");
    const text = document.createElement("div");
    const expando = document.createElement("div");
    leaf.setAttribute("class", "tree-leaf");
    content.setAttribute("class", "tree-leaf-content");
    text.setAttribute("class", "tree-leaf-text");
    const { children, name, expanded } = item;
    text.textContent = name;
    expando.setAttribute("class", `tree-expando ${expanded ? "expanded" : ""}`);
    expando.textContent = expanded ? "-" : "+";
    content.appendChild(expando);
    content.appendChild(text);
    leaf.appendChild(content);
    if (children?.length > 0) {
      const childrenDiv = document.createElement("div");
      childrenDiv.setAttribute("class", "tree-child-leaves");
      children.forEach((child) => {
        childrenDiv.appendChild(this.renderNode(child));
      });
      if (!expanded) {
        childrenDiv.classList.add("hidden");
      }
      leaf.appendChild(childrenDiv);
    } else {
      expando.classList.add("hidden");
      content.setAttribute("data-item", JSON.stringify(item));
    }
    return leaf;
  };

  handleClickEvent = (event) => {
    const parent = (event.target || event.currentTarget).parentNode;
    const leaves = parent.parentNode.querySelector(".tree-child-leaves");
    if (leaves) {
      this.setSubtreeVisibility(
        parent,
        leaves,
        leaves.classList.contains("hidden"),
      );
    } else {
      this.emit("select", {
        target: event,
        data: JSON.parse(parent.getAttribute("data-item")),
      });
    }
  };

  setSubtreeVisibility(node, leaves, visible, skipEmit = false) {
    leaves.classList.toggle("hidden", !visible);
    node.querySelector(".tree-expando").textContent = visible ? "+" : "-";
    if (skipEmit) {
      return;
    }
    this.emit(visible ? "expand" : "collapse", {
      target: node,
      leaves,
    });
  }

  on(name, callback, context = null) {
    const handlers = this.handlers[name] || [];
    handlers.push({ callback, context });
    this.handlers[name] = handlers;
  }

  off(name, callback) {
    this.handlers[name] = (this.handlers[name] || []).filter(
      (handle) => handle.callback !== callback,
    );
  }

  emit(name, ...args) {
    (this.handlers[name] || []).forEach((handle) => {
      window.setTimeout(() => {
        handle.callback.apply(handle.context, args);
      }, 0);
    });
  }
}

class SDDP_UI {
  constructor() {
    this.helpTextsConfigured = false;
    this.wildcardsLoaded = false;
    this.searchKeyConfigured = false;
    this.messageReadTimer = null;
    this.lastMessage = null;
    this.treeView = null;
    this.treeContent = null;
    this.collectionCount = 0;
    this.treeFilter = null;
  }

  configureHelpTexts() {
    if (this.helpTextsConfigured) {
      return;
    }
    for (const elemId in SDDP_HELP_TEXTS) {
      const elem = gradioApp().getElementById(elemId);
      if (elem) {
        elem.setAttribute("title", SDDP_HELP_TEXTS[elemId]);
      } else {
        return;
      }
    }
    this.helpTextsConfigured = true;
  }

  getInboxMessageText() {
    return gradioApp().querySelector(
      "#sddp-wildcard-s2c-message-textbox textarea",
    )?.value;
  }

  formatPayload(payload) {
    return JSON.stringify({ ...payload, id: Math.floor(+new Date()) }, null, 2);
  }

  sendAction(payload) {
    const outbox = gradioApp().querySelector(
      "#sddp-wildcard-c2s-message-textbox textarea",
    );
    outbox.value = this.formatPayload(payload);
    window.updateInput?.(outbox);
    gradioApp().querySelector("#sddp-wildcard-c2s-action-button").click();
  }

  requestWildcardTree() {
    gradioApp().querySelector("#sddp-wildcard-load-tree-button")?.click();
  }

  doReadMessage() {
    const messageText = this.getInboxMessageText();
    if (!messageText || this.lastMessage === messageText) {
      return;
    }
    this.lastMessage = messageText;
    const message = JSON.parse(messageText);
    const { action, success } = message;
    if (action === "load tree" && success) {
      this.treeContent = message.tree;
      this.collectionCount = message.collection_count ?? 0;
      this.setupTree();
    } else if (action === "load file" && success) {
      this.loadFileIntoEditor(message);
    } else {
      console.warn("SDDP: Unknown message", message);
    }
  }

  setupTree() {
    let { treeView } = this;
    const { treeContent: content, treeFilter: filter } = this;
    if (!content) {
      return;
    }
    const filteredContent = this.filterTreeContent(content, filter);
    if (!this.treeView) {
      const treeDiv = gradioApp().querySelector("#sddp-wildcard-tree");
      if (treeDiv) {
        treeView = new SDDPTreeView(filteredContent, treeDiv);
        treeView.on("select", this.onSelectNode.bind(this), null);
        this.treeView = treeView;
      }
    } else {
      treeView.data = filteredContent;
      treeView.render();
    }
  }

  onSelectNode(node) {
    if (node.data?.name) {
      this.sendAction({
        action: "load file",
        name: node.data.name,
      });
    }
  }

  loadFileIntoEditor(message) {
    const editor = gradioApp().querySelector(
      "#sddp-wildcard-file-editor textarea",
    );
    const name = gradioApp().querySelector("#sddp-wildcard-file-name textarea");
    const { contents, wrapped_name: wrappedName } = message;
    editor.value = contents;
    name.value = wrappedName;
    editor.readOnly = true;

    window.updateInput?.(editor);
    window.updateInput?.(name);
  }

  onWildcardManagerTabActivate() {
    if (!this.wildcardsLoaded) {
      this.requestWildcardTree();
      this.wildcardsLoaded = true;
    }
    if (!this.messageReadTimer) {
      this.messageReadTimer = setInterval(this.doReadMessage.bind(this), 120);
    }
    if (!this.searchKeyConfigured) {
      const debouncedSearch = this.debounce(
        (event) => {
          this.treeFilter = event.target.value?.trim() || null;
          this.setupTree();
        },
        () => (this.collectionCount > 5000 ? 500 : 50),
        this,
      );
      gradioApp()
        .querySelector("#sddp-wildcard-search textarea")
        ?.addEventListener("input", debouncedSearch);
      this.searchKeyConfigured = true;
    }
  }

  filterTreeContent = (content, filter) => {
    if (!filter?.length) {
      return content;
    }
    filter = filter.toLowerCase();

    const filteredContent = [];
    function walk(node) {
      if (node.children?.length) {
        node.children.forEach(walk);
      } else if (node.name?.toLowerCase().includes(filter)) {
        filteredContent.push(node);
      }
    }
    content.forEach(walk);
    return filteredContent;
  };

  debounce(handler, timeFunction, context) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => handler.apply(context, args), timeFunction());
    };
  }
}

const SDDP = new SDDP_UI();
window.SDDP = SDDP;

(
  window.onAfterUiUpdate || // sd-webui 1.3.0+
  window.onUiUpdate
)(() => {
  SDDP.configureHelpTexts();
  const currentVisibleTopLevelTab = gradioApp().querySelector(
    '#tabs > .tabitem[id^=tab_]:not([style*="display: none"])',
  );
  if (currentVisibleTopLevelTab?.id === "tab_sddp-wildcard-manager") {
    SDDP.onWildcardManagerTabActivate();
  }
});
