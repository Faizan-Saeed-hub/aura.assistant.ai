// Aura AI Personal Assistant - Client Application

const DEFAULT_MALE_AVATAR = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120&auto=format&fit=crop&q=80";
const DEFAULT_FEMALE_AVATAR = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&auto=format&fit=crop&q=80";

let currentSessionId = null;
let voiceOutputEnabled = localStorage.getItem("aura_voice_tts") === "true"; // Defaults to false
let isRecording = false;
let speechRecognizer = null;
let activeView = "dashboard"; // "dashboard" | "chat"
let activeChatAttachedImage = null;
let activeChatRetouchPreset = "glow";

document.addEventListener("DOMContentLoaded", () => {
  initVoiceRecognition();
  initVoiceToggleUI();
  bindEvents();
  loadSessions();
  loadSettings();
  loadUserProfile();
  loadDashboardData();
  initAutoResizeTextarea();
});

function initVoiceToggleUI() {
  const voiceTtsBtn = document.getElementById("voice-tts-toggle");
  if (!voiceTtsBtn) return;
  voiceTtsBtn.classList.toggle("active", voiceOutputEnabled);
  voiceTtsBtn.querySelector("span").textContent = voiceOutputEnabled ? "Voice: ON" : "Voice: OFF";
  voiceTtsBtn.querySelector("i").className = voiceOutputEnabled ? "fa-solid fa-volume-high" : "fa-solid fa-volume-xmark";
}

// --- Event Binding ---
function bindEvents() {
  // Navigation
  document.getElementById("nav-home-btn").addEventListener("click", () => switchView("dashboard"));
  document.getElementById("nav-back-btn").addEventListener("click", () => switchView("dashboard"));
  document.getElementById("nav-new-chat-btn").addEventListener("click", createNewChat);
  document.getElementById("new-chat-top-btn").addEventListener("click", createNewChat);
  document.getElementById("refresh-page-btn").addEventListener("click", () => window.location.reload());

  // Fullscreen View Toggle
  const fullscreenBtn = document.getElementById("fullscreen-btn");
  if (fullscreenBtn) {
    fullscreenBtn.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
        fullscreenBtn.querySelector("i").className = "fa-solid fa-compress";
        fullscreenBtn.title = "Exit Fullscreen View";
      } else {
        if (document.exitFullscreen) document.exitFullscreen().catch(() => {});
        fullscreenBtn.querySelector("i").className = "fa-solid fa-expand";
        fullscreenBtn.title = "Toggle Fullscreen View";
      }
    });
  }

  // Modals
  setupModal("nav-rag-btn", "rag-modal", loadRagDocuments);
  setupModal("dash-open-rag", "rag-modal", loadRagDocuments);
  setupModal("nav-memory-btn", "memory-modal", loadMemories);
  setupModal("nav-tasks-btn", "notes-modal", loadNotes);
  setupModal("sidebar-settings-btn", "settings-modal", loadSettings);
  // Full-Screen Studio Views Navigation
  const navEmailBtn = document.getElementById("nav-email-btn");
  if (navEmailBtn) navEmailBtn.addEventListener("click", () => switchView("email"));

  const navImageBtn = document.getElementById("nav-image-btn");
  if (navImageBtn) navImageBtn.addEventListener("click", () => switchView("image"));

  // Dashboard Studio Quick Launchers
  const dashEmailCard = document.getElementById("dash-email-card");
  if (dashEmailCard) dashEmailCard.addEventListener("click", () => switchView("email"));

  const dashImageCard = document.getElementById("dash-image-card");
  if (dashImageCard) dashImageCard.addEventListener("click", () => switchView("image"));

  // Studio In-Page Back Buttons
  const btnEmailBack = document.getElementById("btn-email-back");
  if (btnEmailBack) btnEmailBack.addEventListener("click", () => switchView("dashboard"));

  const btnImageBack = document.getElementById("btn-image-back");
  if (btnImageBack) btnImageBack.addEventListener("click", () => switchView("dashboard"));
  setupModal("quick-settings-btn", "settings-modal", loadSettings);
  setupModal("open-settings-promo-btn", "settings-modal", loadSettings);

  // Profile Modal & Account Creation
  setupModal("quick-profile-btn", "profile-modal", () => { loadUserProfile(); switchProfileTab("profile"); });
  setupModal("open-profile-avatar-group", "profile-modal", () => { loadUserProfile(); switchProfileTab("profile"); });
  setupModal("sidebar-create-acc-btn", "profile-modal", () => { loadUserProfile(); switchProfileTab("register"); });

  // Tab switching in Profile Modal
  const tabProfileBtn = document.getElementById("tab-profile-view-btn");
  const tabRegBtn = document.getElementById("tab-register-btn");
  if (tabProfileBtn && tabRegBtn) {
    tabProfileBtn.addEventListener("click", () => switchProfileTab("profile"));
    tabRegBtn.addEventListener("click", () => switchProfileTab("register"));
  }

  // --- Gender & Avatar Uploads: Profile Edit ---
  const editGenderRadios = document.querySelectorAll('input[name="profile-gender"]');
  editGenderRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => {
      const g = e.target.value;
      document.getElementById("pill-gender-male").classList.toggle("active", g === "male");
      document.getElementById("pill-gender-female").classList.toggle("active", g === "female");

      const avatarInput = document.getElementById("profile-avatar-input");
      const previewImg = document.getElementById("edit-avatar-preview");
      const currentUrl = avatarInput ? avatarInput.value.trim() : "";

      // If user hasn't uploaded a custom local avatar, swap default DP according to gender
      if (!currentUrl || currentUrl === DEFAULT_MALE_AVATAR || currentUrl === DEFAULT_FEMALE_AVATAR || currentUrl.includes("unsplash.com")) {
        const newAvatar = g === "female" ? DEFAULT_FEMALE_AVATAR : DEFAULT_MALE_AVATAR;
        if (previewImg) previewImg.src = newAvatar;
        if (avatarInput) avatarInput.value = newAvatar;
      }
    });
  });

  const editUploadBtn = document.getElementById("edit-avatar-upload-btn");
  const editFileInput = document.getElementById("edit-avatar-file-input");
  if (editUploadBtn && editFileInput) {
    editUploadBtn.addEventListener("click", () => editFileInput.click());
    editFileInput.addEventListener("change", async (e) => {
      if (e.target.files.length > 0) {
        const file = e.target.files[0];
        const uploadedUrl = await uploadAvatarFile(file);
        if (uploadedUrl) {
          const previewImg = document.getElementById("edit-avatar-preview");
          const avatarInput = document.getElementById("profile-avatar-input");
          if (previewImg) previewImg.src = uploadedUrl;
          if (avatarInput) avatarInput.value = uploadedUrl;
          showToast("📸 Photo selected! Click 'Save Profile Changes' to apply.");
        }
      }
    });
  }

  // --- Gender & Avatar Uploads: Account Registration ---
  const regGenderRadios = document.querySelectorAll('input[name="reg-gender"]');
  regGenderRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => {
      const g = e.target.value;
      document.getElementById("reg-pill-gender-male").classList.toggle("active", g === "male");
      document.getElementById("reg-pill-gender-female").classList.toggle("active", g === "female");

      const regAvatarUrlEl = document.getElementById("reg-avatar-url");
      const regPreviewImg = document.getElementById("reg-avatar-preview");
      const currentUrl = regAvatarUrlEl ? regAvatarUrlEl.value.trim() : "";

      if (!currentUrl || currentUrl === DEFAULT_MALE_AVATAR || currentUrl === DEFAULT_FEMALE_AVATAR || currentUrl.includes("unsplash.com")) {
        const newAvatar = g === "female" ? DEFAULT_FEMALE_AVATAR : DEFAULT_MALE_AVATAR;
        if (regPreviewImg) regPreviewImg.src = newAvatar;
        if (regAvatarUrlEl) regAvatarUrlEl.value = newAvatar;
      }
    });
  });

  const regUploadBtn = document.getElementById("reg-avatar-upload-btn");
  const regFileInput = document.getElementById("reg-avatar-file-input");
  if (regUploadBtn && regFileInput) {
    regUploadBtn.addEventListener("click", () => regFileInput.click());
    regFileInput.addEventListener("change", async (e) => {
      if (e.target.files.length > 0) {
        const file = e.target.files[0];
        const uploadedUrl = await uploadAvatarFile(file);
        if (uploadedUrl) {
          const regPreviewImg = document.getElementById("reg-avatar-preview");
          const regAvatarUrlEl = document.getElementById("reg-avatar-url");
          if (regPreviewImg) regPreviewImg.src = uploadedUrl;
          if (regAvatarUrlEl) regAvatarUrlEl.value = uploadedUrl;
          showToast("📸 Custom DP ready for new account!");
        }
      }
    });
  }

  // Profile Edit Form Submit
  const profileEditForm = document.getElementById("profile-edit-form");
  if (profileEditForm) {
    profileEditForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("profile-name-input").value.trim();
      const email = document.getElementById("profile-email-input").value.trim();
      const role = document.getElementById("profile-role-input").value.trim();
      const avatar = document.getElementById("profile-avatar-input").value.trim();
      const bio = document.getElementById("profile-bio-input").value.trim();
      const genderChecked = document.querySelector('input[name="profile-gender"]:checked');
      const gender = genderChecked ? genderChecked.value : "male";

      try {
        const res = await fetch("/api/user/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, gender, role, avatar_url: avatar || undefined, bio })
        });
        if (res.ok) {
          const data = await res.json();
          applyUserProfileToUI(data.user);
          closeModal("profile-modal");
          showToast("✅ Profile updated successfully!");
        } else {
          const err = await res.json().catch(() => ({}));
          showToast(`⚠️ Could not update profile: ${err.detail || "Error"}`);
        }
      } catch (err) {
        showToast("⚠️ Network error saving profile.");
      }
    });
  }

  // Account Registration Form Submit
  // Account Registration Form Submit (Supabase / Local Cloud-Ready Auth)
  const regForm = document.getElementById("register-account-form");
  if (regForm) {
    regForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("reg-name-input").value.trim();
      const email = document.getElementById("reg-email-input").value.trim();
      const password = document.getElementById("reg-password-input").value;
      const role = document.getElementById("reg-role-input").value.trim();
      const bio = document.getElementById("reg-bio-input").value.trim();
      const genderChecked = document.querySelector('input[name="reg-gender"]:checked');
      const gender = genderChecked ? genderChecked.value : "male";
      const avatarUrl = document.getElementById("reg-avatar-url") ? document.getElementById("reg-avatar-url").value : undefined;

      try {
        const res = await fetch("/api/auth/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password, gender, role, avatar_url: avatarUrl })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          if (data.user) applyUserProfileToUI(data.user);
          closeModal("profile-modal");
          const modeMsg = data.mode === "supabase_cloud" ? "Synced with Supabase Cloud!" : "Account created & ready!";
          showToast(`🎉 Welcome, ${data.user ? data.user.name : name}! ${modeMsg}`);
        } else {
          showToast(`⚠️ Registration failed: ${data.error || data.detail || "Server error"}`);
        }
      } catch (err) {
        showToast("⚠️ Network error registering account.");
      }
    });
  }

  document.querySelectorAll(".close-modal-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-modal");
      closeModal(modalId);
    });
  });

  // Chat Form Submit
  const chatForm = document.getElementById("chat-form");
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Enter to send (Shift+Enter for newline)
  const inputEl = document.getElementById("user-input");
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Voice TTS toggle
  const voiceTtsBtn = document.getElementById("voice-tts-toggle");
  voiceTtsBtn.addEventListener("click", () => {
    voiceOutputEnabled = !voiceOutputEnabled;
    localStorage.setItem("aura_voice_tts", voiceOutputEnabled);
    voiceTtsBtn.classList.toggle("active", voiceOutputEnabled);
    voiceTtsBtn.querySelector("span").textContent = voiceOutputEnabled ? "Voice: ON" : "Voice: OFF";
    voiceTtsBtn.querySelector("i").className = voiceOutputEnabled ? "fa-solid fa-volume-high" : "fa-solid fa-volume-xmark";
    
    // If turned off, immediately silence all ongoing speech
    if (!voiceOutputEnabled && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  });

  // Voice Input Mic
  const voiceInputBtn = document.getElementById("voice-input-btn");
  voiceInputBtn.addEventListener("click", toggleVoiceRecording);

  // Suggested Prompts on Dashboard
  document.querySelectorAll(".suggested-card").forEach((card) => {
    card.addEventListener("click", () => {
      const prompt = card.getAttribute("data-prompt");
      inputEl.value = prompt;
      handleSendMessage();
    });
  });

  // Weather & Time Prompt button
  document.getElementById("dash-weather-prompt-btn").addEventListener("click", () => {
    inputEl.value = "What is the live weather and system time?";
    handleSendMessage();
  });

  // Prioritize Tasks button
  document.getElementById("dash-prioritize-btn").addEventListener("click", () => {
    inputEl.value = "Please review my pending tasks and prioritize them with suggestions on what to tackle first.";
    handleSendMessage();
  });

  // --- Quick Plus Action Popover Menu ---
  const quickAttachBtn = document.getElementById("quick-attach-btn");
  const omnibarPlusMenu = document.getElementById("omnibar-plus-menu");
  const closePlusMenuBtn = document.getElementById("close-plus-menu-btn");
  const quickFileInput = document.getElementById("quick-file-input");
  const chatPhotoInput = document.getElementById("chat-photo-input");

  function togglePlusMenu() {
    if (!omnibarPlusMenu) return;
    const isShown = omnibarPlusMenu.style.display === "flex";
    omnibarPlusMenu.style.display = isShown ? "none" : "flex";
  }

  function closePlusMenu() {
    if (omnibarPlusMenu) omnibarPlusMenu.style.display = "none";
  }

  if (quickAttachBtn) {
    quickAttachBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      togglePlusMenu();
    });
  }

  if (closePlusMenuBtn) {
    closePlusMenuBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      closePlusMenu();
    });
  }

  // Close plus menu on outside click
  document.addEventListener("click", (e) => {
    if (omnibarPlusMenu && omnibarPlusMenu.style.display === "flex") {
      if (!omnibarPlusMenu.contains(e.target) && e.target !== quickAttachBtn && !quickAttachBtn.contains(e.target)) {
        closePlusMenu();
      }
    }
  });

  // Action 1: Upload & Retouch Photo
  const plusActionUploadPhoto = document.getElementById("plus-action-upload-photo");
  if (plusActionUploadPhoto && chatPhotoInput) {
    plusActionUploadPhoto.addEventListener("click", () => {
      closePlusMenu();
      chatPhotoInput.click();
    });
  }

  // Action 2: Generate AI Image
  const plusActionGenImage = document.getElementById("plus-action-gen-image");
  if (plusActionGenImage) {
    plusActionGenImage.addEventListener("click", () => {
      closePlusMenu();
      const input = document.getElementById("user-input");
      input.value = "Generate an image of ";
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    });
  }

  // Action 3: Open Full Image Studio
  const plusActionFullImage = document.getElementById("plus-action-full-image-studio");
  if (plusActionFullImage) {
    plusActionFullImage.addEventListener("click", () => {
      closePlusMenu();
      switchView("image");
    });
  }

  // Action 4: Draft Email in Chat
  const plusActionDraftEmail = document.getElementById("plus-action-draft-email");
  if (plusActionDraftEmail) {
    plusActionDraftEmail.addEventListener("click", () => {
      closePlusMenu();
      const input = document.getElementById("user-input");
      input.value = "Draft a professional business email proposing our AI automation services, highlighting efficiency gains and requesting a short meeting.";
      input.focus();
    });
  }

  // Action 5: Open Full Email Studio
  const plusActionFullEmail = document.getElementById("plus-action-full-email-studio");
  if (plusActionFullEmail) {
    plusActionFullEmail.addEventListener("click", () => {
      closePlusMenu();
      switchView("email");
    });
  }

  // Action 6: Upload Document (RAG)
  const plusActionUploadDoc = document.getElementById("plus-action-upload-doc");
  if (plusActionUploadDoc && quickFileInput) {
    plusActionUploadDoc.addEventListener("click", () => {
      closePlusMenu();
      quickFileInput.click();
    });
  }

  if (quickFileInput) {
    quickFileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) uploadFile(e.target.files[0]);
    });
  }

  // --- Photo Attachment & In-Chat Retouch Tray Setup ---
  const chatAttachmentTray = document.getElementById("chat-attachment-tray");
  const attachmentPreviewImg = document.getElementById("attachment-preview-img");
  const attachmentFileName = document.getElementById("attachment-file-name");
  const attachmentFileDesc = document.getElementById("attachment-file-desc");
  const chatRetouchPresets = document.getElementById("chat-retouch-presets");
  const removeAttachmentBtn = document.getElementById("remove-attachment-btn");

  if (chatPhotoInput) {
    chatPhotoInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        activeChatAttachedImage = file;
        activeChatRetouchPreset = "glow";

        const reader = new FileReader();
        reader.onload = (re) => {
          if (attachmentPreviewImg) {
            attachmentPreviewImg.src = re.target.result;
            attachmentPreviewImg.style.display = "block";
          }
          if (attachmentFileName) attachmentFileName.textContent = file.name;
          if (attachmentFileDesc) attachmentFileDesc.textContent = `${(file.size / 1024).toFixed(0)} KB • Photo Attached`;
          if (chatRetouchPresets) chatRetouchPresets.style.display = "flex";
          if (chatAttachmentTray) chatAttachmentTray.style.display = "flex";

          const inputEl = document.getElementById("user-input");
          if (inputEl && !inputEl.value.trim()) {
            inputEl.placeholder = "Prompt (e.g. 'Natural face glow & WhatsApp DP crop') or press Send...";
          }
          if (inputEl) inputEl.focus();
        };
        reader.readAsDataURL(file);
      }
    });
  }

  document.querySelectorAll(".chat-preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chat-preset-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeChatRetouchPreset = chip.dataset.preset;
    });
  });

  if (removeAttachmentBtn) {
    removeAttachmentBtn.addEventListener("click", clearChatAttachment);
  }


  const dashQuickUpload = document.getElementById("dash-quick-upload-btn");
  if (dashQuickUpload) {
    dashQuickUpload.addEventListener("click", () => quickFileInput.click());
  }

  // Dropzone file upload inside modal
  const dropZone = document.getElementById("rag-drop-zone");
  const modalFileInput = document.getElementById("modal-file-input");
  dropZone.addEventListener("click", () => modalFileInput.click());
  modalFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) uploadFile(e.target.files[0]);
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
  });

  // Add Memory Form
  const addMemoryForm = document.getElementById("add-memory-form");
  addMemoryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const cat = document.getElementById("mem-category").value;
    const content = document.getElementById("mem-content").value.trim();
    if (!content) return;

    await fetch("/api/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: cat, content: content, importance: 3 })
    });
    document.getElementById("mem-content").value = "";
    loadMemories();
  });

  // Add Note Form (Modal)
  const addNoteForm = document.getElementById("add-note-form");
  addNoteForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("note-title-input").value.trim();
    const due = document.getElementById("note-due-input").value.trim();
    if (!title) return;

    await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, due_date: due })
    });
    document.getElementById("note-title-input").value = "";
    document.getElementById("note-due-input").value = "";
    loadNotes();
    loadDashboardTasks();
  });

  // Tasks search filter on dashboard
  const searchInput = document.getElementById("dash-tasks-search");
  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll(".dash-task-row").forEach((row) => {
      const text = row.querySelector(".task-text").textContent.toLowerCase();
      row.style.display = text.includes(q) ? "flex" : "none";
    });
  });

  // Settings Form Submit
  const settingsForm = document.getElementById("settings-form");
  if (settingsForm) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const provider = document.getElementById("setting-provider").value;
      const openrouterKey = document.getElementById("setting-openrouter-key") ? document.getElementById("setting-openrouter-key").value.trim() : "";
      const openrouterModel = document.getElementById("setting-openrouter-model") ? document.getElementById("setting-openrouter-model").value : "";
      const geminiKey = document.getElementById("setting-gemini-key") ? document.getElementById("setting-gemini-key").value.trim() : "";
      const groqKey = document.getElementById("setting-groq-key") ? document.getElementById("setting-groq-key").value.trim() : "";
      const groqModel = document.getElementById("setting-groq-model") ? document.getElementById("setting-groq-model").value : "";

      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          active_provider: provider,
          openrouter_api_key: openrouterKey || undefined,
          openrouter_model: openrouterModel || undefined,
          gemini_api_key: geminiKey || undefined,
          groq_api_key: groqKey || undefined,
          groq_model: groqModel || undefined
        })
      });

      closeModal("settings-modal");
      loadSettings();
      showToast("Settings saved successfully!");
    });
  }
}

