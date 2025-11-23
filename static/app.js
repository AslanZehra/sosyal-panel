// static/app.js

// --------------------------------------------------
// Yardımcı: mevcut dili bul
// --------------------------------------------------
function getCurrentLang() {
    const htmlTag = document.documentElement;
    return htmlTag.getAttribute("lang") || "tr";
}

// Formdaki seçili platformları oku
function getSelectedPlatforms() {
    const checked = Array.from(document.querySelectorAll('input[name="platforms"]:checked'));
    return checked.map(el => el.value);
}

// Küçük helper: API çağrısı
async function callApi(endpoint, payload) {
    const resp = await fetch(endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload || {})
    });

    if (!resp.ok) {
        let msg = "Bilinmeyen hata";
        try {
            const errData = await resp.json();
            msg = errData.error || msg;
        } catch (e) {}
        throw new Error(msg);
    }

    const data = await resp.json();
    return data;
}

// --------------------------------------------------
// DOM Hazır olduğunda
// --------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    const lang = getCurrentLang();

    // ---------- AI METİN ÖNER ----------
    const btnAiText = document.getElementById("btn-ai-text");
    const postTextArea = document.getElementById("post-text");

    if (btnAiText && postTextArea) {
        btnAiText.addEventListener("click", async () => {
            const originalLabel = btnAiText.innerText;
            btnAiText.disabled = true;
            btnAiText.innerText = "Üretiliyor...";

            try {
                const platforms = getSelectedPlatforms();
                const payload = {
                    lang: getCurrentLang(),
                    base_text: postTextArea.value || "",
                    platforms: platforms,
                    tone: "default" // ileride: "business", "fun", "romantic" vs.
                };

                const data = await callApi("/api/ai_text", payload);
                const suggestion = data.suggestion || "";

                if (!postTextArea.value.trim()) {
                    postTextArea.value = suggestion;
                } else {
                    postTextArea.value = postTextArea.value.trim() + "\n\n" + suggestion;
                }
            } catch (err) {
                alert("AI metin üretiminde hata: " + err.message);
            } finally {
                btnAiText.disabled = false;
                btnAiText.innerText = originalLabel;
            }
        });
    }

    // ---------- AI HASHTAG ÖNER ----------
    const btnAiHashtag = document.getElementById("btn-ai-hashtag");
    const hashtagsArea = document.getElementById("hashtags");

    if (btnAiHashtag && hashtagsArea) {
        btnAiHashtag.addEventListener("click", async () => {
            const originalLabel = btnAiHashtag.innerText;
            btnAiHashtag.disabled = true;
            btnAiHashtag.innerText = "Üretiliyor...";

            try {
                const platforms = getSelectedPlatforms();
                const payload = {
                    lang: getCurrentLang(),
                    base_text: hashtagsArea.value || "",
                    platforms: platforms
                };

                const data = await callApi("/api/ai_hashtags", payload);
                const suggestion = data.suggestion || "";

                if (!hashtagsArea.value.trim()) {
                    hashtagsArea.value = suggestion;
                } else {
                    hashtagsArea.value = hashtagsArea.value.trim() + " " + suggestion;
                }
            } catch (err) {
                alert("Hashtag üretiminde hata: " + err.message);
            } finally {
                btnAiHashtag.disabled = false;
                btnAiHashtag.innerText = originalLabel;
            }
        });
    }

    // ---------- ÖLÇEK SEÇİMİ ----------
    const aspectBadges = document.querySelectorAll(".aspect-badge");
    const aspectInput = document.getElementById("aspect-ratio-input");

    if (aspectBadges.length && aspectInput) {
        aspectBadges.forEach((badge) => {
            badge.addEventListener("click", () => {
                const value = badge.getAttribute("data-aspect") || "";

                // aktif class'ı güncelle
                aspectBadges.forEach(b => b.classList.remove("active"));
                badge.classList.add("active");

                // gizli input'u güncelle
                aspectInput.value = value;
            });
        });
    }
});
