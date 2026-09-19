document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');
    const btnMic = document.getElementById('btn-mic');
    const btnLocation = document.getElementById('btn-location');
    const messagesContainer = document.getElementById('messages-container');
    const typingIndicator = document.getElementById('typing-indicator');
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const ttsPlayer = document.getElementById('tts-player');

    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        body.classList.toggle('light-mode');
        if (body.classList.contains('light-mode')) {
            themeToggle.classList.replace('fa-moon', 'fa-sun');
        } else {
            themeToggle.classList.replace('fa-sun', 'fa-moon');
        }
    });

    // Input listening
    chatInput.addEventListener('input', () => {
        if (chatInput.value.trim().length > 0) {
            btnSend.classList.remove('hidden');
            btnMic.classList.add('hidden');
        } else {
            btnSend.classList.add('hidden');
            btnMic.classList.remove('hidden');
        }
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendTextMessage();
        }
    });

    btnSend.addEventListener('click', sendTextMessage);

    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = text
            // Escape HTML entities to prevent XSS
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            // Bold
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Bullet points
            .replace(/^[•\-\*]\s+(.*)$/gm, '<li>$1</li>')
            // Numbered lists
            .replace(/^(\d+)\.\s+(.*)$/gm, '<li><strong>$1.</strong> $2</li>')
            // Line breaks
            .replace(/\n/g, '<br>');
        return formatted;
    }

    function addMessage(text, type, audioB64 = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${type}`;
        
        msgDiv.innerHTML = formatMarkdown(text);

        if (audioB64) {
            const btnPlay = document.createElement('button');
            btnPlay.innerHTML = '<i class="fa-solid fa-play"></i> Play Voice';
            btnPlay.style.marginTop = '10px';
            btnPlay.style.background = 'var(--bg-header)';
            btnPlay.style.border = 'none';
            btnPlay.style.padding = '8px 14px';
            btnPlay.style.color = 'var(--text-primary)';
            btnPlay.style.borderRadius = '20px';
            btnPlay.style.cursor = 'pointer';
            btnPlay.style.display = 'inline-flex';
            btnPlay.style.alignItems = 'center';
            btnPlay.style.gap = '8px';
            btnPlay.style.fontSize = '0.85rem';
            
            btnPlay.onclick = () => {
                // Determine audio format (OGG if starts with T2dnUw, otherwise MP3)
                const mime = audioB64.startsWith('T2dnUw') ? 'audio/ogg' : 'audio/mp3';
                ttsPlayer.src = `data:${mime};base64,${audioB64}`;
                ttsPlayer.play();
                btnPlay.innerHTML = '<i class="fa-solid fa-volume-high"></i> Playing...';
                ttsPlayer.onended = () => {
                    btnPlay.innerHTML = '<i class="fa-solid fa-play"></i> Play Voice';
                };
            };
            msgDiv.appendChild(btnPlay);
        }

        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendRequest(payload) {
        typingIndicator.classList.remove('hidden');
        scrollToBottom();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            typingIndicator.classList.add('hidden');

            if (data.error) {
                addMessage(`Error: ${data.error}`, 'system');
                return;
            }

            if (data.transcribed_text) {
                addMessage(`*(Transcribed): ${data.transcribed_text}*`, 'outgoing');
            }

            addMessage(data.text, 'incoming', data.audio_b64);
        } catch (error) {
            typingIndicator.classList.add('hidden');
            addMessage(`Failed to reach server: ${error.message}`, 'system');
        }
    }

    function sendTextMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        
        addMessage(text, 'outgoing');
        chatInput.value = '';
        chatInput.dispatchEvent(new Event('input')); // reset icons

        sendRequest({ type: 'text', body: text });
    }

    // --- Geolocation (WhatsApp native GPS simulator) ---
    btnLocation.addEventListener('click', () => {
        if (!navigator.geolocation) {
            addMessage("Geolocation is not supported by your browser.", 'system');
            return;
        }

        addMessage("Fetching your current location...", 'system');
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                addMessage(`📍 Location Shared\nLat: ${lat.toFixed(4)}, Lon: ${lng.toFixed(4)}`, 'outgoing');
                sendRequest({ type: 'location', lat: lat, lng: lng });
            },
            (error) => {
                addMessage(`Unable to retrieve your location: ${error.message}`, 'system');
            }
        );
    });

    // --- Audio Recording (Voice Simulator) ---
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    btnMic.addEventListener('mousedown', startRecording);
    btnMic.addEventListener('mouseup', stopRecording);
    btnMic.addEventListener('touchstart', startRecording);
    btnMic.addEventListener('touchend', stopRecording);

    async function startRecording(e) {
        e.preventDefault();
        if (isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = [];
                
                // Convert blob to base64
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = () => {
                    const base64data = reader.result.split(',')[1];
                    addMessage("🎙️ Sent Voice Message", 'outgoing');
                    sendRequest({ type: 'audio', audio_b64: base64data });
                };
            };

            mediaRecorder.start();
            isRecording = true;
            btnMic.classList.add('recording');
        } catch (err) {
            addMessage(`Microphone access denied or unavailable: ${err.message}`, 'system');
        }
    }

    function stopRecording(e) {
        e.preventDefault();
        if (!isRecording || !mediaRecorder) return;
        
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop()); // release mic
        isRecording = false;
        btnMic.classList.remove('recording');
    }
});
