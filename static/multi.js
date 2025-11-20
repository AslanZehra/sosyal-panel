document.addEventListener("DOMContentLoaded", () => {
    // --- ELEMENTLERİ TOPLA ---
    const checkboxInstagram = document.getElementById("instagram");
    const checkboxFacebook = document.getElementById("facebook");
    const checkboxTwitter = document.getElementById("twitter");
    const checkboxYouTube = document.getElementById("youtube");
    const checkboxTikTok = document.getElementById("tiktok");

    const formatButtons = document.querySelectorAll(".format-btn");
    const textArea = document.getElementById("postText");
    const mediaInput = document.getElementById("mediaInput");

    const modeRadios = document.querySelectorAll("input[name='mode']");
    const scheduleInput = document.getElementById("scheduleTime");

    const prepareBtn = document.getElementById("prepareBtn");
    const saveDraftBtn = document.getElementById("saveDraft");
    const previewBox = document.getElementById("livePreview");

    // --- DURUM NESNESİ ---
    const state = {
        platforms: [],
        format: "normal",
        text: "",
        mediaFiles: [],
        mode: "now",
        schedule: null
    };

    // ---------------------------------------------------
    //  YARDIMCI FONKSİYONLAR
    // ---------------------------------------------------

    function collectSelectedPlatforms() {
        const platforms = [];
        if (checkboxInstagram.checked) platforms.push("instagram");
        if (checkboxFacebook.checked) platforms.push("facebook");
        if (checkboxTwitter.checked) platforms.push("twitter");
        if (checkboxYouTube.checked) platforms.push("youtube");
        if (checkboxTikTok.checked) platforms.push("tiktok");
        return platforms;
    }

    function getSelectedMode() {
        let mode = "now";
        modeRadios.forEach(r => {
            if (r.checked) {
                mode = r.value;
            }
        });
        return mode;
    }

    function updateScheduleInputState() {
        const mode = getSelectedMode();
        if (mode === "schedule") {
            scheduleInput.disabled = false;
        } else {
            scheduleInput.disabled = true;
            scheduleInput.value = "";
        }
    }

    function updatePreview() {
        const platforms = collectSelectedPlatforms();
        const formatText =
            state.format === "reels"
                ? "Short / Reels"
                : state.format === "story"
                ? "Story"
                : "Normal Gönderi";

        const mediaName = state.mediaFiles.length > 0 ? state.mediaFiles[0] : "Medya seçilmedi";

        let line1 =
            platforms.length > 0
                ? platforms.join(", ")
                : "Platform seçilmedi";

        const mode = getSelectedMode();
        let timingText = "";
        if (mode === "now") {
            timingText = "• Şimdi paylaşılacak";
        } else if (mode === "schedule" && scheduleInput.value) {
            timingText = "• Planlı: " + scheduleInput.value;
        } else {
            timingText = "• Planlı (tarih seçilmedi)";
        }

        previewBox.innerHTML = `
            <div style="font-size: 13px; opacity: 0.8; margin-bottom: 4px;">
                ${line1} — ${formatText} ${timingText}
            </div>
            <div style="margin-bottom: 8px; white-space: pre-wrap;">
                ${state.text || "Gönderi metni burada görünür."}
            </div>
            <div style="font-size: 12px; opacity: 0.7;">
                ${mediaName}
            </div>
        `;
    }

    function buildPayload() {
        const platforms = collectSelectedPlatforms();
        const mode = getSelectedMode();
        let scheduleValue = null;

        if (mode === "schedule" && scheduleInput.value) {
            scheduleValue = scheduleInput.value; // şimdilik string olarak yolluyoruz
        }

        return {
            platforms: platforms,
            format: state.format,
            text: state.text,
            media: state.mediaFiles,      // sadece dosya isimleri
            mode: mode,                   // "now" veya "schedule"
            schedule: scheduleValue       // null veya "2025-11-17T12:30"
        };
    }

    function showToast(message) {
        // Çok basit geçici bir bildirim
        alert(message);
    }

    // ---------------------------------------------------
    //  EVENTLER
    // ---------------------------------------------------

    // Format butonları (Normal / Reels / Story)
    formatButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            formatButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            state.format = btn.dataset.format || "normal";
            updatePreview();
        });
    });

    // Başlangıçta ilk butonu aktif yap
    if (formatButtons.length > 0) {
        formatButtons[0].classList.add("active");
    }

    // Metin değişince
    textArea.addEventListener("input", () => {
        state.text = textArea.value;
        updatePreview();
    });

    // Media seçimi
    mediaInput.addEventListener("change", () => {
        const files = Array.from(mediaInput.files || []);
        state.mediaFiles = files.map(f => f.name);
        updatePreview();
    });

    // Platformlar değişince
    [checkboxInstagram, checkboxFacebook, checkboxTwitter, checkboxYouTube, checkboxTikTok]
        .forEach(cb => {
            cb.addEventListener("change", () => {
                updatePreview();
            });
        });

    // Zamanlama modu değişince
    modeRadios.forEach(r => {
        r.addEventListener("change", () => {
            updateScheduleInputState();
            updatePreview();
        });
    });

    // Tarih saat seçimi
    scheduleInput.addEventListener("change", () => {
        updatePreview();
    });

    // Gönderiyi Hazırla → backend'e POST
    prepareBtn.addEventListener("click", async () => {
        const payload = buildPayload();

        if (payload.platforms.length === 0) {
            showToast("En az bir platform seçmelisin.");
            return;
        }

        if (!payload.text && payload.media.length === 0) {
            showToast("Metin veya medya eklemelisin.");
            return;
        }

        if (payload.mode === "schedule" && !payload.schedule) {
            showToast("Planlı paylaşım için tarih/saat seçmelisin.");
            return;
        }

        try {
            const res = await fetch("/api/publish", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (data.ok) {
                showToast("Gönderi backend'e başarıyla iletildi. (Simülasyon)");
            } else {
                console.error("Backend hata:", data);
                showToast("Backend bir hata döndürdü.");
            }
        } catch (err) {
            console.error("İstek hatası:", err);
            showToast("Sunucuya ulaşırken hata oluştu.");
        }
    });

    // Taslak olarak kaydet → localStorage
    saveDraftBtn.addEventListener("click", () => {
        const payload = buildPayload();

        const draftsKey = "mysocial_drafts";
        const existing = localStorage.getItem(draftsKey);
        let arr = [];
        if (existing) {
            try {
                arr = JSON.parse(existing);
                if (!Array.isArray(arr)) arr = [];
            } catch (e) {
                arr = [];
            }
        }

        const draft = {
            ...payload,
            savedAt: new Date().toISOString()
        };

        arr.push(draft);
        localStorage.setItem(draftsKey, JSON.stringify(arr));
        showToast("Taslak yerel olarak kaydedildi (localStorage).");
    });

    // Başlangıçta preview'ı güncelle ve schedule input'u disable et
    updateScheduleInputState();
    updatePreview();
});
