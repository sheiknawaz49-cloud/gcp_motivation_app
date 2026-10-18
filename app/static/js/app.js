/**
 * Daily Motivation App - Client Controller
 */
(function () {
    let currentQuote = window.__APP_DATA__ ? window.__APP_DATA__.quoteText : "";
    let currentStreak = window.__APP_DATA__ ? window.__APP_DATA__.streak : 1;
    let quoteQueue = [];
    let isFetchingBatch = false;

    // DOM Elements
    let stage, quoteEl, player, likeBtn, streakBadge, bufferStatus, cardLoader, loaderMsg, editModal;

    function initDomElements() {
        stage = document.getElementById('quoteStage');
        quoteEl = document.getElementById('quoteText');
        player = document.getElementById('voicePlayer');
        likeBtn = document.getElementById('likeBtn');
        streakBadge = document.getElementById('streakBadge');
        bufferStatus = document.getElementById('bufferStatus');
        cardLoader = document.getElementById('cardLoader');
        loaderMsg = document.getElementById('loaderMsg');
        editModal = document.getElementById('editModal');
    }

    function updateBufferBadge() {
        if (!bufferStatus) return;
        if (isFetchingBatch && quoteQueue.length === 0) {
            bufferStatus.innerHTML = '<span class="tiny-spinner"></span> Preloading...';
        } else if (quoteQueue.length > 0) {
            bufferStatus.innerHTML = '⚡ ' + quoteQueue.length + ' ready';
        } else {
            bufferStatus.innerHTML = '✨ Ready';
        }
    }

    // Prefetch quotes and audio in the background for instant transitions
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
                    // Preload the next audio file into browser cache
                    if (quoteQueue[0] && quoteQueue[0].audio_url) {
                        const preloadAudio = new Audio(quoteQueue[0].audio_url);
                        preloadAudio.preload = 'auto';
                    }
                }
            }
        } catch (err) {
            console.error('Prefetch error:', err);
        } finally {
            isFetchingBatch = false;
            updateBufferBadge();
        }
    }

    // Smoothly animate and swap to next card
    async function showNextCard() {
        if (quoteQueue.length === 0) {
            if (loaderMsg) loaderMsg.innerText = 'Crafting fresh personalized quotes...';
            if (cardLoader) cardLoader.classList.add('active');
            await prefetchQuotes();
            if (cardLoader) cardLoader.classList.remove('active');
        }

        const nextItem = quoteQueue.shift();
        if (!nextItem) return;

        updateBufferBadge();

        // Trigger background refill whenever queue drops to 1 card left
        if (quoteQueue.length <= 1) {
            prefetchQuotes();
        }

        if (!stage || !quoteEl) return;

        // 1. Slide current quote out to the left
        stage.classList.add('slide-out-left');

        setTimeout(() => {
            // 2. Swap text & audio and jump stage to the right (invisible)
            currentQuote = nextItem.quote;
            quoteEl.innerText = '“' + currentQuote + '”';
            if (player && nextItem.audio_url) {
                player.src = nextItem.audio_url;
            }

            // Reset Like button state & increment streak badge
            if (likeBtn) {
                likeBtn.classList.remove('active-like');
                likeBtn.innerHTML = '👍 <span>Like</span>';
            }
            if (streakBadge) {
                currentStreak += 1;
                streakBadge.innerText = '🔥 ' + currentStreak;
            }

            stage.classList.remove('slide-out-left');
            stage.classList.add('slide-in-right');

            // 3. Force browser reflow, then smoothly glide into center
            void stage.offsetWidth;
            stage.classList.remove('slide-in-right');
        }, 260);
    }

    async function sendFeedback(action) {
        if (action === 'like' && likeBtn) {
            likeBtn.classList.add('active-like');
            likeBtn.innerHTML = '❤️ <span>Saved</span>';
        }

        try {
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: action, quote: currentQuote })
            });
        } catch (err) {
            console.error('Feedback error:', err);
        }

        if (action === 'dislike') {
            showNextCard();
        }
    }

    function playVoice() {
        if (player && player.src) {
            player.play().catch(e => console.warn('Audio play prevented:', e));
        }
    }

    function toggleModal(show) {
        if (!editModal) return;
        if (show) {
            editModal.classList.add('open');
        } else {
            editModal.classList.remove('open');
        }
    }

    function showModalLoading() {
        toggleModal(false);
        if (loaderMsg) loaderMsg.innerText = 'Updating your preferences & voice...';
        if (cardLoader) cardLoader.classList.add('active');
    }

    // Expose functions globally for onclick attributes
    window.showNextCard = showNextCard;
    window.sendFeedback = sendFeedback;
    window.playVoice = playVoice;
    window.toggleModal = toggleModal;
    window.showModalLoading = showModalLoading;

    // Initialize once DOM is ready
    window.addEventListener('DOMContentLoaded', () => {
        initDomElements();

        // Close modal when clicking on backdrop
        if (editModal) {
            editModal.addEventListener('click', (e) => {
                if (e.target === editModal) {
                    toggleModal(false);
                }
            });
        }

        // Keyboard navigation (Space or ArrowRight for next card, L for like)
        window.addEventListener('keydown', (e) => {
            if (editModal && editModal.classList.contains('open')) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            if (e.code === 'Space' || e.code === 'ArrowRight') {
                e.preventDefault();
                showNextCard();
            } else if (e.code === 'KeyL') {
                e.preventDefault();
                sendFeedback('like');
            }
        });

        // Start prefetching 3 upcoming cards immediately
        prefetchQuotes();
    });
})();