function setupModal(triggerId, modalId, onLoad) {
  const trigger = document.getElementById(triggerId);
  if (trigger) {
    trigger.addEventListener("click", () => {
      document.getElementById(modalId).classList.add("open");
      if (onLoad) onLoad();
    });
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.remove("open");
}

function switchView(view) {
  activeView = view;
  const dashEl = document.getElementById("dashboard-view");
  const chatEl = document.getElementById("chat-view");
  const emailEl = document.getElementById("email-view");
  const imageEl = document.getElementById("image-view");
  const omnibarEl = document.getElementById("chat-omnibar");

  const navHomeBtn = document.getElementById("nav-home-btn");
  const navNewChatBtn = document.getElementById("nav-new-chat-btn");
  const navEmailBtn = document.getElementById("nav-email-btn");
  const navImageBtn = document.getElementById("nav-image-btn");

  // Reset all view container displays
  if (dashEl) dashEl.style.display = "none";
  if (chatEl) chatEl.style.display = "none";
  if (emailEl) emailEl.style.display = "none";
  if (imageEl) imageEl.style.display = "none";

  // Reset sidebar active indicators
  if (navHomeBtn) navHomeBtn.classList.remove("active");
  if (navNewChatBtn) navNewChatBtn.classList.remove("active");
  if (navEmailBtn) navEmailBtn.classList.remove("active");
  if (navImageBtn) navImageBtn.classList.remove("active");

  if (view === "dashboard") {
    if (dashEl) dashEl.style.display = "flex";
    if (navHomeBtn) navHomeBtn.classList.add("active");
    if (omnibarEl) omnibarEl.style.display = "flex";
    loadDashboardData();
  } else if (view === "chat") {
    if (chatEl) chatEl.style.display = "flex";
    if (navNewChatBtn) navNewChatBtn.classList.add("active");
    if (omnibarEl) omnibarEl.style.display = "flex";
  } else if (view === "email") {
    if (emailEl) emailEl.style.display = "flex";
    if (navEmailBtn) navEmailBtn.classList.add("active");
    if (omnibarEl) omnibarEl.style.display = "none";
    initEmailStudio();
  } else if (view === "image") {
    if (imageEl) imageEl.style.display = "flex";
    if (navImageBtn) navImageBtn.classList.add("active");
    if (omnibarEl) omnibarEl.style.display = "none";
    initImageStudio();
  }
}

function initAutoResizeTextarea() {
  const input = document.getElementById("user-input");
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  });
}

// --- Dashboard Data Loading ---
async function loadDashboardData() {
  loadDashboardFiles();
  loadDashboardTasks();
  updateLiveTimeAndWeather();
}

async function loadDashboardFiles() {
  try {
    const res = await fetch("/api/rag/documents");
    const docs = await res.json();
    const listEl = document.getElementById("dash-files-list");
    listEl.innerHTML = "";

    if (docs.length === 0) {
      listEl.innerHTML = `
        <div class="file-mini-item" style="opacity:0.7;">
          <i class="fa-regular fa-folder-open"></i>
          <span>No files uploaded yet. Click below to add files for RAG!</span>
        </div>
      `;
      return;
    }

    docs.slice(0, 4).forEach((d) => {
      const isPdf = d.file_type === ".pdf";
      const iconClass = isPdf ? "fa-solid fa-file-pdf icon-pdf" : "fa-solid fa-file-lines icon-txt";
      const item = document.createElement("div");
      item.className = "file-mini-item";
      item.innerHTML = `
        <i class="${iconClass}"></i>
        <span>${escapeHtml(d.filename)} (${d.chunk_count} chunks)</span>
      `;
      item.addEventListener("click", () => {
        document.getElementById("user-input").value = `What information is in '${d.filename}'?`;
        handleSendMessage();
      });
      listEl.appendChild(item);
    });
  } catch (e) {
    console.error("Failed to load dashboard files", e);
  }
}

