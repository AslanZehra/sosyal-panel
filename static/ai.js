// static/ai.js
(function () {
    const postText = document.getElementById("post-text");
    const hashtagsEl = document.getElementById("hashtags");
  
    const btnAiText = document.getElementById("btn-ai-text");
    const btnAiHashtag = document.getElementById("btn-ai-hashtag");
  
    if (!postText || !hashtagsEl || !btnAiText || !btnAiHashtag) return;

    function getLang() {
      return localStorage.getItem("lang") || "tr";
    }

    function tr(key, fallback) {
      if (typeof window.t === "function") {
        return window.t(key, getLang());
      }
      return fallback;
    }
  
    function getSelectedPlatform() {
      const checked = document.querySelector('input[name="platforms"]:checked');
      return checked ? checked.value : "instagram";
    }
  
    function getSelectedFormat() {
      const checked = document.querySelector('input[name="format"]:checked');
      return checked ? checked.value : "normal";
    }
  
    async function postJSON(url, payload) {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data?.error || "request_failed");
      return data;
    }
  
    btnAiText.addEventListener("click", async () => {
      const topic = (postText.value || "").trim();
      if (!topic) { alert(tr("alert_write_brief_first", "Önce gönderi metni/brief yaz.")); return; }
  
      btnAiText.disabled = true;
      try {
        const data = await postJSON("/api/ai/text", {
          topic,
          tone: "samimi",
          platform: getSelectedPlatform(),
          format: getSelectedFormat(),
          language: getLang(),
        });
        postText.value = data.text || topic;
      } catch (e) {
        alert(tr("alert_ai_text_error", "AI metin hatası: ") + e.message);
      } finally {
        btnAiText.disabled = false;
      }
    });
  
    btnAiHashtag.addEventListener("click", async () => {
      const fromPost = (postText.value || "").trim();
      const fromHashtags = (hashtagsEl.value || "").replace(/#/g, " ").trim();
      let base = (fromPost || fromHashtags || "").slice(0, 500);

      if (!base) {
        const typedTopic = window.prompt(
          tr("prompt_topic_short", "Kısa konu yaz (ör: kahve dükkanı açılışı):"),
          ""
        );
        base = (typedTopic || "").trim().slice(0, 500);
      }

      if (!base) { alert(tr("alert_hashtag_need_topic", "Hashtag önerisi için kısa bir konu/metin gir.")); return; }
  
      btnAiHashtag.disabled = true;
      try {
        const data = await postJSON("/api/ai/hashtags", {
          topic: base,
          platform: getSelectedPlatform(),
          limit: 12,
        });
        hashtagsEl.value = (data.hashtags || []).join(" ");
      } catch (e) {
        alert(tr("alert_ai_hashtag_error", "AI hashtag hatası: ") + e.message);
      } finally {
        btnAiHashtag.disabled = false;
      }
    });
  })();
  
