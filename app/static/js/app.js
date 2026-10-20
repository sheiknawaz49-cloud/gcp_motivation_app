// Daily Motivation App Logic • Motiveate AI
const state = window.INITIAL_STATE || {};
let currentQuote = state.quote || "";
let currentAudioUrl = state.audioUrl || "";
let currentStreak = state.streak || 1;
let maxStreak = state.maxStreak || 1;
let dailyCount = state.dailyCount || 0;
let savedDailyCards = Array.isArray(state.dailyCards) ? [...state.dailyCards] : [];
let limitReached = !!state.limitReached || dailyCount >= 3;

let quoteQueue = [];
let isFetchingBatch = false;
let isGeneratingAudio = false;

// 3 Quotes Per Day Limit & Friendly Completion Message
const COMPLETION_MESSAGE = "🌿 You've completed your 3 mindful quotes for today. Come back tomorrow to grow your streak!";
let isShowingCompletionMessage = false;
let cycleCardIndex = 0;

// Cache generated audio URLs by quote text so replaying is 100% free
const audioCache = {};
if (currentAudioUrl && currentQuote) {
    audioCache[currentQuote] = currentAudioUrl;
}
if (currentQuote && savedDailyCards.length === 0) {
    savedDailyCards.push({ quote: currentQuote, audio_url: currentAudioUrl });
}

// DOM Elements
const stage = document.getElementById('quoteStage');
const quoteEl = document.getElementById('quoteText');
const player = document.getElementById('voicePlayer');
const likeBtn = document.getElementById('likeBtn');
const dislikeBtn = document.getElementById('dislikeBtn');
const voiceBtn = document.getElementById('voiceBtn');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');
const moreBtn = document.getElementById('moreBtn');
const streakBadge = document.getElementById('streakBadge');
const bufferStatus = document.getElementById('bufferStatus');
const cardLoader = document.getElementById('cardLoader');
const loaderMsg = document.getElementById('loaderMsg');
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeToggleIcon = document.getElementById('themeToggleIcon');
const themeModeSelect = document.getElementById('themeModeSelect');

// 1. Daily Eye-Friendly Themes Rotation (6 Soothing Palettes)
const THEMES = [
    'warm-sage',
    'morning-sand',
    'sky-mist',
    'lavender-calm',
    'peach-clay',
    'mint-alabaster'
];

function applyDailyTheme() {
    const now = new Date();
    const start = new Date(now.getFullYear(), 0, 0);
    const diff = (now - start) + ((start.getTimezoneOffset() - now.getTimezoneOffset()) * 60 * 1000);
    const dayOfYear = Math.floor(diff / (1000 * 60 * 60 * 24));
    const themeIndex = Math.abs(dayOfYear) % THEMES.length;
    const activeTheme = THEMES[themeIndex];
    document.documentElement.setAttribute('data-theme', activeTheme);
    if (document.body) {
        document.body.setAttribute('data-theme', activeTheme);
    }
}
applyDailyTheme();

// 1b. Light / Dark / System Preference Mode Management
let currentThemeMode = localStorage.getItem('motiveate_theme_mode') || state.themeMode || 'auto';

function applyThemeMode(mode) {
    let resolvedDark = false;
    if (mode === 'dark') {
        resolvedDark = true;
    } else if (mode === 'light') {
        resolvedDark = false;
    } else {
        // System preference
        resolvedDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    document.documentElement.setAttribute('data-mode', resolvedDark ? 'dark' : 'light');
    if (document.body) {
        document.body.setAttribute('data-mode', resolvedDark ? 'dark' : 'light');
    }

    // Update Top Bar Toggle Button Icon & Tooltip
    const iconEl = document.getElementById('themeToggleIcon');
    const toggleBtn = document.getElementById('themeToggleBtn');
    if (iconEl && toggleBtn) {
        if (mode === 'auto') {
            iconEl.innerText = '🌓';
            toggleBtn.title = `Theme: System (${resolvedDark ? 'Dark' : 'Light'}) • Click for Light`;
        } else if (mode === 'light') {
            iconEl.innerText = '☀️';
            toggleBtn.title = 'Theme: Light • Click for Dark';
        } else {
            iconEl.innerText = '🌙';
            toggleBtn.title = 'Theme: Dark • Click for System';
        }
    }

    // Sync modal select dropdown if present
    const selectEl = document.getElementById('themeModeSelect');
    if (selectEl && selectEl.value !== mode) {
        selectEl.value = mode;
    }
}

function setThemeMode(mode) {
    if (!['auto', 'light', 'dark'].includes(mode)) mode = 'auto';
    currentThemeMode = mode;
    try {
        localStorage.setItem('motiveate_theme_mode', mode);
    } catch (e) {}
    applyThemeMode(mode);
}

function cycleThemeMode() {
    if (currentThemeMode === 'auto') {
        setThemeMode('light');
    } else if (currentThemeMode === 'light') {
        setThemeMode('dark');
    } else {
        setThemeMode('auto');
    }
}

// Listen to System OS Theme Changes in real-time
if (window.matchMedia) {
    try {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
            if (currentThemeMode === 'auto') {
                applyThemeMode('auto');
            }
        });
    } catch (e) {}
}

