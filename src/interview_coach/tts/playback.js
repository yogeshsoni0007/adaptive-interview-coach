const cleanups = new WeakMap();

export default function ({ data, parentElement }) {
    cleanups.get(parentElement)?.();
    const get = (id) => parentElement.querySelector(`#${id}`);
    const readAll = get("read-all");
    const stopButton = get("stop");
    const replay = get("replay");
    const browserButton = get("browser");
    const selector = get("question-number");
    const voiceSelect = get("voice-select");
    const status = get("status");
    const synth = window.speechSynthesis;
    const browserSupported = Boolean(synth && window.SpeechSynthesisUtterance);
    let runId = 0;
    let currentAudio = null;
    let currentUtterance = null;

    selector.replaceChildren();
    data.questions.forEach((text, i) => {
        const option = document.createElement("option");
        option.value = String(i);
        option.textContent = `Question ${i + 1}`;
        selector.appendChild(option);
    });

    function populateVoices() {
        const previous = voiceSelect.value;
        voiceSelect.replaceChildren();
        const language = data.language.split("-")[0].toLowerCase();
        const voices = browserSupported ? synth.getVoices().filter(
            voice => voice.lang.toLowerCase().startsWith(language)
        ) : [];
        const choices = voices.length ? voices : [{ name: "", lang: data.language }];
        choices.forEach(voice => {
            const option = document.createElement("option");
            option.value = voice.name;
            option.textContent = voice.name ? `${voice.name} (${voice.lang})` : "Default voice";
            voiceSelect.appendChild(option);
        });
        if (voices.some(voice => voice.name === previous)) voiceSelect.value = previous;
    }
    populateVoices();
    readAll.disabled = replay.disabled = false;
    status.textContent = "Ready.";
    voiceSelect.disabled = !browserSupported;
    browserButton.disabled = !browserSupported;
    if (browserSupported) synth.addEventListener("voiceschanged", populateVoices);
    if (!browserSupported && data.audio.every(item => !item)) {
        status.textContent = "Speech unavailable in this browser. Please read the question on screen.";
        readAll.disabled = replay.disabled = true;
    }

    function releaseAudio() {
        if (currentAudio) {
            currentAudio.onended = null;
            currentAudio.onerror = null;
            currentAudio.pause();
            currentAudio.removeAttribute("src");
            currentAudio.load();
            currentAudio = null;
        }
    }

    function stop() {
        runId += 1;
        releaseAudio();
        if (browserSupported) synth.cancel();
        currentUtterance = null;
        status.textContent = "Stopped.";
    }

    function play(indices, forceBrowser = false) {
        stop();
        const thisRun = runId;
        status.textContent = "Starting...";

        function next(position) {
            if (thisRun !== runId) return;
            releaseAudio();
            currentUtterance = null;
            if (position >= indices.length) {
                status.textContent = "Finished.";
                return;
            }
            const index = indices[position];
            const describe = () => {
                status.textContent = `Reading question ${index + 1} of ${data.questions.length}.`;
            };
            let browserStarted = false;
            function speakBrowser() {
                if (thisRun !== runId || browserStarted) return;
                browserStarted = true;
                releaseAudio();
                if (!browserSupported) {
                    status.textContent = "Audio unavailable. Please read the question on screen.";
                    return;
                }
                try {
                    synth.resume();
                    const utterance = new window.SpeechSynthesisUtterance(data.questions[index]);
                    currentUtterance = utterance;
                    const voice = synth.getVoices().find(v => v.name === voiceSelect.value);
                    if (voice) utterance.voice = voice;
                    utterance.lang = voice?.lang || data.language;
                    utterance.rate = data.speed;
                    utterance.onstart = () => { if (thisRun === runId) describe(); };
                    utterance.onend = () => { if (thisRun === runId) next(position + 1); };
                    utterance.onerror = () => {
                        if (thisRun === runId) {
                            status.textContent = "Speech could not finish. Try Replay selected.";
                        }
                    };
                    synth.speak(utterance);
                } catch {
                    status.textContent = "Speech could not start. Try another browser.";
                }
            }
            if (forceBrowser || !data.audio[index]) {
                speakBrowser();
                return;
            }
            try {
                const audio = new Audio(data.audio[index]);
                currentAudio = audio;
                audio.onended = () => { if (thisRun === runId) next(position + 1); };
                audio.onerror = speakBrowser;
                describe();
                const playing = audio.play();
                playing?.catch(error => {
                    if (thisRun !== runId) return;
                    if (error.name === "NotAllowedError") {
                        releaseAudio();
                        status.textContent = "Playback blocked. Click Replay selected or Use browser voice.";
                    } else {
                        speakBrowser();
                    }
                });
            } catch {
                speakBrowser();
            }
        }
        next(0);
    }

    readAll.onclick = () => play(data.questions.map((_, index) => index));
    stopButton.onclick = stop;
    replay.onclick = () => play([Number(selector.value)]);
    browserButton.onclick = () => play([Number(selector.value)], true);
    window.addEventListener("pagehide", stop);

    function cleanup() {
        if (cleanups.get(parentElement) !== cleanup) return;
        stop();
        readAll.onclick = stopButton.onclick = replay.onclick = browserButton.onclick = null;
        if (browserSupported) synth.removeEventListener("voiceschanged", populateVoices);
        window.removeEventListener("pagehide", stop);
        cleanups.delete(parentElement);
    }
    cleanups.set(parentElement, cleanup);
    return cleanup;
}
