document.addEventListener("DOMContentLoaded", () => {
    console.log("app.js yüklendi ✅");

    const textInput = document.querySelector("#postText");
    const platformCheckboxes = document.querySelectorAll(
        "input[type='checkbox'][name='platforms']"
    );

    const scheduleRadios = document.querySelectorAll("input[name='scheduleMode']");
    const scheduledAtInput = document.querySelector("input[name='scheduled_at']");
    const mediaInput = document.getElementById("mediaInput");

    const allButtons = Array.from(document.querySelectorAll("button"));
    const saveDraftBtn = allButtons.find(btn =>
        btn.textContent.trim().includes("Taslak Olarak Kaydet")
    );
    const prepareBtn = allButtons.find(btn =>
        btn.textContent.trim().includes("Gönderiyi Hazırla")
    );

    const previewText =
        document.getElementById("preview-text") ||
        document.querySelector(".preview-text");
    const previewPlatforms =
        document.getElementById("preview-platforms") ||
        document.querySelector(".preview-platforms");
    const previewFormatTag = document.querySelector(".preview-format-tag");

    // --------------------------------------------------
    // Form verisini toparlayan fonksiyon
    // --------------------------------------------------
    function collectFormData() {
        const text = textInput ? textInput.value.trim() : "";

        const platforms = [];
        platformCheckboxes.forEach(cb => {
            if (cb.checked) {
                const label = cb.closest("label");
                const val = cb.value || (label && label.innerText.trim());
                if (val) platforms.push(val);
            }
        });

        let schedule_mode = "now";
        scheduleRadios.forEach(r => {
            if (r.checked) {
                schedule_mode = r.value || "now";
            }
        });

        const scheduled_at = scheduledAtInput ? (scheduledAtInput.value || "") : "";

        let media_files = [];
        if (mediaInput && mediaInput.files && mediaInput.files.length > 0) {
            media_files = Array.from(mediaInput.files).map(f => f.name);
        }

        // Format şimdilik sadece önizleme için
        let format = "Normal Gönderi";
        const formatRadio = document.querySelector("input[name='format']:checked");
        if (formatRadio) {
            const v = formatRadio.value;
            if (v === "reels") format = "Short / Reels";
            else if (v === "story") format = "Story";
        }

        return {
            text,
            platforms,
            schedule_mode,
            scheduled_at,
            media_files,
            format
        };
    }

    // --------------------------------------------------
    // Taslak kaydet butonu
    // --------------------------------------------------
    if (saveDraftBtn) {
        saveDraftBtn.addEventListener("click", async () => {
            const data = collectFormData();
            console.log("Taslak kaydet tıklandı:", data);

            try {
                const res = await fetch("/api/draft", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        text: data.text,
                        platforms: data.platforms,
                        schedule_mode: data.schedule_mode,
                        scheduled_at: data.scheduled_at,
                        media_files: data.media_files
                    })
                });

                const json = await res.json();
                console.log("API cevabı:", json);

                if (json.ok) {
                    window.location.href = "/drafts";
                } else {
                    alert("Taslak kaydedilirken bir hata oluştu.");
                }
            } catch (err) {
                console.error("Taslak kaydederken hata:", err);
                alert("Sunucuya ulaşılamadı.");
            }
        });
    }

    // --------------------------------------------------
    // Gönderiyi Hazırla -> önizleme
    // --------------------------------------------------
    if (prepareBtn) {
        prepareBtn.addEventListener("click", () => {
            const data = collectFormData();
            console.log("Gönderiyi Hazırla tıklandı:", data);

            if (previewText) {
                previewText.textContent =
                    data.text || "Gönderi metnin burada görünecek ✨";
            }

            if (previewPlatforms) {
                previewPlatforms.innerHTML = "";
                if (data.platforms.length === 0) {
                    previewPlatforms.textContent = "Platform seçilmedi";
                } else {
                    data.platforms.forEach(p => {
                        const span = document.createElement("span");
                        span.className = "pill-soft";
                        span.textContent = p;
                        previewPlatforms.appendChild(span);
                    });
                }
            }

            if (previewFormatTag && data.format) {
                previewFormatTag.textContent = data.format;
            }
        });
    }

    // --------------------------------------------------
    // Ölçek pill'lerini seçilebilir yapmak
    // --------------------------------------------------
    const ratioBlocks = document.querySelectorAll(".ratio-block");
    ratioBlocks.forEach(block => {
        const chips = block.querySelectorAll(".chip-small");
        chips.forEach(chip => {
            chip.classList.add("chip-selectable");
            chip.addEventListener("click", () => {
                chips.forEach(c => c.classList.remove("chip-selected"));
                chip.classList.add("chip-selected");
            });
        });
    });
});