applyThemeMode(currentThemeMode);

// 2. Buffer & Limit Status Display
function updateBufferBadge() {
    if (!bufferStatus) return;
    if (isFetchingBatch && quoteQueue.length === 0) {
        bufferStatus.innerHTML = '<span class="tiny-spinner"></span> Syncing deck...';
    } else if (limitReached && quoteQueue.length === 0) {
        bufferStatus.innerHTML = '🌿 3 of 3 complete';
    } else if (quoteQueue.length > 0) {
        bufferStatus.innerHTML = '⚡ ' + quoteQueue.length + ' ready';
    } else {
        bufferStatus.innerHTML = '✨ Ready';
    }
}

// 3. Prefetch quotes respecting daily limit (Fast & Free—no upfront TTS!)
async function prefetchQuotes() {
    if (isFetchingBatch) return;
    if (limitReached && quoteQueue.length === 0) {
        updateBufferBadge();
        return;
    }

    isFetchingBatch = true;
    updateBufferBadge();
    try {
        const res = await fetch('/api/batch?count=3');
        if (res.ok) {
            const data = await res.json();
            if (data.cards && data.cards.length > 0) {
                for (const c of data.cards) {
                    if (c && c.quote && !quoteQueue.some(q => q.quote === c.quote)) {
                        quoteQueue.push(c);
                    }
                }
            }
            if (data.daily_cards && data.daily_cards.length > 0) {
                savedDailyCards = data.daily_cards;
            }
            if (data.limit_reached !== undefined) {
                limitReached = data.limit_reached;
            }
            if (data.streak !== undefined) {
                currentStreak = data.streak;
                if (streakBadge) streakBadge.innerText = '🔥 ' + currentStreak;
            }
        }
    } catch (err) {
        console.error('Prefetch error:', err);
    } finally {
        isFetchingBatch = false;
        updateBufferBadge();
    }
}

// 4. Smooth Card Transition Helper
function displayCard(quote, audioUrl) {
    if (!stage || !quoteEl) return;
    stage.classList.add('slide-out-left');

    setTimeout(() => {
        currentQuote = quote;
        currentAudioUrl = audioCache[quote] || audioUrl || "";
        quoteEl.innerText = '“' + currentQuote + '”';
        if (player) player.src = currentAudioUrl;

        // Reset action dock states
        if (likeBtn) {
            likeBtn.classList.remove('active-like');
            likeBtn.innerHTML = '👍';
        }
        if (dislikeBtn) dislikeBtn.style.opacity = '1';
        if (voiceBtn) {
            voiceBtn.innerHTML = '🔊';
            voiceBtn.title = 'Listen to voice';
            voiceBtn.style.opacity = '1';
        }

        // Streak badge reflects true daily date streak (NEVER increment on More click)
        if (streakBadge) streakBadge.innerText = '🔥 ' + currentStreak;

        stage.classList.remove('slide-out-left');
        stage.classList.add('slide-in-right');

        void stage.offsetWidth;
        stage.classList.remove('slide-in-right');
    }, 240);
}

function displayCompletionMessage() {
    if (!stage || !quoteEl) return;
    stage.classList.add('slide-out-left');

    setTimeout(() => {
        currentQuote = COMPLETION_MESSAGE;
        currentAudioUrl = "";
        quoteEl.innerText = COMPLETION_MESSAGE;
        if (player) {
            player.pause();
            player.src = "";
        }

        if (likeBtn) {
            likeBtn.classList.remove('active-like');
            likeBtn.innerHTML = '🌱';
        }
        if (voiceBtn) {
            voiceBtn.innerHTML = '✨';
            voiceBtn.title = 'Completed for today';
        }

        if (streakBadge) streakBadge.innerText = '🔥 ' + currentStreak;
        if (bufferStatus) bufferStatus.innerHTML = '🌿 3 of 3 complete';

        stage.classList.remove('slide-out-left');
        stage.classList.add('slide-in-right');

        void stage.offsetWidth;
        stage.classList.remove('slide-in-right');
    }, 240);
}

