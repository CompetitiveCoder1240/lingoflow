/**
 * LingoFlow – Audio Player Module
 * Manages a queue of MP3 audio chunks for seamless, gapless playback.
 * Supports barge-in (immediate stop + queue flush).
 */

class AudioPlayer {
    constructor() {
        /** @type {ArrayBuffer[]} */
        this.queue = [];
        this.isPlaying = false;
        this.currentAudio = null;

        /** @type {Function|null} Callback when playback of all queued audio completes. */
        this.onPlaybackComplete = null;

        /** @type {Function|null} Callback when a chunk starts playing. */
        this.onChunkStart = null;
    }

    /**
     * Add an MP3 audio chunk (as ArrayBuffer) to the playback queue.
     * Automatically begins playback if not already playing.
     * @param {ArrayBuffer} audioBuffer - MP3 audio data.
     */
    enqueue(audioBuffer) {
        this.queue.push(audioBuffer);
        if (!this.isPlaying) {
            this._playNext();
        }
    }

    /**
     * Immediately stop playback and clear the queue (barge-in).
     */
    stop() {
        this.queue = [];
        this.isPlaying = false;

        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.removeAttribute('src');
            this.currentAudio.load();
            this.currentAudio = null;
        }

        console.log('[AudioPlayer] Playback stopped and queue flushed.');
    }

    /**
     * Play the next chunk in the queue.
     * @private
     */
    async _playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            if (this.onPlaybackComplete) {
                this.onPlaybackComplete();
            }
            return;
        }

        this.isPlaying = true;
        const buffer = this.queue.shift();

        try {
            const blob = new Blob([buffer], { type: 'audio/mpeg' });
            const url = URL.createObjectURL(blob);

            this.currentAudio = new Audio(url);

            if (this.onChunkStart) {
                this.onChunkStart();
            }

            this.currentAudio.onended = () => {
                URL.revokeObjectURL(url);
                this.currentAudio = null;
                this._playNext();
            };

            this.currentAudio.onerror = (e) => {
                console.error('[AudioPlayer] Error playing audio chunk:', e);
                URL.revokeObjectURL(url);
                this.currentAudio = null;
                this._playNext();
            };

            await this.currentAudio.play();
        } catch (error) {
            console.error('[AudioPlayer] Playback error:', error);
            this._playNext();
        }
    }

    /**
     * Whether audio is currently playing or queued.
     * @returns {boolean}
     */
    get isBusy() {
        return this.isPlaying || this.queue.length > 0;
    }
}

// Export for use in app.js
window.AudioPlayer = AudioPlayer;