async function loadDashboardTasks() {
  try {
    const res = await fetch("/api/notes?status=all");
    let tasks = await res.json();
    const listEl = document.getElementById("dash-tasks-list");
    const countBadge = document.getElementById("dash-tasks-count");
    
    // If no tasks exist in DB, populate default sample tasks (matching reference UI)
    if (tasks.length === 0) {
      await fetch("/api/notes", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ title: "Design Meeting", due_date: "Today 2 pm" }) });
      await fetch("/api/notes", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ title: "Refine UI components based on user feedback", due_date: "By today" }) });
      await fetch("/api/notes", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ title: "Prepare a prototype for usability testing", due_date: "By tomorrow" }) });
      const refreshRes = await fetch("/api/notes?status=all");
      tasks = await refreshRes.json();
    }

    countBadge.textContent = tasks.length;
    listEl.innerHTML = "";

    const tagTypes = [
      { class: "urgent", text: "Urgent" },
      { class: "today", text: "By today" },
      { class: "progress", text: "In progress" },
      { class: "tomorrow", text: "By tomorrow" }
    ];

    tasks.slice(0, 6).forEach((t, idx) => {
      const isDone = t.status === "completed";
      const row = document.createElement("div");
      row.className = `dash-task-row ${isDone ? "done" : ""}`;
      
      const tag = tagTypes[idx % tagTypes.length];
      const dotColor = idx % 3 === 0 ? "orange" : idx % 3 === 1 ? "blue" : "green";

      row.innerHTML = `
        <div class="task-left">
          <input type="checkbox" class="task-check-input" ${isDone ? "checked" : ""} />
          <span class="task-dot ${dotColor}"></span>
          <span class="task-text">${escapeHtml(t.title)}</span>
        </div>
        <div class="task-tags">
          ${t.due_date ? `<span class="tag-pill today"><i class="fa-regular fa-clock"></i> ${escapeHtml(t.due_date)}</span>` : ""}
          <span class="tag-pill ${tag.class}">${tag.text}</span>
        </div>
      `;

      row.querySelector(".task-check-input").addEventListener("change", async () => {
        await fetch(`/api/notes/${t.id}/complete`, { method: "PUT" });
        loadDashboardTasks();
      });

      listEl.appendChild(row);
    });
  } catch (e) {
    console.error("Failed to load dashboard tasks", e);
  }
}

function updateLiveTimeAndWeather() {
  const timeEl = document.getElementById("dash-live-time");
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const dateStr = now.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
  timeEl.textContent = `${dateStr}, ${timeStr} • Online & Ready`;
}

// --- Chat Sessions Management ---
async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    const sessions = await res.json();
    const todayList = document.getElementById("history-today");
    const olderList = document.getElementById("history-older");
    todayList.innerHTML = "";
    olderList.innerHTML = "";

    if (sessions.length === 0) {
      todayList.innerHTML = `<span style="font-size:0.75rem; color:#94a3b8; padding: 4px;">No chats yet</span>`;
      return;
    }

    sessions.forEach((s, idx) => {
      const item = document.createElement("div");
      item.className = `history-item ${s.id === currentSessionId ? "active" : ""}`;
      item.innerHTML = `
        <span class="history-item-title">${escapeHtml(s.title || "Conversation")}</span>
        <button class="history-del-btn" title="Delete conversation">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      `;

      item.querySelector(".history-item-title").addEventListener("click", () => {
        selectSession(s.id, s.title);
      });

      item.querySelector(".history-del-btn").addEventListener("click", (e) => {
        e.stopPropagation();
        deleteSession(s.id);
      });

      if (idx < 3) {
        todayList.appendChild(item);
      } else {
        olderList.appendChild(item);
      }
    });

    if (!currentSessionId && sessions.length > 0) {
      currentSessionId = sessions[0].id;
    }
  } catch (err) {
    console.error("Failed to load sessions", err);
  }
}

async function createNewChat() {
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "New Conversation" })
  });
  const newSess = await res.json();
  selectSession(newSess.id, newSess.title);
  loadSessions();
}

async function selectSession(sessionId, title) {
  currentSessionId = sessionId;
  switchView("chat");

  document.querySelectorAll(".history-item").forEach((el) => el.classList.remove("active"));
  const container = document.getElementById("messages-container");
  container.innerHTML = "";

  const res = await fetch(`/api/sessions/${sessionId}/messages`);
  const messages = await res.json();

  if (messages.length === 0) {
    appendMessageUI("assistant", "👋 **Hello! How can I assist you today?**\n\nYou can ask questions, search the live web, check weather, calculate math, or manage your notes!");
  } else {
    messages.forEach((m) => {
      appendMessageUI(m.role, m.content, m.tool_calls, m.citations);
    });
    scrollToBottom();
  }
}

async function deleteSession(sessionId) {
  await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
  if (currentSessionId === sessionId) {
    currentSessionId = null;
    switchView("dashboard");
  }
  loadSessions();
}

function clearChatAttachment() {
  activeChatAttachedImage = null;
  activeChatRetouchPreset = "glow";
  const chatPhotoInput = document.getElementById("chat-photo-input");
  if (chatPhotoInput) chatPhotoInput.value = "";
  const chatAttachmentTray = document.getElementById("chat-attachment-tray");
  if (chatAttachmentTray) chatAttachmentTray.style.display = "none";
  const inputEl = document.getElementById("user-input");
  if (inputEl) {
    inputEl.placeholder = "Ask anything, describe an image, retouch a photo, draft an email, or search...";
  }
}

// --- Messaging Flow ---
async function handleSendMessage() {
  const inputEl = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const text = inputEl.value.trim();

  // If nothing typed and no photo attached, return
  if (!text && !activeChatAttachedImage) return;

  // 1. Immediately abort voice recognition & reset dictation buffers
  stopVoiceRecording();
  accumulatedDictation = "";

  // 2. Handle Attached Photo Retouching if active
  if (activeChatAttachedImage) {
    const photoFile = activeChatAttachedImage;
    const preset = activeChatRetouchPreset || "glow";
    const userPrompt = text || `Retouch this photo with ${preset.toUpperCase()} preset and natural face glow.`;

    inputEl.value = "";
    inputEl.style.height = "auto";
    inputEl.dispatchEvent(new Event("input"));
    clearChatAttachment();

    switchView("chat");

    if (!currentSessionId) {
      const sRes = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Photo Retouch Studio" })
      });
      const sData = await sRes.json();
      currentSessionId = sData.id;
    }

    const localPreviewUrl = URL.createObjectURL(photoFile);
    const userMsgHtml = `${escapeHtml(userPrompt)}<br/><div class="chat-attached-user-img" style="margin-top:8px;"><img src="${localPreviewUrl}" style="max-width:220px; max-height:220px; border-radius:12px; display:block; border:1px solid rgba(255,255,255,0.4);" /></div>`;
    appendMessageUI("user", userMsgHtml);
    scrollToBottom();

    showActivity("Aura is enhancing & retouching your photo with AI...");
    sendBtn.disabled = true;

    try {
      const formData = new FormData();
      formData.append("file", photoFile);
      formData.append("preset", preset);
      if (preset === "crop_dp") {
        formData.append("crop_aspect", "1:1");
      }

      const res = await fetch("/api/image/retouch", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      hideActivity();
      sendBtn.disabled = false;

      if (data.success && data.url) {
        const assistantText = `✨ **Photo Retouched Successfully!**\n\n` +
          `Applied **${preset.toUpperCase()}** preset (${data.details || 'Natural lighting & skin enhance'}).\n\n` +
          `<div class="chat-image-card">` +
            `<div class="chat-image-preview"><img src="${data.url}" alt="Retouched Photo" /></div>` +
            `<div class="chat-image-actions">` +
              `<a href="${data.url}" download="${data.filename}" class="btn-chat-img-action primary"><i class="fa-solid fa-download"></i> Download</a>` +
              `<button type="button" class="btn-chat-img-action" onclick="setAsAccountDPFromChat('${data.url}')"><i class="fa-solid fa-user-check"></i> Set as Profile DP</button>` +
              `<button type="button" class="btn-chat-img-action" onclick="openImageInStudio('${data.url}')"><i class="fa-solid fa-sliders"></i> Fine-Tune in Studio</button>` +
            `</div>` +
          `</div>`;
        appendMessageUI("assistant", assistantText);
        scrollToBottom();
      } else {
        appendMessageUI("assistant", `⚠️ Photo retouch failed: ${data.error || "Unknown error"}`);
      }
    } catch (err) {
      hideActivity();
      sendBtn.disabled = false;
      appendMessageUI("assistant", `⚠️ Error processing image: ${err.message}`);
    }
    return;
  }

  // 3. Normal Text Chat Message Flow
  inputEl.value = "";
  inputEl.style.height = "auto";
  inputEl.dispatchEvent(new Event("input"));

  if (document.activeElement === inputEl) {
    inputEl.blur();
  }

  setTimeout(() => {
    inputEl.value = "";
    inputEl.style.height = "auto";
  }, 40);
  setTimeout(() => {
    inputEl.value = "";
    inputEl.style.height = "auto";
  }, 150);

  switchView("chat");

  if (!currentSessionId) {
    const sRes = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: text.slice(0, 26) })
    });
    const sData = await sRes.json();
    currentSessionId = sData.id;
  }

  appendMessageUI("user", text);
  scrollToBottom();

  showActivity("Aura is reasoning & executing tools...");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server status ${res.status}`);
    }

    const data = await res.json();
    hideActivity();
    sendBtn.disabled = false;

    appendMessageUI("assistant", data.text, data.tool_calls, data.citations);
    scrollToBottom();

    if (voiceOutputEnabled && data.text) {
      speakText(data.text);
    }

    loadSessions();
    loadDashboardTasks();
  } catch (err) {
    hideActivity();
    sendBtn.disabled = false;
    appendMessageUI("assistant", `⚠️ Error: ${err.message || "Failed to communicate with assistant backend."}`);
  }
}

function appendMessageUI(role, content, toolCalls = [], citations = []) {
  const container = document.getElementById("messages-container");
  const row = document.createElement("div");
  row.className = `chat-message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar";
  avatar.innerHTML = role === "assistant" ? '<i class="fa-solid fa-sparkles"></i>' : '<i class="fa-solid fa-user"></i>';

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";

  let innerHTML = "";

  // Render Tool Execution Badges
  if (toolCalls && toolCalls.length > 0) {
    toolCalls.forEach((tc) => {
      const toolIcons = {
        web_search: "fa-solid fa-globe",
        get_weather: "fa-solid fa-cloud-sun",
        calculate: "fa-solid fa-calculator",
        wikipedia_lookup: "fa-brands fa-wikipedia-w",
        get_system_info: "fa-solid fa-clock",
        add_note: "fa-solid fa-clipboard",
        list_notes: "fa-solid fa-list-check",
        generate_image: "fa-solid fa-paintbrush"
      };
      const icon = toolIcons[tc.tool] || "fa-solid fa-wrench";
      innerHTML += `<div class="tool-badge-pill"><i class="${icon}"></i> Executed ${tc.tool}</div><br/>`;
    });
  }

  // Render Content
  if (role === "assistant" && typeof marked !== "undefined") {
    innerHTML += marked.parse(content || "");
  } else if (content.includes("<img") || content.includes("<div") || content.includes("<br/>")) {
    innerHTML += content;
  } else {
    innerHTML += `<p>${escapeHtml(content || "")}</p>`;
  }

  // Render Citations (RAG)
  if (citations && citations.length > 0) {
    innerHTML += `<div class="citations-panel">
      <strong><i class="fa-solid fa-book-bookmark"></i> Grounded in Documents:</strong>`;
    citations.forEach((c) => {
      innerHTML += `<div class="citation-item">
        <b>📄 ${escapeHtml(c.filename)}</b> (Page ${c.page || 1}, Match: ${Math.round((c.score || 0) * 100)}%)
        <div style="color:#64748b; margin-top:2px;">"${escapeHtml(c.snippet || "")}"</div>
      </div>`;
    });
    innerHTML += `</div>`;
  }

  bubble.innerHTML = innerHTML;

  // Enhance standalone images in assistant responses with action buttons
  if (role === "assistant") {
    const imgs = bubble.querySelectorAll("img");
    imgs.forEach((img) => {
      if (img.closest(".chat-image-card") || img.closest(".chat-attached-user-img")) return;
      const src = img.getAttribute("src");
      if (!src) return;

      const card = document.createElement("div");
      card.className = "chat-image-card";

      const preview = document.createElement("div");
      preview.className = "chat-image-preview";
      const clonedImg = img.cloneNode(true);
      preview.appendChild(clonedImg);

      const actions = document.createElement("div");
      actions.className = "chat-image-actions";
      actions.innerHTML = `
        <a href="${src}" target="_blank" download="aura_image.png" class="btn-chat-img-action primary"><i class="fa-solid fa-download"></i> Download</a>
        <button type="button" class="btn-chat-img-action" onclick="setAsAccountDPFromChat('${src}')"><i class="fa-solid fa-user-check"></i> Set as Profile DP</button>
        <button type="button" class="btn-chat-img-action" onclick="openImageInStudio('${src}')"><i class="fa-solid fa-sliders"></i> Open in Studio</button>
      `;

      card.appendChild(preview);
      card.appendChild(actions);
      img.replaceWith(card);
    });
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  container.appendChild(row);

  if (typeof Prism !== "undefined") {
    Prism.highlightAllUnder(bubble);
  }
}

