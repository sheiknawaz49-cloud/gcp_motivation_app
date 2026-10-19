const state = window.INITIAL_STATE || {};
let currentQuote = state.quote || "";
let currentAudioUrl = state.audioUrl || "";
let currentStreak = state.streak || 1;
let quoteQueue = [];
let isFetchingBatch = false;
let isGeneratingAudio = false;

// Cache generated audio URLs by quote text so replaying is 100% free
const audioCache = {};
if (currentAudioUrl && currentQuote) {
    audioCache[currentQuote] = currentAudioUrl;
}

const stage = document.getElementById('quoteStage');
const quoteEl = document.getElementById('quoteText');
const player = document.getElementById('voicePlayer');
const likeBtn = document.getElementById('likeBtn');
const voiceBtn = document.getElementById('voiceBtn');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');
const streakBadge = document.getElementById('streakBadge');
const bufferStatus = document.getElementById('bufferStatus');
const cardLoader = document.getElementById('cardLoader');
const loaderMsg = document.getElementById('loaderMsg');

function updateBufferBadge() {
    if (isFetchingBatch && quoteQueue.length === 0) {
        bufferStatus.innerHTML = '<span class="tiny-spinner"></span> Preloading...';
    } else if (quoteQueue.length > 0) {
        bufferStatus.innerHTML = '⚡ ' + quoteQueue.length + ' ready';
    } else {
        bufferStatus.innerHTML = '✨ Ready';
    }
}

// Prefetch 3 quotes in the background (Fast & Free—no upfront TTS!)
async function prefetchQuotes() {
    if (isFetchingBatch) return;
    isFetchingBatch = true;
    updateBufferBadge();
    try {
        const res = await fetch('/api/batch?count=3');
        if (res.ok) {
            const data = await res.json();
            if (data.cards && data.cards.length > 0) {
                quoteQueue.push(...data.cards);
            }
        }
    } catch (err) {
        console.error('Prefetch error:', err);
    } finally {
        isFetchingBatch = false;
        updateBufferBadge();
    }
}

// Smoothly animate to the next card
async function showNextCard() {
    if (quoteQueue.length === 0) {
        loaderMsg.innerText = 'Crafting fresh personalized quotes...';
        cardLoader.classList.add('active');
        await prefetchQuotes();
        cardLoader.classList.remove('active');
    }

    const nextItem = quoteQueue.shift();
    if (!nextItem) return;

    updateBufferBadge();

    if (quoteQueue.length <= 1) {
        prefetchQuotes();
    }

    // Stop any playing audio before switching card
    if (player) {
        player.pause();
        player.currentTime = 0;
    }

    stage.classList.add('slide-out-left');

    setTimeout(() => {
        currentQuote = nextItem.quote;
        currentAudioUrl = audioCache[currentQuote] || nextItem.audio_url || "";
        quoteEl.innerText = '“' + currentQuote + '”';
        player.src = currentAudioUrl;

        // Reset button states & increment streak badge
        likeBtn.classList.remove('active-like');
        likeBtn.innerHTML = '👍';
        voiceBtn.innerHTML = '🔊';
        currentStreak += 1;
        streakBadge.innerText = '🔥 ' + currentStreak;

        stage.classList.remove('slide-out-left');
        stage.classList.add('slide-in-right');

        void stage.offsetWidth;
        stage.classList.remove('slide-in-right');
    }, 260);
}

// ON-DEMAND VOICE GENERATION (Saves 80% of Cloud TTS costs!)
async function playVoice() {
    if (isGeneratingAudio) return;

    // 1. If we already generated audio for this quote, play immediately from cache!
    if (audioCache[currentQuote]) {
        player.src = audioCache[currentQuote];
        player.play();
        return;
    }

    // 2. Otherwise, synthesize audio on-demand via /api/tts
    isGeneratingAudio = true;
    voiceBtn.innerHTML = '<span class="tiny-spinner"></span>';
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
        voiceBtn.innerHTML = '🔊';
    }
}

// HELPER: Generate 1080x1920 high-res Story card blob via html2canvas
async function generateCardBlob() {
    const exportQuote = document.getElementById('exportQuoteText');
    const exportStreak = document.getElementById('exportStreak');
    if (exportQuote) exportQuote.innerText = currentQuote;
    if (exportStreak) exportStreak.innerText = currentStreak;

    const exportEl = document.getElementById('storyExportCard');
    if (!exportEl) return null;

    const canvas = await html2canvas(exportEl, {
        scale: 2, // 1080x1920 Full HD resolution
        backgroundColor: '#090d16',
        useCORS: true
    });

    return new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), 'image/png');
    });
}

// HELPER: Trigger instant file download in browser
function triggerDownload(blob, filename) {
    const link = document.createElement('a');
    link.download = filename || `motiveate-day-${currentStreak}.png`;
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(link.href), 1500);
}

// 1-CLICK INSTANT PNG DOWNLOAD (Direct to computer / Downloads folder)
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

// Modal controls for Export & Share
function openShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.classList.add('open');
}

function closeShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.classList.remove('open');
}

// Download option inside the Share modal
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

// Copy Image directly to clipboard (for WhatsApp Web, Slack, Discord)
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

// Copy quote text to clipboard
async function copyQuoteText() {
    const btn = document.getElementById('modalCopyTextBtn');
    const titleEl = btn ? btn.querySelector('.share-title') : null;
    const descEl = btn ? btn.querySelector('.share-desc') : null;
    const iconEl = btn ? btn.querySelector('.share-icon-wrap') : null;

    try {
        const textToCopy = `“${currentQuote}” — via Motiveate AI (Day ${currentStreak})`;
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

// System share sheet (triggers Windows Share / Mobile share) with automatic download option
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

async function sendFeedback(action) {
    if (action === 'like') {
        likeBtn.classList.add('active-like');
        likeBtn.innerHTML = '❤️';
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

function toggleModal(show) {
    const modal = document.getElementById('editModal');
    if (show) modal.classList.add('open');
    else modal.classList.remove('open');
}

function showModalLoading() {
    toggleModal(false);
    loaderMsg.innerText = 'Updating your preferences & voice...';
    cardLoader.classList.add('active');
}

// Close modal if user clicks outside modal box
window.addEventListener('click', (e) => {
    if (e.target && e.target.classList && e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

// Keyboard shortcuts: Space / Right Arrow for next card, L to like, S to share modal, D to download
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

if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', () => {
        prefetchQuotes();
    });
} else {
    prefetchQuotes();
}