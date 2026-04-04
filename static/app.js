(function () {
  const modeSel = document.getElementById("schedule-mode");
  const oneShotWrap = document.getElementById("one-shot-wrap");
  const intervalWrap = document.getElementById("interval-wrap");
  const campaignWrap = document.getElementById("campaign-wrap");
  const actionField = document.getElementById("action-field");
  const btnDraft = document.getElementById("btn-save-draft");
  const btnSubmit = document.getElementById("btn-submit-post");

  const mediaInput = document.getElementById("media-input");
  const mediaRadios = document.querySelectorAll('input[name="media_mode"]');
  const formatRadios = document.querySelectorAll('input[name="format"]');
  const platformBoxes = document.querySelectorAll('input[name="platforms"]');
  const mediaSelectionInfo = document.getElementById("media-selection-info");
  const mediaSelectionList = document.getElementById("media-selection-list");
  const mediaModeNote = document.getElementById("media-mode-note");
  const formatPlatformNote = document.getElementById("format-platform-note");

  const stagedFiles = [];
  const canStageFiles = typeof DataTransfer !== "undefined";

  function fileKey(f) {
    return `${f.name}::${f.size}::${f.lastModified}`;
  }

  function getCurrentFormat() {
    const checked = document.querySelector('input[name="format"]:checked');
    return checked ? checked.value : "normal";
  }

  function getCurrentMediaMode() {
    const checked = document.querySelector('input[name="media_mode"]:checked');
    return checked ? checked.value : "mixed";
  }

  function isImageFile(file) {
    const t = (file.type || "").toLowerCase();
    return t.startsWith("image/");
  }

  function isVideoFile(file) {
    const t = (file.type || "").toLowerCase();
    return t.startsWith("video/");
  }

  function canUseFileByMode(file, mode) {
    if (mode === "image") return isImageFile(file);
    if (mode === "video") return isVideoFile(file);
    return isImageFile(file) || isVideoFile(file);
  }

  function setModeUI(mode) {
    if (!oneShotWrap || !intervalWrap) return;
    const m = mode || "now";
    oneShotWrap.style.display = m === "one_shot" ? "" : "none";
    intervalWrap.style.display = m === "interval" ? "" : "none";
    if (campaignWrap) campaignWrap.style.display = m === "campaign" ? "" : "none";
  }

  function setMediaAccept() {
    if (!mediaInput) return;
    const mode = getCurrentMediaMode();

    if (mode === "image") mediaInput.accept = "image/*";
    else if (mode === "video") mediaInput.accept = "video/*";
    else mediaInput.accept = "image/*,video/*";
  }

  function syncStagedFilesToInput() {
    if (!mediaInput || !canStageFiles) return;
    const dt = new DataTransfer();
    stagedFiles.forEach((f) => dt.items.add(f));
    mediaInput.files = dt.files;
  }

  function renderStagedFiles() {
    if (!mediaSelectionInfo || !mediaSelectionList) return;
    if (!stagedFiles.length) {
      mediaSelectionInfo.textContent = "Henüz medya seçilmedi.";
      mediaSelectionList.textContent = "";
      return;
    }

    mediaSelectionInfo.textContent = `${stagedFiles.length} medya seçildi.`;
    mediaSelectionList.textContent = stagedFiles.map((f) => f.name).join(" • ");
  }

  function enforceMediaConstraints() {
    const mode = getCurrentMediaMode();
    const fmt = getCurrentFormat();

    if (mediaInput) {
      mediaInput.multiple = fmt !== "story";
    }

    if (mediaModeNote) {
      if (fmt === "story") {
        mediaModeNote.textContent = "Story için tek fotoğraf veya tek video seçebilirsin.";
      } else {
        mediaModeNote.textContent = "Normal/Short modunda birden fazla medya seçebilirsin.";
      }
    }

    if (!stagedFiles.length) return;

    for (let i = stagedFiles.length - 1; i >= 0; i -= 1) {
      if (!canUseFileByMode(stagedFiles[i], mode)) {
        stagedFiles.splice(i, 1);
      }
    }

    if (fmt === "story" && stagedFiles.length > 1) {
      stagedFiles.splice(1);
    }

    syncStagedFilesToInput();
    renderStagedFiles();
  }

  function enforceFormatPlatformConstraints() {
    if (!platformBoxes || !platformBoxes.length) return;
    const fmt = getCurrentFormat();

    if (fmt === "story") {
      platformBoxes.forEach((box) => {
        const platform = (box.value || "").toLowerCase();
        if (platform === "instagram") {
          box.checked = true;
          box.disabled = false;
        } else {
          box.checked = false;
          box.disabled = true;
        }
      });
      if (formatPlatformNote) {
        formatPlatformNote.textContent = "Story modunda sadece Instagram aktiftir.";
      }
      return;
    }

    platformBoxes.forEach((box) => {
      box.disabled = false;
    });
    if (formatPlatformNote) {
      formatPlatformNote.textContent = "";
    }
  }

  function stageIncomingFiles(fileList) {
    const mode = getCurrentMediaMode();
    const fmt = getCurrentFormat();
    const seen = new Set(stagedFiles.map(fileKey));

    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;

    if (fmt === "story") {
      stagedFiles.length = 0;
      const firstValid = incoming.find((f) => canUseFileByMode(f, mode));
      if (firstValid) stagedFiles.push(firstValid);
      syncStagedFilesToInput();
      renderStagedFiles();
      return;
    }

    incoming.forEach((f) => {
      if (!canUseFileByMode(f, mode)) return;
      const key = fileKey(f);
      if (seen.has(key)) return;
      seen.add(key);
      stagedFiles.push(f);
    });

    syncStagedFilesToInput();
    renderStagedFiles();
  }

  if (modeSel) {
    setModeUI(modeSel.value);
    modeSel.addEventListener("change", () => setModeUI(modeSel.value));
  }

  if (btnDraft && actionField) {
    btnDraft.addEventListener("click", () => {
      actionField.value = "draft";
      const form = btnDraft.closest("form");
      if (form) form.submit();
    });
  }

  if (btnSubmit && actionField) {
    btnSubmit.addEventListener("click", () => {
      actionField.value = "submit";
    });
  }

  if (mediaRadios && mediaRadios.length) {
    setMediaAccept();
    mediaRadios.forEach((r) =>
      r.addEventListener("change", () => {
        setMediaAccept();
        enforceMediaConstraints();
      })
    );
  }

  if (formatRadios && formatRadios.length) {
    formatRadios.forEach((r) =>
      r.addEventListener("change", () => {
        enforceMediaConstraints();
        enforceFormatPlatformConstraints();
      })
    );
  }

  if (mediaInput) {
    mediaInput.addEventListener("change", () => {
      if (canStageFiles) {
        stageIncomingFiles(mediaInput.files);
      } else {
        // Fallback browsers: only current selection is available.
        renderStagedFiles();
      }
    });
  }

  setMediaAccept();
  enforceMediaConstraints();
  enforceFormatPlatformConstraints();
  renderStagedFiles();
})();