// Global Image Actions from Chat
window.setAsAccountDPFromChat = async function(imageUrl) {
  try {
    showToast("Updating your profile picture...");
    const res = await fetch(imageUrl);
    const blob = await res.blob();
    const file = new File([blob], "profile_dp.jpg", { type: blob.type || "image/jpeg" });
    const uploadedUrl = await uploadAvatarFile(file);
    if (uploadedUrl) {
      const profRes = await fetch("/api/user/profile");
      if (profRes.ok) {
        const curr = await profRes.json();
        const updateRes = await fetch("/api/user/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: curr.name,
            email: curr.email,
            gender: curr.gender || "male",
            role: curr.role,
            avatar_url: uploadedUrl,
            bio: curr.bio
          })
        });
        if (updateRes.ok) {
          const uData = await updateRes.json();
          applyUserProfileToUI(uData.user);
          showToast("🎉 Profile DP updated with this image!");
        }
      }
    }
  } catch (err) {
    showToast(`⚠️ Failed to update DP: ${err.message}`);
  }
};

window.openImageInStudio = function(imageUrl) {
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    studioImage = img;
    const dropzone = document.getElementById("studio-canvas-dropzone");
    if (dropzone) dropzone.classList.add("has-image");
    const emptyOverlay = document.getElementById("studio-empty-overlay");
    if (emptyOverlay) emptyOverlay.style.display = "none";
    switchView("image");
    invalidateRetouchCache();
    renderStudioCanvas();
    showToast("🎨 Loaded photo into Image Studio!");
  };
  img.src = imageUrl;
};

function showActivity(msg) {
  const bar = document.getElementById("agent-activity-bar");
  const text = document.getElementById("activity-text");
  text.textContent = msg;
  bar.style.display = "flex";
}

function hideActivity() {
  document.getElementById("agent-activity-bar").style.display = "none";
}

function scrollToBottom() {
  const container = document.getElementById("messages-container");
  container.scrollTop = container.scrollHeight;
}

// --- Voice Recognition & Synthesis ---
let speechLang = localStorage.getItem("aura_speech_lang") || "ur-PK";
let cachedVoices = [];

if (typeof window !== "undefined" && window.speechSynthesis) {
  cachedVoices = window.speechSynthesis.getVoices() || [];
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoices = window.speechSynthesis.getVoices() || [];
  };
}

let accumulatedDictation = "";

function initVoiceRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) return;

  speechRecognizer = new SpeechRec();
  speechRecognizer.continuous = true; // Continuous listening to capture entire speech without cutting off
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = speechLang;

  const micBtn = document.getElementById("voice-input-btn");
  const inputEl = document.getElementById("user-input");
  const langBadge = document.getElementById("voice-lang-badge");
  const langBtn = document.getElementById("voice-lang-toggle");

  const updateLangUI = () => {
    const isUr = speechLang.startsWith("ur");
    if (langBadge) langBadge.textContent = isUr ? "UR" : "EN";
    if (langBtn) {
      langBtn.title = isUr 
        ? "Language: Urdu / Roman Urdu (UR) — Click to switch to English" 
        : "Language: English (EN) — Click to switch to Urdu / Roman Urdu";
      langBtn.style.color = isUr ? "#059669" : "#2563eb";
      langBtn.style.borderColor = isUr ? "#a7f3d0" : "#bfdbfe";
      langBtn.style.background = isUr ? "#ecfdf5" : "#eff6ff";
    }
  };

  updateLangUI();

  if (langBtn && !langBtn.dataset.bound) {
    langBtn.dataset.bound = "true";
    langBtn.addEventListener("click", () => {
      speechLang = speechLang.startsWith("ur") ? "en-US" : "ur-PK";
      localStorage.setItem("aura_speech_lang", speechLang);
      if (speechRecognizer) speechRecognizer.lang = speechLang;
      updateLangUI();
      const name = speechLang.startsWith("ur") ? "Urdu / Roman Urdu (UR)" : "English (EN)";
      showToast(`🌐 Voice input language set to: ${name}`);
    });
  }

  speechRecognizer.onstart = () => {
    isRecording = true;
    micBtn.classList.add("recording");
    const langLabel = speechLang.startsWith("ur") ? "Urdu / Roman Urdu" : "English";
    micBtn.title = `Listening (${langLabel})... Click mic again to stop`;
    accumulatedDictation = inputEl.value ? inputEl.value.trim() + " " : "";
    showToast(`🎤 Continuous listening (${langLabel})... Speak your full message.`);
  };

  speechRecognizer.onend = () => {
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.title = "Voice Dictation";
    if (inputEl.value.trim()) {
      showToast("📝 Dictation captured! Click Send when you are ready.");
    }
  };

  speechRecognizer.onerror = (e) => {
    isRecording = false;
    micBtn.classList.remove("recording");
    if (e.error === "not-allowed") {
      showToast("⚠️ Microphone access denied. Please allow microphone permissions in your browser.");
    } else if (e.error !== "no-speech") {
      console.warn("Speech recognition notice:", e.error);
    }
  };

  speechRecognizer.onresult = (event) => {
    if (!isRecording) return; // Discard trailing recognition events if stopped or sending
    let interim = "";
    let finalPart = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalPart += event.results[i][0].transcript + " ";
      } else {
        interim += event.results[i][0].transcript;
      }
    }
    if (!isRecording) return;
    if (finalPart) {
      accumulatedDictation += finalPart;
    }
    const currentText = (accumulatedDictation + interim).trim();
    if (currentText && isRecording) {
      inputEl.value = currentText;
      inputEl.dispatchEvent(new Event("input"));
    }
    // STRICT REQUIREMENT: No auto-send! Dictation is written to text box, user sends manually.
  };
}

function stopVoiceRecording() {
  isRecording = false; // Flag immediately false to block any trailing onresult callbacks
  if (speechRecognizer) {
    try {
      if (typeof speechRecognizer.abort === "function") {
        speechRecognizer.abort(); // Immediately cancels without firing trailing onresult
      } else {
        speechRecognizer.stop();
      }
    } catch (e) {
      try { speechRecognizer.stop(); } catch (e2) {}
    }
  }
  const micBtn = document.getElementById("voice-input-btn");
  if (micBtn) {
    micBtn.classList.remove("recording");
    micBtn.title = "Voice Dictation";
  }
  accumulatedDictation = "";
}

function toggleVoiceRecording() {
  if (!speechRecognizer) {
    initVoiceRecognition();
  }
  if (!speechRecognizer) {
    showToast("⚠️ Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.");
    return;
  }
  if (isRecording) {
    stopVoiceRecording();
    showToast("⏹️ Voice input stopped.");
  } else {
    try {
      if (speechRecognizer) speechRecognizer.lang = speechLang;
      speechRecognizer.start();
    } catch (e) {
      console.warn("Speech start exception:", e);
    }
  }
}

function speakText(text) {
  if (!voiceOutputEnabled || !window.speechSynthesis) {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    return;
  }
  window.speechSynthesis.cancel();

  // Strip Markdown, links, and code blocks for spoken audio
  const clean = text
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*#_~>-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  // Bilingual Voice Selection: If Roman Urdu or Urdu script, use native South Asian voice (hi / ur)
  const isUrdu = /[\u0600-\u06FF]/.test(clean) || /\b(hai|hain|hoon|ho|kya|kaun|kon|kaisa|kaisi|kaise|theek|shukriya|aaj|kal|meri|mera|aap|ap|hum|tum|nahi|nahin|kar|diya|bhi|yeh|woh|karachi|lahore|islamabad|waqt|tareekh|batao|suno|madad|bhai)\b/i.test(clean);
  
  const voices = (cachedVoices && cachedVoices.length > 0) ? cachedVoices : (window.speechSynthesis.getVoices() || []);
  
  if (isUrdu) {
    const urVoice = voices.find(v => {
      const l = (v.lang || "").toLowerCase();
      const n = (v.name || "").toLowerCase();
      return l.includes("ur") || l.includes("hi") || n.includes("urdu") || n.includes("hindi") || n.includes("india") || n.includes("pakistan");
    });
    if (urVoice) {
      utterance.voice = urVoice;
      utterance.rate = 1.0;
    }
  } else {
    const enVoice = voices.find(v => {
      const l = (v.lang || "").toLowerCase();
      const n = (v.name || "").toLowerCase();
      return l.startsWith("en") && (n.includes("google") || n.includes("natural") || n.includes("microsoft") || n.includes("jenny") || n.includes("aria") || n.includes("guy"));
    }) || voices.find(v => (v.lang || "").toLowerCase().startsWith("en"));
    
    if (enVoice) {
      utterance.voice = enVoice;
    }
  }

  window.speechSynthesis.speak(utterance);
}

// --- Document Upload & RAG ---
async function uploadFile(file) {
  if (!file) return;
  showToast(`📄 Uploading and indexing '${file.name}'...`);
  showActivity(`Indexing document '${file.name}' into vector database...`);
  
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/rag/upload", {
      method: "POST",
      body: formData
    });

    hideActivity();
    const quickInput = document.getElementById("quick-file-input");
    if (quickInput) quickInput.value = "";
    const modalInput = document.getElementById("modal-file-input");
    if (modalInput) modalInput.value = "";

    if (res.ok) {
      const data = await res.json();
      showToast(`✅ '${file.name}' indexed successfully (${data.chunk_count} vector chunks)!`);
      loadRagDocuments();
      loadDashboardFiles();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(`⚠️ Upload failed: ${err.detail || "Server error"}`);
    }
  } catch (e) {
    hideActivity();
    showToast(`⚠️ Upload error: ${e.message}`);
  }
}

