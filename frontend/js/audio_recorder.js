/**
 * LingoFlow – Audio Recorder Module
 * Captures microphone audio as raw PCM (16kHz, mono, 16-bit)
 * and streams it via a callback for WebSocket transmission.
 */

class AudioRecorder {
    /**
     * @param {Function} onAudioData - Callback receiving ArrayBuffer of PCM audio data.
     * @param {number} sampleRate - Target sample rate (default: 16000 for Deepgram).
     */
    constructor(onAudioData, sampleRate = 16000) {
        this.onAudioData = onAudioData;
        this.targetSampleRate = sampleRate;
        this.stream = null;
        this.audioContext = null;
        this.processor = null;
        this.source = null;
        this.isRecording = false;
    }

    /**
     * Request microphone access and begin recording.
     */
    async start() {
        if (this.isRecording) return;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: this.targetSampleRate,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            this.audioContext = new AudioContext({
                sampleRate: this.targetSampleRate,
            });

            this.source = this.audioContext.createMediaStreamSource(this.stream);

            // Use ScriptProcessorNode (widely supported) for raw PCM access.
            // Buffer size of 4096 balances latency and CPU usage.
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.processor.onaudioprocess = (event) => {
                if (!this.isRecording) return;

                const inputData = event.inputBuffer.getChannelData(0);
                // Convert Float32 [-1, 1] to Int16 PCM
                const pcmData = this._float32ToInt16(inputData);
                this.onAudioData(pcmData.buffer);
            };

            this.source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            this.isRecording = true;

            console.log('[AudioRecorder] Recording started.');
        } catch (error) {
            console.error('[AudioRecorder] Microphone access denied:', error);
            throw error;
        }
    }

    /**
     * Stop recording and release microphone.
     */
    stop() {
        this.isRecording = false;

        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        if (this.source) {
            this.source.disconnect();
            this.source = null;
        }
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }

        console.log('[AudioRecorder] Recording stopped.');
    }

    /**
     * Convert Float32Array audio samples to Int16Array (PCM 16-bit).
     * @param {Float32Array} float32Array
     * @returns {Int16Array}
     */
    _float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        return int16Array;
    }
}

// Export for use in app.js
window.AudioRecorder = AudioRecorder;
