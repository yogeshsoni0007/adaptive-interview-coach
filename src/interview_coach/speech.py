import streamlit as st


_SPEECH = st.components.v2.component(
    "interview_question_speech",
    html="""
<div>
    <button id="read-all" type="button">Read all</button>
    <button id="stop" type="button">Stop</button>

    <label>
        Voice
        <select id="voice-select"></select>
    </label>

    <label>
        Question
        <select id="question-number"></select>
    </label>

    <button id="replay" type="button">Replay selected</button>

    <p id="status" role="status" aria-live="polite">
        Ready.
    </p>
</div>
""",
    js="""
const cleanups = new WeakMap();

export default function ({ data, parentElement }) {
    const previousCleanup = cleanups.get(parentElement);

    if (previousCleanup) {
        previousCleanup();
    }

    const questions = data.questions;

    const readAll = parentElement.querySelector('[id="read-all"]');
    const stopButton = parentElement.querySelector('[id="stop"]');
    const selector = parentElement.querySelector('[id="question-number"]');
    const replay = parentElement.querySelector('[id="replay"]');
    const status = parentElement.querySelector('[id="status"]');
    const voiceSelect = parentElement.querySelector('[id="voice-select"]');

    if (
        !("speechSynthesis" in window) ||
        !("SpeechSynthesisUtterance" in window)
    ) {
        status.textContent =
            "Speech is not supported in this browser.";

        readAll.disabled = true;
        stopButton.disabled = true;
        selector.disabled = true;
        replay.disabled = true;

        return;
    }

    const synth = window.speechSynthesis;

    let runId = 0;
    let utterances = [];

    function populateVoices() {
        const voices = synth.getVoices();

        voiceSelect.replaceChildren();

        const englishVoices = voices.filter((voice) =>
            voice.lang.toLowerCase().startsWith("en")
        );

        englishVoices.forEach((voice) => {
            const option = document.createElement("option");

            option.value = voice.name;
            option.textContent = `${voice.name} (${voice.lang})`;

            voiceSelect.appendChild(option);
        });

        if (englishVoices.length === 0) {
            const option = document.createElement("option");

            option.value = "";
            option.textContent = "Default browser voice";

            voiceSelect.appendChild(option);
        }
    }

    populateVoices();
    synth.addEventListener("voiceschanged", populateVoices);

    selector.replaceChildren();

    questions.forEach((question, index) => {
        const option = document.createElement("option");

        option.value = String(index);
        option.textContent = `Question ${index + 1}`;

        selector.appendChild(option);
    });

    function stop() {
        runId += 1;

        synth.cancel();
        utterances = [];

        status.textContent = "Stopped.";
    }

    function play(indices) {
        stop();

        const currentRun = runId;

        status.textContent = "Starting...";

        utterances = indices.map((index, position) => {
            const utterance = new SpeechSynthesisUtterance(
                questions[index]
            );

            const selectedVoice = synth
                .getVoices()
                .find((voice) => voice.name === voiceSelect.value);

            if (selectedVoice) {
                utterance.voice = selectedVoice;
                utterance.lang = selectedVoice.lang;
            } else {
                utterance.lang = "en-US";
            }

            utterance.rate = 0.92;
            utterance.pitch = 1;

            utterance.onstart = () => {
                if (currentRun !== runId) {
                    return;
                }

                status.textContent =
                    `Reading question ${index + 1} of ${questions.length}.`;
            };

            utterance.onend = () => {
                if (currentRun !== runId) {
                    return;
                }

                if (position === indices.length - 1) {
                    status.textContent = "Finished.";
                    utterances = [];
                }
            };

            utterance.onerror = (event) => {
                if (currentRun !== runId) {
                    return;
                }

                stop();
                status.textContent = `Speech error: ${event.error}`;
            };

            return utterance;
        });

        utterances.forEach((utterance) => {
            synth.speak(utterance);
        });
    }

    readAll.onclick = () => {
        const allQuestionIndexes = questions.map(
            (_, index) => index
        );

        play(allQuestionIndexes);
    };

    stopButton.onclick = stop;

    replay.onclick = () => {
        const selectedIndex = Number(selector.value);

        play([selectedIndex]);
    };

    window.addEventListener("pagehide", stop);

    function cleanup() {
        stop();

        readAll.onclick = null;
        stopButton.onclick = null;
        replay.onclick = null;

        synth.removeEventListener(
            "voiceschanged",
            populateVoices
        );

        window.removeEventListener("pagehide", stop);

        cleanups.delete(parentElement);
    }

    cleanups.set(parentElement, cleanup);

    return cleanup;
}
""",
)


def render_question_speech(questions: list[str]) -> None:
    """Render browser controls for speaking interview questions."""

    if not questions:
        return

    _SPEECH(
        data={"questions": questions},
        key="interview_speech_player",
        height="content",
    )
