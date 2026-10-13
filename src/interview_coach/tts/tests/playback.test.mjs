import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(new URL("../playback.js", import.meta.url), "utf8");
const { default: render } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

function fixture({ browser = true, reject = null, audio = ["data:audio/mpeg;base64,AAA", null] } = {}) {
    const elements = Object.fromEntries(
        ["read-all", "stop", "replay", "browser", "question-number", "voice-select", "status"].map(id => [id, {
            value: "0", disabled: false, textContent: "", children: [],
            replaceChildren() { this.children = []; this.value = ""; },
            appendChild(child) { if (!this.children.length) this.value = child.value; this.children.push(child); },
        }])
    );
    const audios = [], spoken = [], events = new Map(), voiceEvents = new Map();
    globalThis.document = { createElement: () => ({ value: "", textContent: "" }) };
    globalThis.window = {
        addEventListener: (name, fn) => events.set(name, fn),
        removeEventListener: name => events.delete(name),
        SpeechSynthesisUtterance: browser ? class { constructor(text) { this.text = text; } } : undefined,
        speechSynthesis: browser ? {
            getVoices: () => [{ name: "English", lang: "en-US" }],
            cancel() {}, resume() {},
            speak(utterance) { spoken.push(utterance); utterance.onstart?.(); },
            addEventListener: (name, fn) => voiceEvents.set(name, fn),
            removeEventListener: name => voiceEvents.delete(name),
        } : undefined,
    };
    globalThis.Audio = class {
        constructor(src) { this.src = src; audios.push(this); }
        play() { return reject ? Promise.reject({ name: reject }) : Promise.resolve(); }
        pause() { this.paused = true; }
        removeAttribute() { this.src = ""; }
        load() {}
    };
    const parentElement = { querySelector: selector => elements[selector.slice(1)] };
    const data = { questions: ["First?", "Second?"], audio, language: "en-US", speed: 0.92 };
    const cleanup = render({ data, parentElement });
    return { elements, audios, spoken, events, voiceEvents, cleanup, data, parentElement };
}

test("Read all sequences generated audio then browser audio; Replay uses same audio", () => {
    const f = fixture();
    f.elements["read-all"].onclick();
    assert.equal(f.audios.length, 1);
    f.audios[0].onended();
    assert.equal(f.spoken[0].text, "Second?");
    f.spoken[0].onend();
    assert.equal(f.elements.status.textContent, "Finished.");
    f.elements.replay.onclick();
    assert.equal(f.audios.length, 2);
    f.cleanup();
});

test("Stop cancels the queue and ignores stale audio completion", () => {
    const f = fixture();
    f.elements["read-all"].onclick();
    const lateEnd = f.audios[0].onended;
    f.elements.stop.onclick();
    lateEnd();
    assert.equal(f.spoken.length, 0);
    assert.equal(f.audios[0].paused, true);
    assert.equal(f.elements.status.textContent, "Stopped.");
    f.cleanup();
});

test("Decode error falls back to browser once even if both error paths fire", async () => {
    const f = fixture({ reject: "NotSupportedError" });
    f.elements.replay.onclick();
    f.audios[0].onerror();
    await Promise.resolve();
    assert.equal(f.spoken.length, 1);
    assert.equal(f.spoken[0].text, "First?");
    f.cleanup();
});

test("Autoplay restriction leaves a usable manual browser fallback", async () => {
    const f = fixture({ reject: "NotAllowedError" });
    f.elements.replay.onclick();
    await Promise.resolve();
    assert.match(f.elements.status.textContent, /Playback blocked/);
    f.elements.browser.onclick();
    assert.equal(f.spoken[0].text, "First?");
    f.cleanup();
});

test("Generated audio works when speechSynthesis is unavailable", () => {
    const f = fixture({ browser: false });
    assert.equal(f.elements.replay.disabled, false);
    assert.equal(f.elements.browser.disabled, true);
    f.elements.replay.onclick();
    assert.equal(f.audios.length, 1);
    f.cleanup();
});

test("Browser-only playback supports Stop, selected question, and stale speech events", () => {
    const f = fixture({ audio: [null, null] });
    f.elements["read-all"].onclick();
    const lateEnd = f.spoken[0].onend;
    f.elements.stop.onclick();
    lateEnd();
    assert.equal(f.spoken.length, 1);
    f.elements["question-number"].value = "1";
    f.elements.replay.onclick();
    assert.equal(f.spoken[1].text, "Second?");
    assert.equal(f.spoken[1].rate, 0.92);
    f.cleanup();
});

test("Rerender cleans up audio and handlers; pagehide stops playback", () => {
    const f = fixture();
    f.elements.replay.onclick();
    const cleanup = render({ data: f.data, parentElement: f.parentElement });
    assert.equal(f.audios[0].paused, true);
    f.elements.replay.onclick();
    f.events.get("pagehide")();
    assert.equal(f.audios[1].paused, true);
    cleanup();
    assert.equal(f.events.size, 0);
    assert.equal(f.voiceEvents.size, 0);
    assert.equal(f.elements.replay.onclick, null);
});

test("Unavailable speech leaves text guidance; rerender re-enables generated audio", () => {
    const f = fixture({ browser: false, audio: [null, null] });
    assert.equal(f.elements.replay.disabled, true);
    assert.match(f.elements.status.textContent, /read the question/);
    const cleanup = render({ data: { ...f.data, audio: ["data:audio/mpeg;base64,AAA", null] }, parentElement: f.parentElement });
    assert.equal(f.elements.replay.disabled, false);
    cleanup();
});