// 5. Show Next Card or Cycle Through Today's 3 Saved Cards
async function showNextCard() {
    if (player) {
        player.pause();
        player.currentTime = 0;
    }

    // Case A: Quotes remaining in queue
    if (quoteQueue.length > 0) {
        const nextItem = quoteQueue.shift();
        isShowingCompletionMessage = false;
        displayCard(nextItem.quote, nextItem.audio_url);
        updateBufferBadge();
        if (!limitReached && quoteQueue.length <= 1) {
            prefetchQuotes();
        }
        return;
    }

    // Case B: Queue empty, try prefetch if limit not yet reached
    if (!limitReached) {
        if (loaderMsg && cardLoader) {
            loaderMsg.innerText = 'Crafting fresh personalized quotes...';
            cardLoader.classList.add('active');
        }
        await prefetchQuotes();
        if (cardLoader) cardLoader.classList.remove('active');

        if (quoteQueue.length > 0) {
            const nextItem = quoteQueue.shift();
            isShowingCompletionMessage = false;
            displayCard(nextItem.quote, nextItem.audio_url);
            updateBufferBadge();
            return;
        }
    }

    // Case C: All 3 quotes for today have been viewed & limit_reached is true
    // Alternate between completion message and cycling through today's 3 saved cards
    if (!isShowingCompletionMessage) {
        isShowingCompletionMessage = true;
        displayCompletionMessage();
        cycleCardIndex = 0;
        return;
    }

    // In cycling mode: cycle through saved daily cards
    if (savedDailyCards.length > 0) {
        if (cycleCardIndex < savedDailyCards.length) {
            const card = savedDailyCards[cycleCardIndex];
            cycleCardIndex++;
            isShowingCompletionMessage = false;
            displayCard(card.quote, card.audio_url);
        } else {
            // Once cycle reaches end, show friendly completion message again
            isShowingCompletionMessage = true;
            displayCompletionMessage();
            cycleCardIndex = 0;
        }
    } else {
        displayCompletionMessage();
    }
}

// 6. On-Demand Voice Generation (Saves 80% of Cloud TTS costs!)
async function playVoice() {
    if (isGeneratingAudio) return;
    if (isShowingCompletionMessage) {
        return;
    }

    if (audioCache[currentQuote]) {
        player.src = audioCache[currentQuote];
        player.play();
        return;
    }

    isGeneratingAudio = true;
    if (voiceBtn) voiceBtn.innerHTML = '<span class="tiny-spinner"></span>';
    try {
        const res = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quote: currentQuote })
        });
        if (res.ok) {
            const data = await res.json();
            if (data.audio_url) {
                audioCache[currentQuote] = data.audio_url;
                player.src = data.audio_url;
                await player.play();
            }
        }
    } catch (err) {
        console.error('TTS error:', err);
    } finally {
        isGeneratingAudio = false;
        if (voiceBtn) voiceBtn.innerHTML = '🔊';
    }
}

// 7. High-Res 9:16 Story Card Blob Generator
async function generateCardBlob() {
    const exportQuote = document.getElementById('exportQuoteText');
    const exportStreak = document.getElementById('exportStreak');

    let quoteToExport = currentQuote;
    if (isShowingCompletionMessage && savedDailyCards.length > 0) {
        quoteToExport = savedDailyCards[0].quote;
    }

    if (exportQuote) exportQuote.innerText = quoteToExport;
    if (exportStreak) exportStreak.innerText = currentStreak;

    const exportEl = document.getElementById('storyExportCard');
    if (!exportEl) return null;

    const canvas = await html2canvas(exportEl, {
        scale: 2, // 1080x1920 Full HD resolution
        backgroundColor: '#0f172a',
        useCORS: true
    });

    return new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), 'image/png');
    });
}

function triggerDownload(blob, filename) {
    const link = document.createElement('a');
    link.download = filename || `motiveate-day-${currentStreak}.png`;
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
}

async function downloadQuoteCard() {
    const btn = document.getElementById('downloadBtn');
    const originalText = btn ? btn.innerHTML : '📥';
    if (btn) btn.innerHTML = '<span class="tiny-spinner"></span>';

    try {
        const blob = await generateCardBlob();
        if (!blob) throw new Error('Could not generate story card');
        triggerDownload(blob, `motiveate-day-${currentStreak}.png`);
        if (btn) {
            btn.innerHTML = '✅';
            setTimeout(() => { btn.innerHTML = originalText; }, 1500);
        }
    } catch (err) {
        console.error('Download error:', err);
        if (btn) btn.innerHTML = originalText;
    }
}