async function loadRagDocuments() {
  const res = await fetch("/api/rag/documents");
  const docs = await res.json();
  const tbody = document.getElementById("rag-docs-tbody");
  document.getElementById("rag-doc-count").textContent = docs.length;
  tbody.innerHTML = "";

  if (docs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No documents uploaded yet.</td></tr>`;
    return;
  }

  docs.forEach((d) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${escapeHtml(d.filename)}</strong></td>
      <td>${escapeHtml(d.file_type)}</td>
      <td>${d.chunk_count} chunks</td>
      <td>${d.uploaded_at ? d.uploaded_at.split("T")[0] : ""}</td>
      <td>
        <button class="action-btn-del" title="Delete document">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    `;
    tr.querySelector(".action-btn-del").addEventListener("click", async () => {
      await fetch(`/api/rag/documents/${d.id}`, { method: "DELETE" });
      loadRagDocuments();
      loadDashboardFiles();
    });
    tbody.appendChild(tr);
  });
}

// --- Memory Vault ---
async function loadMemories() {
  const res = await fetch("/api/memories");
  const memories = await res.json();
  const grid = document.getElementById("memories-grid");
  grid.innerHTML = "";

  if (memories.length === 0) {
    grid.innerHTML = `<p style="color:#94a3b8; font-size:0.84rem;">No memories stored yet. Mention facts in chat or add one above!</p>`;
    return;
  }

  memories.forEach((m) => {
    const card = document.createElement("div");
    card.className = "memory-clean-item";
    card.innerHTML = `
      <div>
        <span class="mem-badge">${escapeHtml(m.category)}</span>
        <span>${escapeHtml(m.content)}</span>
      </div>
      <button class="action-btn-del" title="Delete memory">
        <i class="fa-solid fa-trash"></i>
      </button>
    `;
    card.querySelector(".action-btn-del").addEventListener("click", async () => {
      await fetch(`/api/memories/${m.id}`, { method: "DELETE" });
      loadMemories();
    });
    grid.appendChild(card);
  });
}

// --- Notes Management ---
async function loadNotes(status = "all") {
  const res = await fetch(`/api/notes?status=${status}`);
  const notes = await res.json();
  const container = document.getElementById("notes-container");
  container.innerHTML = "";

  if (notes.length === 0) {
    container.innerHTML = `<p style="color:#94a3b8; font-size:0.84rem;">No notes in this category.</p>`;
    return;
  }

  notes.forEach((n) => {
    const isDone = n.status === "completed";
    const item = document.createElement("div");
    item.className = `dash-task-row ${isDone ? "done" : ""}`;
    item.style.border = "1px solid #f1f5f9";
    item.style.marginBottom = "6px";
    item.innerHTML = `
      <div class="task-left">
        <input type="checkbox" class="task-check-input" ${isDone ? "checked" : ""} />
        <span class="task-text">${escapeHtml(n.title)}</span>
      </div>
      <div class="task-tags">
        ${n.due_date ? `<span class="tag-pill today">${escapeHtml(n.due_date)}</span>` : ""}
        <button class="action-btn-del"><i class="fa-solid fa-trash"></i></button>
      </div>
    `;

    item.querySelector(".task-check-input").addEventListener("change", async () => {
      await fetch(`/api/notes/${n.id}/complete`, { method: "PUT" });
      loadNotes(status);
      loadDashboardTasks();
    });

    item.querySelector(".action-btn-del").addEventListener("click", async () => {
      await fetch(`/api/notes/${n.id}`, { method: "DELETE" });
      loadNotes(status);
      loadDashboardTasks();
    });

    container.appendChild(item);
  });
}

// --- Settings Management ---
async function loadSettings() {
  const res = await fetch("/api/settings");
  const s = await res.json();

  const providerEl = document.getElementById("setting-provider");
  if (providerEl) providerEl.value = s.active_provider || "groq";
  
  const badge = document.getElementById("active-model-badge");
  if (badge) {
    let provName = "⚡ Groq Free Active";
    if (s.active_provider === "groq") provName = "⚡ Groq Free Active";
    else if (s.active_provider === "gemini") provName = "✨ Gemini (BYOK Active)";
    else if (s.active_provider === "openrouter") provName = "OpenRouter (Free)";
    else provName = `${(s.active_provider || "groq").toUpperCase()} Active`;
    badge.textContent = provName;
  }

  const setConfiguredBadge = (elementId, isConfigured) => {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (isConfigured) {
      el.textContent = "Configured";
      el.style.color = "#059669";
      el.style.fontWeight = "600";
    } else {
      el.textContent = "Not configured";
      el.style.color = "#94a3b8";
      el.style.fontWeight = "400";
    }
  };

  setConfiguredBadge("openrouter-status-hint", s.openrouter_configured);
  setConfiguredBadge("gemini-status-hint", s.gemini_configured);
  setConfiguredBadge("groq-status-hint", s.groq_configured);

  const openrouterModelEl = document.getElementById("setting-openrouter-model");
  if (openrouterModelEl && s.openrouter_model) {
    openrouterModelEl.value = s.openrouter_model;
  }

  const groqModelEl = document.getElementById("setting-groq-model");
  if (groqModelEl && s.groq_model) {
    groqModelEl.value = s.groq_model;
  }
}

// --- User Profile & Account Management ---
async function loadUserProfile() {
  try {
    const res = await fetch("/api/user/profile");
    if (res.ok) {
      const user = await res.json();
      applyUserProfileToUI(user);
    }
  } catch (e) {
    console.warn("Could not load user profile:", e);
  }
}

async function uploadAvatarFile(file) {
  if (!file) return null;
  showToast(`Uploading photo '${file.name}'...`);
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/user/avatar", {
      method: "POST",
      body: formData
    });
    if (res.ok) {
      const data = await res.json();
      return data.avatar_url;
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(`⚠️ Avatar upload failed: ${err.detail || "Server error"}`);
      return null;
    }
  } catch (e) {
    showToast(`⚠️ Network error uploading avatar: ${e.message}`);
    return null;
  }
}

function applyUserProfileToUI(user) {
  if (!user) return;
  const name = user.name || "Faizan";
  const role = user.role || "Personal AI User";
  const gender = (user.gender || "male").toLowerCase();
  const defaultDp = gender === "female" ? DEFAULT_FEMALE_AVATAR : DEFAULT_MALE_AVATAR;
  const avatar = user.avatar_url || defaultDp;

  // Sidebar User Card
  const sidebarName = document.getElementById("user-display-name");
  if (sidebarName) sidebarName.textContent = name;
  const sidebarRole = document.getElementById("user-display-role");
  if (sidebarRole) sidebarRole.textContent = role;
  const sidebarAvatar = document.getElementById("user-avatar-img");
  if (sidebarAvatar) sidebarAvatar.src = avatar;

  // Header User Button
  const headerName = document.getElementById("header-display-name");
  if (headerName) headerName.textContent = name;
  const headerAvatar = document.getElementById("header-avatar-img");
  if (headerAvatar) headerAvatar.src = avatar;

  // Dashboard Welcome Banner
  const dashWelcomeName = document.getElementById("dash-welcome-name");
  if (dashWelcomeName) dashWelcomeName.textContent = name;

  // Profile Edit Modal Pre-fill
  const editPreviewName = document.getElementById("edit-preview-name");
  if (editPreviewName) editPreviewName.textContent = name;
  const editPreviewRole = document.getElementById("edit-preview-role");
  if (editPreviewRole) editPreviewRole.textContent = role;
  const editAvatarPreview = document.getElementById("edit-avatar-preview");
  if (editAvatarPreview) editAvatarPreview.src = avatar;

  // Gender Radio Pre-fill
  const maleRadio = document.querySelector('input[name="profile-gender"][value="male"]');
  const femaleRadio = document.querySelector('input[name="profile-gender"][value="female"]');
  const pillM = document.getElementById("pill-gender-male");
  const pillF = document.getElementById("pill-gender-female");
  if (gender === "female") {
    if (femaleRadio) femaleRadio.checked = true;
    if (pillM) pillM.classList.remove("active");
    if (pillF) pillF.classList.add("active");
  } else {
    if (maleRadio) maleRadio.checked = true;
    if (pillM) pillM.classList.add("active");
    if (pillF) pillF.classList.remove("active");
  }

  const nameInput = document.getElementById("profile-name-input");
  if (nameInput) nameInput.value = name;
  const emailInput = document.getElementById("profile-email-input");
  if (emailInput) emailInput.value = user.email || "";
  const roleInput = document.getElementById("profile-role-input");
  if (roleInput) roleInput.value = role;
  const avatarInput = document.getElementById("profile-avatar-input");
  if (avatarInput) avatarInput.value = avatar;
  const bioInput = document.getElementById("profile-bio-input");
  if (bioInput) bioInput.value = user.bio || "";
}

function switchProfileTab(tab) {
  const tabProfile = document.getElementById("tab-profile-view-btn");
  const tabReg = document.getElementById("tab-register-btn");
  const formProfile = document.getElementById("profile-edit-form");
  const formReg = document.getElementById("register-account-form");
  const modalTitle = document.getElementById("profile-modal-title");

  if (tab === "register") {
    if (tabReg) tabReg.classList.add("active");
    if (tabProfile) tabProfile.classList.remove("active");
    if (formReg) formReg.style.display = "flex";
    if (formProfile) formProfile.style.display = "none";
    if (modalTitle) modalTitle.textContent = "Create New Account";
  } else {
    if (tabProfile) tabProfile.classList.add("active");
    if (tabReg) tabReg.classList.remove("active");
    if (formProfile) formProfile.style.display = "flex";
    if (formReg) formReg.style.display = "none";
    if (modalTitle) modalTitle.textContent = "Account & Profile";
  }
}

