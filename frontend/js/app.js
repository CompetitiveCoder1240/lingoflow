/**
 * LingoFlow – Main Application Controller
 * Orchestrates the WebSocket connection, audio recorder, audio player,
 * and all UI updates for the real-time voice conversation experience.
 */

(function () {
    'use strict';

    // ── DOM Elements ────────────────────────────────────
    const voiceOrb = document.getElementById('voiceOrb');
    const orbStatus = document.getElementById('orbStatus');
    const btnMic = document.getElementById('btnMic');
    const btnReset = document.getElementById('btnReset');
    const voiceSelect = document.getElementById('voiceSelect');
    const transcriptArea = document.getElementById('transcriptArea');
    const transcriptPlaceholder = document.getElementById('transcriptPlaceholder');
    const feedbackCard = document.getElementById('feedbackCard');
    const feedbackBody = document.getElementById('feedbackBody');
    const btnCloseFeedback = document.getElementById('btnCloseFeedback');

    // ── State ───────────────────────────────────────────
    let ws = null;
    let recorder = null;
    let player = null;
    let isSessionActive = false;
    let currentState = 'idle'; // idle, listening, thinking, speaking

    // ── Initialize ──────────────────────────────────────

    function init() {
        player = new AudioPlayer();

        player.onPlaybackComplete = () => {
            // After AI finishes speaking, go back to listening if session active
            if (isSessionActive && currentState === 'speaking') {
                setOrbState('listening');
            }
        };

        // Event listeners
        btnMic.addEventListener('click', toggleSession);
        btnReset.addEventListener('click', resetConversation);
        voiceSelect.addEventListener('change', changeVoice);
        btnCloseFeedback.addEventListener('click', () => {
            feedbackCard.classList.add('hidden');
        });
    }

    // ── WebSocket Connection ────────────────────────────

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/conversation`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[WS] Connected.');
        };

        ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // Binary frame: MP3 audio chunk
                event.data.arrayBuffer().then((buffer) => {
                    player.enqueue(buffer);
                });
            } else {
                // Text frame: JSON message
                handleServerMessage(JSON.parse(event.data));
            }
        };

        ws.onerror = (error) => {
            console.error('[WS] Error:', error);
            setOrbState('idle');
            setStatus('Connection error. Please try again.');
        };

        ws.onclose = () => {
            console.log('[WS] Disconnected.');
            if (isSessionActive) {
                setStatus('Connection lost. Click mic to reconnect.');
                stopSession();
            }
        };
    }

    // ── Handle Server Messages ──────────────────────────

    function handleServerMessage(msg) {
        switch (msg.type) {
            case 'state':
                setOrbState(msg.state);
                break;

            case 'transcript':
                if (msg.is_final) {
                    addTranscriptMessage('You', msg.text, 'user');
                }
                break;

            case 'ai_text':
                addTranscriptMessage('LingoFlow', msg.text, 'ai');
                break;

            case 'feedback':
                displayFeedback(msg);
                break;

            case 'error':
                console.error('[Server Error]', msg.message);
                setStatus(`Error: ${msg.message}`);
                break;

            default:
                console.log('[WS] Unknown message type:', msg.type);
        }
    }

    // ── Session Control ─────────────────────────────────

    async function toggleSession() {
        if (isSessionActive) {
            stopSession();
        } else {
            await startSession();
        }
    }

    async function startSession() {
        try {
            connectWebSocket();

            recorder = new AudioRecorder((pcmBuffer) => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(pcmBuffer);
                }
            });

            await recorder.start();

            isSessionActive = true;
            btnMic.classList.add('active');
            setOrbState('listening');
            setStatus('Listening... speak naturally!');

            // Clear placeholder
            if (transcriptPlaceholder) {
                transcriptPlaceholder.style.display = 'none';
            }
        } catch (error) {
            setStatus('Microphone access required. Please allow and retry.');
            console.error('[Session] Start failed:', error);
        }
    }

    function stopSession() {
        isSessionActive = false;

        if (recorder) {
            recorder.stop();
            recorder = null;
        }

        if (player) {
            player.stop();
        }

        if (ws) {
            ws.close();
            ws = null;
        }

        btnMic.classList.remove('active');
        setOrbState('idle');
        setStatus('Click the microphone to start');
    }

    function resetConversation() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'control', action: 'reset' }));
        }

        // Clear transcript
        transcriptArea.innerHTML = '';
        if (transcriptPlaceholder) {
            const placeholder = document.createElement('div');
            placeholder.className = 'transcript-placeholder';
            placeholder.id = 'transcriptPlaceholder';
            placeholder.textContent = 'Your conversation will appear here...';
            transcriptArea.appendChild(placeholder);
        }

        // Hide feedback
        feedbackCard.classList.add('hidden');
        setStatus('Conversation reset. Ready to start fresh!');
    }

    function changeVoice() {
        const voice = voiceSelect.value;
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'config', voice: voice }));
        }
    }

    // ── Barge-in: User speaks while AI is talking ────────

    // Detect barge-in: if the user starts recording while AI is speaking
    // Note: This is handled by the backend via VAD + Deepgram utterance events.
    // On the client side, when we detect the user's mic is active and AI is
    // speaking, we send a cancel signal and stop playback.

    // ── UI Updates ──────────────────────────────────────

    function setOrbState(state) {
        currentState = state;
        voiceOrb.className = 'voice-orb';

        switch (state) {
            case 'listening':
                voiceOrb.classList.add('listening');
                setStatus('Listening...');
                break;
            case 'thinking':
                voiceOrb.classList.add('thinking');
                setStatus('Thinking...');
                break;
            case 'speaking':
                voiceOrb.classList.add('speaking');
                setStatus('Speaking...');
                break;
            case 'idle':
            default:
                if (isSessionActive) {
                    setStatus('Ready – speak anytime!');
                } else {
                    setStatus('Click the microphone to start');
                }
                break;
        }
    }

    function setStatus(text) {
        orbStatus.textContent = text;
    }

    function addTranscriptMessage(label, text, type) {
        // Remove placeholder if present
        const placeholder = document.getElementById('transcriptPlaceholder');
        if (placeholder) placeholder.remove();

        const msgDiv = document.createElement('div');
        msgDiv.className = `transcript-msg ${type}`;

        const labelDiv = document.createElement('div');
        labelDiv.className = 'label';
        labelDiv.textContent = label;

        const textDiv = document.createElement('div');
        textDiv.textContent = text;

        msgDiv.appendChild(labelDiv);
        msgDiv.appendChild(textDiv);
        transcriptArea.appendChild(msgDiv);

        // Auto-scroll to bottom
        transcriptArea.scrollTop = transcriptArea.scrollHeight;
    }

    function displayFeedback(feedback) {
        feedbackBody.innerHTML = '';

        // Corrections
        if (feedback.has_corrections && feedback.corrections && feedback.corrections.length > 0) {
            feedback.corrections.forEach((c) => {
                const item = document.createElement('div');
                item.className = 'correction-item';
                item.innerHTML = `
                    <span class="original">${escapeHtml(c.original)}</span>
                    → <span class="corrected">${escapeHtml(c.corrected)}</span>
                    <div class="rule">${escapeHtml(c.rule || '')}</div>
                `;
                feedbackBody.appendChild(item);
            });
        }

        // Natural alternative
        if (feedback.natural_alternative) {
            const tip = document.createElement('div');
            tip.className = 'tip-item';
            tip.innerHTML = `<strong>🗣️ More natural:</strong> ${escapeHtml(feedback.natural_alternative)}`;
            feedbackBody.appendChild(tip);
        }

        // Vocabulary tip
        if (feedback.vocabulary_tip) {
            const tip = document.createElement('div');
            tip.className = 'tip-item';
            tip.innerHTML = `<strong>📚 Vocab tip:</strong> ${escapeHtml(feedback.vocabulary_tip)}`;
            feedbackBody.appendChild(tip);
        }

        // Show card if there's anything to display
        if (feedbackBody.children.length > 0) {
            feedbackCard.classList.remove('hidden');
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // ── Boot ────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', init);
})();