// 8. Modal Controls for Export & Share
function openShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.classList.add('open');
}

function closeShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.classList.remove('open');
}

async function downloadFromShare() {
    const btn = document.getElementById('modalDownloadBtn');
    const titleEl = btn ? btn.querySelector('.share-title') : null;
    const descEl = btn ? btn.querySelector('.share-desc') : null;
    const iconEl = btn ? btn.querySelector('.share-icon-wrap') : null;

    if (titleEl) titleEl.innerText = 'Generating High-Res Card...';
    if (descEl) descEl.innerText = 'Rendering 1080×1920 PNG';
    if (iconEl) iconEl.innerHTML = '<span class="tiny-spinner"></span>';

    try {
        const blob = await generateCardBlob();
        if (!blob) throw new Error('Could not generate card');
        triggerDownload(blob, `motiveate-day-${currentStreak}.png`);

        if (titleEl) titleEl.innerText = 'Downloaded to PC! ✅';
        if (descEl) descEl.innerText = 'Saved in your Downloads folder';
        if (iconEl) iconEl.innerHTML = '✅';

        setTimeout(() => {
            closeShareModal();
            setTimeout(() => {
                if (titleEl) titleEl.innerText = 'Download Story Card';
                if (descEl) descEl.innerText = 'High-Res 1080×1920 PNG saved to PC';
                if (iconEl) iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`;
            }, 300);
        }, 800);
    } catch (err) {
        console.error('Download error:', err);
        if (titleEl) titleEl.innerText = 'Download Failed';
    }
}

async function copyImageToClipboard() {
    const btn = document.getElementById('modalCopyImgBtn');
    const titleEl = btn ? btn.querySelector('.share-title') : null;
    const descEl = btn ? btn.querySelector('.share-desc') : null;
    const iconEl = btn ? btn.querySelector('.share-icon-wrap') : null;

    if (titleEl) titleEl.innerText = 'Rendering Card...';
    if (descEl) descEl.innerText = 'Copying image to clipboard';
    if (iconEl) iconEl.innerHTML = '<span class="tiny-spinner"></span>';

    try {
        const blob = await generateCardBlob();
        if (!blob) throw new Error('Could not generate card');

        if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([
                new ClipboardItem({ 'image/png': blob })
            ]);
            if (titleEl) titleEl.innerText = 'Image Copied! ✅';
            if (descEl) descEl.innerText = 'Paste anywhere with Ctrl+V';
            if (iconEl) iconEl.innerHTML = '✅';
        } else {
            triggerDownload(blob, `motiveate-day-${currentStreak}.png`);
            if (titleEl) titleEl.innerText = 'Downloaded to PC! ✅';
            if (descEl) descEl.innerText = 'Saved in your Downloads folder';
            if (iconEl) iconEl.innerHTML = '📥';
        }

        setTimeout(() => {
            closeShareModal();
            setTimeout(() => {
                if (titleEl) titleEl.innerText = 'Copy Image to Clipboard';
                if (descEl) descEl.innerText = 'Paste (Ctrl+V) into WhatsApp Web, Slack, Discord';
                if (iconEl) iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
            }, 300);
        }, 900);
    } catch (err) {
        console.error('Clipboard error:', err);
        if (titleEl) titleEl.innerText = 'Copy Failed';
    }
}

async function copyQuoteText() {
    const btn = document.getElementById('modalCopyTextBtn');
    const titleEl = btn ? btn.querySelector('.share-title') : null;
    const descEl = btn ? btn.querySelector('.share-desc') : null;
    const iconEl = btn ? btn.querySelector('.share-icon-wrap') : null;

    try {
        const quoteToShare = isShowingCompletionMessage && savedDailyCards.length > 0
            ? savedDailyCards[0].quote
            : currentQuote;
        const textToCopy = `“${quoteToShare}” — via Motiveate AI (Day ${currentStreak})`;
        await navigator.clipboard.writeText(textToCopy);
        if (titleEl) titleEl.innerText = 'Quote Text Copied! ✅';
        if (descEl) descEl.innerText = 'Ready to paste in messages or notes';
        if (iconEl) iconEl.innerHTML = '✅';

        setTimeout(() => {
            closeShareModal();
            setTimeout(() => {
                if (titleEl) titleEl.innerText = 'Copy Quote Text';
                if (descEl) descEl.innerText = 'Copy quote text to paste anywhere';
                if (iconEl) iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>`;
            }, 300);
        }, 800);
    } catch (err) {
        console.error('Copy text error:', err);
        if (titleEl) titleEl.innerText = 'Copy Failed';
    }
}