function escapeHtml(str) {
  return (str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(msg) {
  const toast = document.createElement("div");
  toast.style.cssText = `
    position: fixed; bottom: 24px; right: 24px;
    background: #0f172a; color: #fff; padding: 10px 18px;
    border-radius: 9999px; font-weight: 600; font-size: 0.84rem;
    z-index: 9999; box-shadow: 0 10px 25px rgba(0,0,0,0.15);
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

// ==================== EMAIL STUDIO LOGIC ====================
let activeEmailTone = "Professional";
let emailStudioInitialized = false;
let isEmailDictating = false;
let emailSpeechRecognition = null;

function updateWordCharCount(sourceEl, targetEl) {
  if (!sourceEl || !targetEl) return;
  const text = sourceEl.value.trim();
  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
  const chars = text.length;
  targetEl.textContent = `${words} ${words === 1 ? "word" : "words"} (${chars} chars)`;
}

function initEmailVoiceDictation() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById("email-voice-dictate-btn");
  const label = document.getElementById("email-dictate-label");
  const status = document.getElementById("email-dictate-status");
  const keyPointsEl = document.getElementById("email-key-points");
  const countEl = document.getElementById("email-key-points-count");

  if (!btn) return;

  btn.addEventListener("click", () => {
    if (!SpeechRec) {
      showToast("⚠️ Voice dictation is not supported by your browser. Please try Google Chrome or Microsoft Edge.");
      return;
    }

    if (isEmailDictating && emailSpeechRecognition) {
      emailSpeechRecognition.stop();
      return;
    }

    try {
      emailSpeechRecognition = new SpeechRec();
      emailSpeechRecognition.continuous = true;
      emailSpeechRecognition.interimResults = true;
      emailSpeechRecognition.lang = "en-US";

      emailSpeechRecognition.onstart = () => {
        isEmailDictating = true;
        btn.classList.add("recording");
        if (label) label.textContent = "Listening...";
        if (status) status.textContent = "🎙️ Listening... Speak your points clearly";
        showToast("🎙️ Microphone active: dictating into Email Studio");
      };

      emailSpeechRecognition.onresult = (event) => {
        let interim = "";
        let finalStr = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalStr += transcript;
          } else {
            interim += transcript;
          }
        }

        if (finalStr && keyPointsEl) {
          const current = keyPointsEl.value.trim();
          const addition = finalStr.trim();
          keyPointsEl.value = current ? `${current}\n• ${addition}` : `• ${addition}`;
          updateWordCharCount(keyPointsEl, countEl);
        }

        if (status) {
          if (interim) {
            status.textContent = `🎙️ "${interim}"`;
          } else if (finalStr) {
            status.textContent = "✨ Dictation captured";
          }
        }
      };

      emailSpeechRecognition.onerror = (event) => {
        console.warn("Email voice recognition error:", event.error);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          showToast("⚠️ Microphone access denied. Please allow microphone permissions in browser.");
        } else if (event.error !== "no-speech") {
          showToast(`⚠️ Voice input: ${event.error}`);
        }
      };

      emailSpeechRecognition.onend = () => {
        isEmailDictating = false;
        btn.classList.remove("recording");
        if (label) label.textContent = "Voice Input";
        if (status) {
          if (status.textContent.includes("Listening")) {
            status.textContent = "";
          } else {
            setTimeout(() => { if (status) status.textContent = ""; }, 3000);
          }
        }
      };

      emailSpeechRecognition.start();
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
      showToast(`⚠️ Could not start voice input: ${err.message}`);
      isEmailDictating = false;
      btn.classList.remove("recording");
      if (label) label.textContent = "Voice Input";
    }
  });
}

function initEmailStudio() {
  if (emailStudioInitialized) return;
  emailStudioInitialized = true;

  // Initialize Voice Dictation
  initEmailVoiceDictation();

  // Quick Starter Chips
  const starterChips = document.querySelectorAll("#email-starter-chips .starter-chip");
  starterChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      starterChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      const purpose = chip.getAttribute("data-purpose");
      const tone = chip.getAttribute("data-tone");
      const prompt = chip.getAttribute("data-prompt");

      const purposeSelect = document.getElementById("email-purpose-select");
      if (purposeSelect && purpose) purposeSelect.value = purpose;

      if (tone) {
        activeEmailTone = tone;
        document.querySelectorAll("#tone-pill-group .tone-pill").forEach((pill) => {
          pill.classList.toggle("active", pill.getAttribute("data-tone") === tone);
        });
      }

      const keyPointsEl = document.getElementById("email-key-points");
      if (keyPointsEl && prompt) {
        keyPointsEl.value = prompt;
        updateWordCharCount(keyPointsEl, document.getElementById("email-key-points-count"));
      }

      showToast(`⚡ Loaded starter: ${chip.textContent.trim()}`);
    });
  });

  // Word & Character count listeners
  const keyPointsEl = document.getElementById("email-key-points");
  const keyPointsCountEl = document.getElementById("email-key-points-count");
  if (keyPointsEl && keyPointsCountEl) {
    keyPointsEl.addEventListener("input", () => updateWordCharCount(keyPointsEl, keyPointsCountEl));
  }

  const outputBodyEl = document.getElementById("email-output-body");
  const outputBodyCountEl = document.getElementById("email-body-count");
  if (outputBodyEl && outputBodyCountEl) {
    outputBodyEl.addEventListener("input", () => updateWordCharCount(outputBodyEl, outputBodyCountEl));
  }

  // Tone pill switching
  const tonePills = document.querySelectorAll("#tone-pill-group .tone-pill");
  tonePills.forEach((btn) => {
    btn.addEventListener("click", () => {
      tonePills.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      activeEmailTone = btn.getAttribute("data-tone") || "Professional";
    });
  });

  // Generate Email button
  const genBtn = document.getElementById("btn-generate-email");
  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      const purpose = document.getElementById("email-purpose-select").value;
      const recName = document.getElementById("email-recipient-name").value.trim();
      const recComp = document.getElementById("email-recipient-company").value.trim();
      const keyPoints = document.getElementById("email-key-points").value.trim();

      if (!keyPoints) {
        showToast("⚠️ Please enter a few key points for your email.");
        return;
      }

      genBtn.disabled = true;
      genBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating tailored email...';

      try {
        const res = await fetch("/api/email/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            purpose,
            recipient_name: recName,
            recipient_company: recComp,
            tone: activeEmailTone,
            key_points: keyPoints
          })
        });

        if (res.ok) {
          const data = await res.json();
          const subjEl = document.getElementById("email-output-subject");
          const bodyEl = document.getElementById("email-output-body");
          if (subjEl) subjEl.value = data.subject || "";
          if (bodyEl) {
            bodyEl.value = data.body || "";
            updateWordCharCount(bodyEl, document.getElementById("email-body-count"));
          }
          showToast("✨ Email generated successfully!");
        } else {
          showToast("⚠️ Failed to generate email from AI.");
        }
      } catch (err) {
        showToast(`⚠️ Error: ${err.message}`);
      } finally {
        genBtn.disabled = false;
        genBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Email with AI';
      }
    });
  }

  // Copy Email Text
  const copyBtn = document.getElementById("btn-copy-email");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const subj = document.getElementById("email-output-subject").value.trim();
      const body = document.getElementById("email-output-body").value.trim();
      if (!body) {
        showToast("⚠️ Nothing to copy yet. Generate an email first!");
        return;
      }
      const fullText = subj ? `Subject: ${subj}\n\n${body}` : body;
      navigator.clipboard.writeText(fullText).then(() => {
        showToast("📋 Email text copied to clipboard!");
      }).catch(() => {
        showToast("⚠️ Failed to copy to clipboard.");
      });
    });
  }

  // Download .eml
  const dlBtn = document.getElementById("btn-download-email");
  if (dlBtn) {
    dlBtn.addEventListener("click", () => {
      const subj = document.getElementById("email-output-subject").value.trim() || "Draft Email";
      const body = document.getElementById("email-output-body").value.trim();
      if (!body) {
        showToast("⚠️ Please generate or write an email first.");
        return;
      }
      const emlContent = `To: \nSubject: ${subj}\nX-Unsent: 1\nContent-Type: text/plain; charset=utf-8\n\n${body}`;
      const blob = new Blob([emlContent], { type: "message/rfc822" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${subj.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.eml`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("📥 Downloaded as .eml draft file!");
    });
  }

  // Open in Mail App
  const openMailBtn = document.getElementById("btn-open-mailapp");
  if (openMailBtn) {
    openMailBtn.addEventListener("click", () => {
      const subj = document.getElementById("email-output-subject").value.trim();
      const body = document.getElementById("email-output-body").value.trim();
      if (!body) {
        showToast("⚠️ Please generate or write an email first.");
        return;
      }
      window.location.href = `mailto:?subject=${encodeURIComponent(subj)}&body=${encodeURIComponent(body)}`;
    });
  }
}

// ==================== IMAGE STUDIO LOGIC ====================
const SOCIAL_PRESETS = {
  whatsapp: [
    { id: "wa_dp", name: "WhatsApp Profile Picture (DP)", width: 1080, height: 1080, ratio: "1:1", defaultMode: "circle" },
    { id: "wa_status", name: "WhatsApp Status / Story", width: 1080, height: 1920, ratio: "9:16", defaultMode: "blur" }
  ],
  instagram: [
    { id: "ig_square", name: "Instagram Square Post (1:1)", width: 1080, height: 1080, ratio: "1:1", defaultMode: "blur" },
    { id: "ig_portrait", name: "Instagram Portrait Post (4:5)", width: 1080, height: 1350, ratio: "4:5", defaultMode: "blur" },
    { id: "ig_story", name: "Instagram Story / Reel (9:16)", width: 1080, height: 1920, ratio: "9:16", defaultMode: "blur" },
    { id: "ig_landscape", name: "Instagram Landscape Post", width: 1080, height: 566, ratio: "1.91:1", defaultMode: "blur" }
  ],
  facebook: [
    { id: "fb_dp", name: "Facebook Profile Picture", width: 1080, height: 1080, ratio: "1:1", defaultMode: "circle" },
    { id: "fb_cover", name: "Facebook Cover Banner", width: 1640, height: 624, ratio: "16:9", defaultMode: "blur" },
    { id: "fb_post", name: "Facebook Feed Post", width: 1200, height: 630, ratio: "1.91:1", defaultMode: "blur" }
  ],
  youtube: [
    { id: "yt_thumb", name: "YouTube Video Thumbnail", width: 1280, height: 720, ratio: "16:9", defaultMode: "blur" },
    { id: "yt_banner", name: "YouTube Channel Banner", width: 2560, height: 1440, ratio: "16:9", defaultMode: "blur" },
    { id: "yt_avatar", name: "YouTube Profile Avatar", width: 800, height: 800, ratio: "1:1", defaultMode: "circle" }
  ],
  linkedin: [
    { id: "li_avatar", name: "LinkedIn Profile Picture", width: 800, height: 800, ratio: "1:1", defaultMode: "circle" },
    { id: "li_banner", name: "LinkedIn Cover Banner", width: 1584, height: 396, ratio: "4:1", defaultMode: "blur" },
    { id: "li_post", name: "LinkedIn Feed Post", width: 1200, height: 627, ratio: "1.91:1", defaultMode: "blur" }
  ],
  twitter: [
    { id: "x_avatar", name: "Twitter / X Profile Picture", width: 800, height: 800, ratio: "1:1", defaultMode: "circle" },
    { id: "x_header", name: "Twitter / X Header Banner", width: 1500, height: 500, ratio: "3:1", defaultMode: "blur" },
    { id: "x_post", name: "Twitter / X In-Stream Post", width: 1200, height: 675, ratio: "16:9", defaultMode: "blur" }
  ],
  custom: [
    { id: "custom_square", name: "Square (1:1 • 1080 × 1080)", width: 1080, height: 1080, ratio: "1:1", defaultMode: "blur" },
    { id: "custom_landscape", name: "Widescreen (16:9 • 1920 × 1080)", width: 1920, height: 1080, ratio: "16:9", defaultMode: "blur" },
    { id: "custom_vertical", name: "Vertical (9:16 • 1080 × 1920)", width: 1080, height: 1920, ratio: "9:16", defaultMode: "blur" },
    { id: "custom_classic", name: "Standard (4:3 • 1440 × 1080)", width: 1440, height: 1080, ratio: "4:3", defaultMode: "blur" }
  ]
};

// Studio Framing State
let studioImage = null;
let studioPlatform = "whatsapp";
let studioPreset = SOCIAL_PRESETS.whatsapp[0];
let studioMode = "blur";
let studioZoom = 1.0;
let studioBlur = 25;
let studioPanX = 0;
let studioPanY = 0;
let studioRotation = 0;
let imageStudioInitialized = false;

// Retouch Suite State (Non-destructive, expression & geometry strictly preserved)
let retouchGlow = 35; // 0-100%
let retouchDarkCircles = true; // boolean
let retouchDarkCirclesIntensity = 65; // 0-100%
let retouchSmooth = 25; // 0-100%
let retouchWarmth = 10; // -50 to +50
let isComparingOriginal = false;

// Retouch cache to guarantee 60fps responsive panning & zooming
let cachedRetouchCanvas = null;
let cachedRetouchKey = null;

function invalidateRetouchCache() {
  cachedRetouchCanvas = null;
  cachedRetouchKey = null;
}

const RETOUCH_PRESETS = {
  glow: { glow: 50, darkCircles: true, darkCirclesIntensity: 65, smooth: 30, warmth: 15 },
  undereye: { glow: 25, darkCircles: true, darkCirclesIntensity: 90, smooth: 20, warmth: 5 },
  glam: { glow: 65, darkCircles: true, darkCirclesIntensity: 85, smooth: 45, warmth: 20 },
  reset: { glow: 0, darkCircles: false, darkCirclesIntensity: 0, smooth: 0, warmth: 0 }
};

