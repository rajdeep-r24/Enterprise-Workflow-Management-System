/**
 * Auto Code Generator Module
 * Listens to Name changes and fetches a code suggestion from the backend.
 * Supports manual override detection and manual regeneration.
 */

class AutoCodeGenerator {
    constructor(entityName) {
        this.entityName = entityName;
        this.nameInput = document.getElementById("id_name");
        this.codeInput = document.getElementById("id_code");
        this.manuallyEdited = false;
        this.debounceTimer = null;
        this.lastFetchedName = "";

        if (!this.nameInput || !this.codeInput) {
            console.warn("AutoCodeGenerator: Missing #id_name or #id_code input fields.");
            return;
        }

        this.init();
    }

    init() {
        // Wrap the code input with a container to add the refresh button
        const wrap = document.createElement("div");
        wrap.className = "ff-flex ff-gap-2 ff-items-center";
        
        this.codeInput.parentNode.insertBefore(wrap, this.codeInput);
        wrap.appendChild(this.codeInput);
        this.codeInput.style.flex = "1";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ff-btn ff-btn--ghost ff-btn--icon";
        btn.title = "Regenerate Code";
        btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
        wrap.appendChild(btn);

        // Events
        this.codeInput.addEventListener("input", () => {
            this.manuallyEdited = true;
            this.codeInput.dataset.manuallyEdited = "true";
        });

        this.nameInput.addEventListener("input", () => {
            if (!this.manuallyEdited && this.nameInput.value.trim() !== "") {
                this.scheduleGeneration();
            }
        });

        btn.addEventListener("click", () => {
            this.manuallyEdited = false;
            this.codeInput.dataset.manuallyEdited = "false";
            this.generateNow();
        });

        // Initialize state based on dataset
        if (this.codeInput.dataset.manuallyEdited === "true") {
            this.manuallyEdited = true;
        }
    }

    scheduleGeneration() {
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.generateNow();
        }, 500); // 500ms debounce
    }

    async generateNow() {
        const nameVal = this.nameInput.value.trim();
        if (!nameVal) {
            this.codeInput.value = "";
            return;
        }

        if (nameVal === this.lastFetchedName) return;

        try {
            // Include CSRF token
            const csrfToken = this.getCsrfToken();
            console.log("CSRF Token before fetch:", csrfToken, "Length:", csrfToken ? csrfToken.length : 0);
            
            const response = await fetch("/api/code-suggestion/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({
                    entity: this.entityName,
                    name: nameVal
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.suggested_code) {
                    if (!this.manuallyEdited) {
                        this.codeInput.value = data.suggested_code;
                        this.lastFetchedName = nameVal;
                    }
                }
            }
        } catch (err) {
            console.error("AutoCodeGenerator API Error:", err);
        }
    }

    getCsrfToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) {
            return csrfInput.value;
        }
        return "";
    }
}