async function triggerSystemShare() {
    const btn = document.getElementById('modalSysShareBtn');
    const titleEl = btn ? btn.querySelector('.share-title') : null;
    const descEl = btn ? btn.querySelector('.share-desc') : null;
    const iconEl = btn ? btn.querySelector('.share-icon-wrap') : null;

    if (titleEl) titleEl.innerText = 'Preparing Share...';
    if (descEl) descEl.innerText = 'Generating story card';
    if (iconEl) iconEl.innerHTML = '<span class="tiny-spinner"></span>';

    try {
        const blob = await generateCardBlob();
        const file = new File([blob], `motivation-day-${currentStreak}.png`, { type: 'image/png' });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            closeShareModal();
            await navigator.share({
                title: 'Daily AI Motivation',
                text: `“${currentQuote}” — via Motiveate AI`,
                files: [file]
            });
        } else {
            triggerDownload(blob, `motiveate-day-${currentStreak}.png`);
            if (titleEl) titleEl.innerText = 'Saved to Downloads! ✅';
            if (descEl) descEl.innerText = 'Saved in your Downloads folder';
            if (iconEl) iconEl.innerHTML = '📥';
            setTimeout(() => {
                closeShareModal();
            }, 800);
        }
    } catch (err) {
        console.log('Share dismissed or cancelled:', err);
        closeShareModal();
    } finally {
        setTimeout(() => {
            if (titleEl) titleEl.innerText = 'System Share Sheet';
            if (descEl) descEl.innerText = 'Send via Windows apps or mobile share tray';
            if (iconEl) iconEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>`;
        }, 400);
    }
}

// 9. Feedback
async function sendFeedback(action) {
    if (isShowingCompletionMessage) return;
    if (action === 'like') {
        if (likeBtn) {
            likeBtn.classList.add('active-like');
            likeBtn.innerHTML = '❤️';
        }
    }
    fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, quote: currentQuote })
    });
    if (action === 'dislike') {
        showNextCard();
    }
}

// 10. Modals & Preferences
function toggleModal(show) {
    const modal = document.getElementById('editModal');
    if (show) modal.classList.add('open');
    else modal.classList.remove('open');
}

function showModalLoading() {
    toggleModal(false);
    if (loaderMsg && cardLoader) {
        loaderMsg.innerText = 'Updating your preferences & voice...';
        cardLoader.classList.add('active');
    }
}

// 11. Feature 5: Delete Account Confirmation
function confirmDeleteAccount() {
    if (confirm("Are you sure you want to permanently delete your account and all saved data?")) {
        const form = document.getElementById("deleteAccountForm");
        if (form) {
            form.submit();
        }
    }
}

// Close modal if user clicks outside modal box
window.addEventListener('click', (e) => {
    if (e.target && e.target.classList && e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

// Keyboard shortcuts
window.addEventListener('keydown', (e) => {
    const editModal = document.getElementById('editModal');
    const shareModal = document.getElementById('shareModal');
    if ((editModal && editModal.classList.contains('open')) ||
        (shareModal && shareModal.classList.contains('open'))) return;

    if (e.code === 'Space' || e.code === 'ArrowRight') {
        e.preventDefault();
        showNextCard();
    } else if (e.key.toLowerCase() === 'l') {
        sendFeedback('like');
    } else if (e.key.toLowerCase() === 's') {
        openShareModal();
    } else if (e.key.toLowerCase() === 'd') {
        downloadQuoteCard();
    }
});

// Explicitly expose functions for inline HTML event handlers
window.showNextCard = showNextCard;
window.playVoice = playVoice;
window.downloadQuoteCard = downloadQuoteCard;
window.openShareModal = openShareModal;
window.closeShareModal = closeShareModal;
window.downloadFromShare = downloadFromShare;
window.copyImageToClipboard = copyImageToClipboard;
window.copyQuoteText = copyQuoteText;
window.triggerSystemShare = triggerSystemShare;
window.sendFeedback = sendFeedback;
window.toggleModal = toggleModal;
window.showModalLoading = showModalLoading;
window.confirmDeleteAccount = confirmDeleteAccount;
window.cycleThemeMode = cycleThemeMode;
window.setThemeMode = setThemeMode;

// Initial Load & Prefetch
if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => {
        prefetchQuotes();
    });
} else {
    prefetchQuotes();
}