function applyRetouchPreset(presetKey) {
  const preset = RETOUCH_PRESETS[presetKey];
  if (!preset) return;

  retouchGlow = preset.glow;
  retouchDarkCircles = preset.darkCircles;
  retouchDarkCirclesIntensity = preset.darkCirclesIntensity;
  retouchSmooth = preset.smooth;
  retouchWarmth = preset.warmth;

  // Update UI elements
  const toggleDark = document.getElementById("toggle-dark-circles");
  if (toggleDark) toggleDark.checked = preset.darkCircles;

  const rowDark = document.getElementById("row-dark-circles-slider");
  if (rowDark) rowDark.style.display = preset.darkCircles ? "flex" : "none";

  const sliderDark = document.getElementById("slider-dark-circles");
  if (sliderDark) sliderDark.value = preset.darkCirclesIntensity;
  const labelDark = document.getElementById("label-dark-circles");
  if (labelDark) labelDark.textContent = `${preset.darkCirclesIntensity}%`;

  const sliderGlow = document.getElementById("slider-face-glow");
  if (sliderGlow) sliderGlow.value = preset.glow;
  const labelGlow = document.getElementById("label-face-glow");
  if (labelGlow) labelGlow.textContent = `${preset.glow}%`;

  const sliderSmooth = document.getElementById("slider-skin-smooth");
  if (sliderSmooth) sliderSmooth.value = preset.smooth;
  const labelSmooth = document.getElementById("label-skin-smooth");
  if (labelSmooth) labelSmooth.textContent = `${preset.smooth}%`;

  const sliderWarmth = document.getElementById("slider-face-warmth");
  if (sliderWarmth) sliderWarmth.value = preset.warmth;
  const labelWarmth = document.getElementById("label-face-warmth");
  if (labelWarmth) labelWarmth.textContent = `${preset.warmth > 0 ? "+" : ""}${preset.warmth}`;

  // Update active pill button
  document.querySelectorAll(".retouch-pill-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.id === `preset-retouch-${presetKey}`);
  });

  invalidateRetouchCache();
  renderStudioCanvas();
  showToast(`✨ Applied Preset: ${presetKey.toUpperCase()}`);
}

/**
 * Pure client-side Canvas pixel processing engine.
 * STRICT GUARANTEE: Does not alter facial geometry, eye shape, smile, nose, or expressions.
 */
function getRetouchedCanvas(sourceImg) {
  if (!sourceImg) return null;

  // If compare mode is active or all retouch filters are inactive/zero, return original source
  const isRetouchActive =
    !isComparingOriginal &&
    (retouchGlow > 0 ||
      (retouchDarkCircles && retouchDarkCirclesIntensity > 0) ||
      retouchSmooth > 0 ||
      retouchWarmth !== 0);

  if (!isRetouchActive) {
    return sourceImg;
  }

  // Check cache to avoid re-processing on zoom or pan
  const cacheKey = `${sourceImg.src}_${sourceImg.width}_${sourceImg.height}_${retouchGlow}_${retouchDarkCircles ? retouchDarkCirclesIntensity : 0}_${retouchSmooth}_${retouchWarmth}`;
  if (cachedRetouchCanvas && cachedRetouchKey === cacheKey) {
    return cachedRetouchCanvas;
  }

  const w = sourceImg.width;
  const h = sourceImg.height;
  const offscreen = document.createElement("canvas");
  offscreen.width = w;
  offscreen.height = h;
  const offCtx = offscreen.getContext("2d", { willReadFrequently: true });
  offCtx.drawImage(sourceImg, 0, 0, w, h);

  const imgData = offCtx.getImageData(0, 0, w, h);
  const data = imgData.data;

  // Filter parameters
  const glowVal = retouchGlow / 100;
  const underEyeActive = retouchDarkCircles && retouchDarkCirclesIntensity > 0;
  const underEyeIntensity = underEyeActive ? retouchDarkCirclesIntensity / 100 : 0;
  const smoothFactor = (retouchSmooth / 100) * 0.70;
  const warmth = retouchWarmth;

  // Pass 1: Edge-preserving skin smoothing (bilateral approximation)
  // Keeps eyes, eyelashes, lips, hair, and outlines crisp while smoothing pores/blemishes
  if (smoothFactor > 0.02) {
    const copy = new Uint8ClampedArray(data);
    const stepX = 4;
    const stepY = w * 4;
    const colorThreshold = 45; // Separates skin texture from sharp facial borders

    for (let y = 1; y < h - 1; y += 1) {
      const rowOffset = y * stepY;
      for (let x = 1; x < w - 1; x += 1) {
        const idx = rowOffset + (x * 4);
        const r0 = copy[idx];
        const g0 = copy[idx + 1];
        const b0 = copy[idx + 2];

        // Only smooth human skin undertones: R > G, G >= B - 8, R > 50
        if (r0 > g0 && g0 >= (b0 - 8) && r0 > 50) {
          let sumR = r0 * 2;
          let sumG = g0 * 2;
          let sumB = b0 * 2;
          let totalWeight = 2;

          const neighbors = [idx - stepX, idx + stepX, idx - stepY, idx + stepY];
          for (let n = 0; n < 4; n++) {
            const nIdx = neighbors[n];
            const nr = copy[nIdx];
            const ng = copy[nIdx + 1];
            const nb = copy[nIdx + 2];
            const colorDist = Math.abs(r0 - nr) + Math.abs(g0 - ng) + Math.abs(b0 - nb);

            if (colorDist < colorThreshold) {
              const weight = 1.0 - (colorDist / colorThreshold);
              sumR += nr * weight;
              sumG += ng * weight;
              sumB += nb * weight;
              totalWeight += weight;
            }
          }

          const avgR = sumR / totalWeight;
          const avgG = sumG / totalWeight;
          const avgB = sumB / totalWeight;

          data[idx] = Math.round(r0 * (1 - smoothFactor) + avgR * smoothFactor);
          data[idx + 1] = Math.round(g0 * (1 - smoothFactor) + avgG * smoothFactor);
          data[idx + 2] = Math.round(b0 * (1 - smoothFactor) + avgB * smoothFactor);
        }
      }
    }
  }

  // Pass 2: Natural Face Glow Up + Under-Eye Dark Circles Lift + Warmth
  for (let y = 0; y < h; y++) {
    const normY = y / h;
    const isUnderEyeY = normY >= 0.22 && normY <= 0.62;
    const underEyeYWeight = isUnderEyeY ? Math.sin(((normY - 0.22) / 0.40) * Math.PI) : 0;
    const rowOffset = y * w * 4;

    for (let x = 0; x < w; x++) {
      const idx = rowOffset + (x * 4);
      let r = data[idx];
      let g = data[idx + 1];
      let b = data[idx + 2];

      const lum = 0.299 * r + 0.587 * g + 0.114 * b;

      // 1. Natural Face Light & Midtone Radiance Lift (Glow Up)
      if (glowVal > 0) {
        // Softbox bell curve lifting midtone shadows and skin tones without clipping pure white or crushing blacks
        const midtoneMask = Math.sin((lum / 255) * Math.PI);
        const glowBoost = 1.0 + (glowVal * 0.42 * midtoneMask);
        r = Math.min(255, r * glowBoost);
        g = Math.min(255, g * glowBoost);
        b = Math.min(255, b * glowBoost);
      }

      // 2. Dark Circles Remover (Under-Eye Conceal & Lift)
      if (underEyeActive && isUnderEyeY) {
        const normX = x / w;
        if (normX >= 0.18 && normX <= 0.82) {
          const underEyeXWeight = Math.sin(((normX - 0.18) / 0.64) * Math.PI);
          const spatialWeight = underEyeYWeight * underEyeXWeight;

          // Target dark circles & tear trough depression: low-to-medium luminance in skin tone
          const isSkinTone = r > g && g >= (b - 12) && r > 45;
          if (isSkinTone && lum > 25 && lum < 175) {
            const depression = Math.max(0, (165 - lum) / 130);
            const blueShadowCast = Math.max(0, b - (g * 0.82)) / 80;
            const darkCircleStrength = depression * (0.65 + Math.min(1.0, blueShadowCast));

            const liftAmount = underEyeIntensity * darkCircleStrength * spatialWeight;

            if (liftAmount > 0) {
              // Lift luminance smoothly towards cheek tone and neutralize blue/purple undertones
              r = Math.min(255, r + 48 * liftAmount);
              g = Math.min(255, g + 40 * liftAmount);
              b = Math.min(255, b + 16 * liftAmount);
            }
          }
        }
      }

      // 3. Skin Tone Warmth Adjustment
      if (warmth !== 0) {
        const wNorm = warmth / 50; // -1.0 to +1.0
        if (wNorm > 0) {
          // Warm golden softbox
          r = Math.min(255, r + 18 * wNorm);
          g = Math.min(255, g + 8 * wNorm);
          b = Math.max(0, b - 10 * wNorm);
        } else {
          // Cool tone
          const cNorm = Math.abs(wNorm);
          b = Math.min(255, b + 16 * cNorm);
          r = Math.max(0, r - 10 * cNorm);
        }
      }

      data[idx] = Math.round(r);
      data[idx + 1] = Math.round(g);
      data[idx + 2] = Math.round(b);
    }
  }

  offCtx.putImageData(imgData, 0, 0);
  cachedRetouchCanvas = offscreen;
  cachedRetouchKey = cacheKey;
  return offscreen;
}

function initImageStudio() {
  updateStudioPresetsDropdown();
  renderStudioCanvas();

  if (imageStudioInitialized) return;
  imageStudioInitialized = true;

  // Studio Subpanel Tab Switcher (Framing vs Retouch)
  const tabFramingBtn = document.getElementById("tab-studio-framing-btn");
  const tabRetouchBtn = document.getElementById("tab-studio-retouch-btn");
  const panelFraming = document.getElementById("panel-studio-framing");
  const panelRetouch = document.getElementById("panel-studio-retouch");

  if (tabFramingBtn && tabRetouchBtn && panelFraming && panelRetouch) {
    tabFramingBtn.addEventListener("click", () => {
      tabFramingBtn.classList.add("active");
      tabRetouchBtn.classList.remove("active");
      panelFraming.classList.add("active");
      panelRetouch.classList.remove("active");
    });
    tabRetouchBtn.addEventListener("click", () => {
      tabRetouchBtn.classList.add("active");
      tabFramingBtn.classList.remove("active");
      panelRetouch.classList.add("active");
      panelFraming.classList.remove("active");
    });
  }

  // Choose image file button
  const fileInput = document.getElementById("studio-file-input");
  const uploadBtn = document.getElementById("studio-upload-btn");
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) loadStudioImageFromFile(e.target.files[0]);
    });
  }

  // Canvas Drag and drop
  const dropzone = document.getElementById("studio-canvas-dropzone");
  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) loadStudioImageFromFile(e.dataTransfer.files[0]);
    });
  }

  // Platform selection tabs
  const platformTabs = document.querySelectorAll("#platform-tabs .platform-tab");
  platformTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      platformTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      studioPlatform = tab.getAttribute("data-platform") || "whatsapp";
      updateStudioPresetsDropdown();
      renderStudioCanvas();
    });
  });

  // Preset dropdown change
  const presetSelect = document.getElementById("studio-preset-select");
  if (presetSelect) {
    presetSelect.addEventListener("change", (e) => {
      const presets = SOCIAL_PRESETS[studioPlatform] || [];
      const chosen = presets.find((p) => p.id === e.target.value);
      if (chosen) {
        studioPreset = chosen;
        if (chosen.defaultMode && chosen.defaultMode !== studioMode) {
          setStudioMode(chosen.defaultMode);
        }
        renderStudioCanvas();
      }
    });
  }

  // Fitting mode radios
  const modeRadios = document.querySelectorAll('input[name="studio-mode"]');
  modeRadios.forEach((radio) => {
    radio.addEventListener("change", (e) => {
      setStudioMode(e.target.value);
      renderStudioCanvas();
    });
  });

  // Framing Sliders
  const zoomSlider = document.getElementById("slider-zoom");
  if (zoomSlider) {
    zoomSlider.addEventListener("input", (e) => {
      studioZoom = parseFloat(e.target.value);
      document.getElementById("label-zoom").textContent = `${studioZoom.toFixed(2)}x`;
      renderStudioCanvas();
    });
  }

  const blurSlider = document.getElementById("slider-blur");
  if (blurSlider) {
    blurSlider.addEventListener("input", (e) => {
      studioBlur = parseInt(e.target.value);
      document.getElementById("label-blur").textContent = `${studioBlur}px`;
      renderStudioCanvas();
    });
  }

  const panXSlider = document.getElementById("slider-pan-x");
  if (panXSlider) {
    panXSlider.addEventListener("input", (e) => {
      studioPanX = parseInt(e.target.value);
      document.getElementById("label-pan-x").textContent = `${studioPanX}px`;
      renderStudioCanvas();
    });
  }

  const panYSlider = document.getElementById("slider-pan-y");
  if (panYSlider) {
    panYSlider.addEventListener("input", (e) => {
      studioPanY = parseInt(e.target.value);
      document.getElementById("label-pan-y").textContent = `${studioPanY}px`;
      renderStudioCanvas();
    });
  }

  // Rotate & Reset Framing
  const rotateBtn = document.getElementById("studio-rotate-btn");
  if (rotateBtn) {
    rotateBtn.addEventListener("click", () => {
      studioRotation = (studioRotation + 90) % 360;
      renderStudioCanvas();
    });
  }

  const resetBtn = document.getElementById("studio-reset-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      studioZoom = 1.0;
      studioPanX = 0;
      studioPanY = 0;
      studioRotation = 0;
      if (zoomSlider) zoomSlider.value = "1.0";
      if (panXSlider) panXSlider.value = "0";
      if (panYSlider) panYSlider.value = "0";
      document.getElementById("label-zoom").textContent = "1.0x";
      document.getElementById("label-pan-x").textContent = "0px";
      document.getElementById("label-pan-y").textContent = "0px";
      renderStudioCanvas();
    });
  }

  // --- AI Retouch Suite Event Listeners ---
  const toggleDarkCircles = document.getElementById("toggle-dark-circles");
  const rowDarkCircles = document.getElementById("row-dark-circles-slider");
  if (toggleDarkCircles) {
    toggleDarkCircles.addEventListener("change", (e) => {
      retouchDarkCircles = e.target.checked;
      if (rowDarkCircles) rowDarkCircles.style.display = retouchDarkCircles ? "flex" : "none";
      invalidateRetouchCache();
      renderStudioCanvas();
    });
  }

  const sliderDarkCircles = document.getElementById("slider-dark-circles");
  if (sliderDarkCircles) {
    sliderDarkCircles.addEventListener("input", (e) => {
      retouchDarkCirclesIntensity = parseInt(e.target.value);
      const label = document.getElementById("label-dark-circles");
      if (label) label.textContent = `${retouchDarkCirclesIntensity}%`;
      invalidateRetouchCache();
      renderStudioCanvas();
    });
  }

  const sliderFaceGlow = document.getElementById("slider-face-glow");
  if (sliderFaceGlow) {
    sliderFaceGlow.addEventListener("input", (e) => {
      retouchGlow = parseInt(e.target.value);
      const label = document.getElementById("label-face-glow");
      if (label) label.textContent = `${retouchGlow}%`;
      invalidateRetouchCache();
      renderStudioCanvas();
    });
  }

  const sliderSkinSmooth = document.getElementById("slider-skin-smooth");
  if (sliderSkinSmooth) {
    sliderSkinSmooth.addEventListener("input", (e) => {
      retouchSmooth = parseInt(e.target.value);
      const label = document.getElementById("label-skin-smooth");
      if (label) label.textContent = `${retouchSmooth}%`;
      invalidateRetouchCache();
      renderStudioCanvas();
    });
  }

  const sliderFaceWarmth = document.getElementById("slider-face-warmth");
  if (sliderFaceWarmth) {
    sliderFaceWarmth.addEventListener("input", (e) => {
      retouchWarmth = parseInt(e.target.value);
      const label = document.getElementById("label-face-warmth");
      if (label) label.textContent = `${retouchWarmth > 0 ? "+" : ""}${retouchWarmth}`;
      invalidateRetouchCache();
      renderStudioCanvas();
    });
  }

  // 1-Click Retouch Presets
  const presetGlowBtn = document.getElementById("preset-retouch-glow");
  if (presetGlowBtn) presetGlowBtn.addEventListener("click", () => applyRetouchPreset("glow"));

  const presetUnderEyeBtn = document.getElementById("preset-retouch-undereye");
  if (presetUnderEyeBtn) presetUnderEyeBtn.addEventListener("click", () => applyRetouchPreset("undereye"));

  const presetGlamBtn = document.getElementById("preset-retouch-glam");
  if (presetGlamBtn) presetGlamBtn.addEventListener("click", () => applyRetouchPreset("glam"));

  const presetResetBtn = document.getElementById("preset-retouch-reset");
  if (presetResetBtn) presetResetBtn.addEventListener("click", () => applyRetouchPreset("reset"));

  // Hold to Compare (Before / After) Button & Badge
  const compareBtn = document.getElementById("btn-compare-retouch");
  const compareBadge = document.getElementById("studio-compare-badge");

  const startCompare = (e) => {
    if (e && e.cancelable) e.preventDefault();
    if (!studioImage) return;
    isComparingOriginal = true;
    if (compareBtn) compareBtn.classList.add("comparing");
    if (compareBadge) compareBadge.style.display = "inline-flex";
    renderStudioCanvas();
  };

  const endCompare = (e) => {
    if (e && e.cancelable) e.preventDefault();
    if (!isComparingOriginal) return;
    isComparingOriginal = false;
    if (compareBtn) compareBtn.classList.remove("comparing");
    if (compareBadge) compareBadge.style.display = "none";
    renderStudioCanvas();
  };

  if (compareBtn) {
    compareBtn.addEventListener("mousedown", startCompare);
    compareBtn.addEventListener("mouseup", endCompare);
    compareBtn.addEventListener("mouseleave", endCompare);
    compareBtn.addEventListener("touchstart", startCompare, { passive: false });
    compareBtn.addEventListener("touchend", endCompare);
    compareBtn.addEventListener("touchcancel", endCompare);
  }

  // Download Formatted Image Button
  const dlBtn = document.getElementById("studio-download-btn");
  if (dlBtn) {
    dlBtn.addEventListener("click", downloadStudioImage);
  }

  // Set as Assistant DP Button
  const setDpBtn = document.getElementById("studio-set-dp-btn");
  if (setDpBtn) {
    setDpBtn.addEventListener("click", setStudioCanvasAsProfileDP);
  }
}

function updateStudioPresetsDropdown() {
  const select = document.getElementById("studio-preset-select");
  if (!select) return;
  const presets = SOCIAL_PRESETS[studioPlatform] || SOCIAL_PRESETS.whatsapp;
  select.innerHTML = "";
  presets.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.ratio} • ${p.width} × ${p.height})`;
    select.appendChild(opt);
  });
  studioPreset = presets[0];
  select.value = studioPreset.id;
}

function setStudioMode(mode) {
  studioMode = mode;
  document.querySelectorAll(".fitting-mode-btn").forEach((b) => b.classList.remove("active"));
  const btn = document.getElementById(`mode-${mode}`);
  if (btn) btn.classList.add("active");
  const radio = document.querySelector(`input[name="studio-mode"][value="${mode}"]`);
  if (radio) radio.checked = true;

  const blurRow = document.getElementById("row-blur-slider");
  if (blurRow) blurRow.style.display = (mode === "blur") ? "flex" : "none";
}

function loadStudioImageFromFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      studioImage = img;
      invalidateRetouchCache();
      document.getElementById("studio-empty-overlay").style.display = "none";
      renderStudioCanvas();
      showToast(`📸 Loaded image: ${file.name} (${img.width} × ${img.height})`);
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function renderStudioCanvas() {
  const canvas = document.getElementById("studio-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const targetW = studioPreset.width || 1080;
  const targetH = studioPreset.height || 1080;
  canvas.width = targetW;
  canvas.height = targetH;

  // Update badge in footer
  const badge = document.getElementById("studio-resolution-badge");
  if (badge) {
    badge.querySelector("span").textContent = `${studioPreset.name} (${studioPreset.width} × ${studioPreset.height} px)`;
  }

  // If no image loaded yet, draw empty grid canvas
  if (!studioImage) {
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, targetW, targetH);
    return;
  }

  // Get active source (either raw photo or non-destructive retouched canvas)
  const activeImageSource = getRetouchedCanvas(studioImage);

  ctx.clearRect(0, 0, targetW, targetH);

  // Background Rendering
  if (studioMode === "blur") {
    // Draw heavily blurred background covering full canvas
    ctx.save();
    ctx.filter = `blur(${studioBlur}px) brightness(0.7)`;
    const bgScale = Math.max(targetW / studioImage.width, targetH / studioImage.height) * 1.2;
    const bgW = studioImage.width * bgScale;
    const bgH = studioImage.height * bgScale;
    ctx.drawImage(activeImageSource, (targetW - bgW) / 2, (targetH - bgH) / 2, bgW, bgH);
    ctx.restore();

    // Darken overlay for depth
    ctx.fillStyle = "rgba(0, 0, 0, 0.18)";
    ctx.fillRect(0, 0, targetW, targetH);
  } else if (studioMode === "circle") {
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, targetW, targetH);
  } else if (studioMode === "fit") {
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, targetW, targetH);
  }

  // Foreground Image Rendering with transform
  ctx.save();

  // Circle mask clipping
  if (studioMode === "circle") {
    ctx.beginPath();
    const radius = Math.min(targetW, targetH) * 0.48;
    ctx.arc(targetW / 2, targetH / 2, radius, 0, Math.PI * 2, true);
    ctx.closePath();
    ctx.clip();
  }

  // Base scale calculation
  let scale = 1.0;
  if (studioMode === "crop") {
    scale = Math.max(targetW / studioImage.width, targetH / studioImage.height) * studioZoom;
  } else if (studioMode === "fit") {
    scale = Math.min(targetW / studioImage.width, targetH / studioImage.height) * studioZoom;
  } else {
    // Blur or Circle: fit cleanly into view
    scale = Math.min(targetW / studioImage.width, targetH / studioImage.height) * studioZoom;
  }

  const drawW = studioImage.width * scale;
  const drawH = studioImage.height * scale;

  // Center coordinate with pan
  const centerX = (targetW / 2) + studioPanX;
  const centerY = (targetH / 2) + studioPanY;

  ctx.translate(centerX, centerY);
  if (studioRotation !== 0) {
    ctx.rotate((studioRotation * Math.PI) / 180);
  }

  // Drop shadow for blur mode to pop out foreground image
  if (studioMode === "blur") {
    ctx.shadowColor = "rgba(0, 0, 0, 0.45)";
    ctx.shadowBlur = 30;
    ctx.shadowOffsetY = 10;
  }

  ctx.drawImage(activeImageSource, -drawW / 2, -drawH / 2, drawW, drawH);
  ctx.restore();

  // Outer border guide for circular DP
  if (studioMode === "circle") {
    ctx.save();
    ctx.beginPath();
    const radius = Math.min(targetW, targetH) * 0.48;
    ctx.arc(targetW / 2, targetH / 2, radius, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(59, 130, 246, 0.4)";
    ctx.lineWidth = Math.max(4, Math.round(targetW * 0.005));
    ctx.stroke();
    ctx.restore();
  }
}

function downloadStudioImage() {
  const canvas = document.getElementById("studio-canvas");
  if (!canvas || !studioImage) {
    showToast("⚠️ Please upload an image first.");
    return;
  }

  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const cleanName = `${studioPreset.id}_${studioPreset.width}x${studioPreset.height}.png`;
    a.download = cleanName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast(`🎉 Downloaded formatted image: ${cleanName}`);
  }, "image/png");
}

async function setStudioCanvasAsProfileDP() {
  const canvas = document.getElementById("studio-canvas");
  if (!canvas || !studioImage) {
    showToast("⚠️ Please upload an image first.");
    return;
  }

  showToast("Updating your profile picture...");
  canvas.toBlob(async (blob) => {
    if (!blob) return;
    const file = new File([blob], "custom_profile_dp.png", { type: "image/png" });
    const uploadedUrl = await uploadAvatarFile(file);
    if (uploadedUrl) {
      const profRes = await fetch("/api/user/profile");
      if (profRes.ok) {
        const curr = await profRes.json();
        const updateRes = await fetch("/api/user/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: curr.name,
            email: curr.email,
            gender: curr.gender || "male",
            role: curr.role,
            avatar_url: uploadedUrl,
            bio: curr.bio
          })
        });
        if (updateRes.ok) {
          const data = await updateRes.json();
          applyUserProfileToUI(data.user);
          showToast("✅ Profile DP updated with your customized picture!");
        }
      }
    }
  }, "image/png");
}

