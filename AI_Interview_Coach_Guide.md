# AI Interview Coach - Product and Build Guide

Status: POC in progress. Phase checklist items below remain open until all their requirements are verified.
Last updated: 2026-10-03.

This is the source of truth for the POC, MVP, and MVP+1 scope. Coding agents should read it before making product changes and update the task checkboxes only after implementation and verification. Follow `AGENTS.md` and the user's current instructions for workflow and permissions; this guide does not override them.

## Verified implementation checkpoint — 2026-10-03

The voice answer loop now saves audio, transcribes, analyzes, and shows a targeted
probe/clarification/challenge or advances. Follow-ups have fresh recording widgets and
separate audio/metadata entries. Code enforces the two-follow-up limit. Failures keep the
question active and preserve completed work for retry.

Streamlit submission tests cover visible follow-ups, advance/completion, failed transcription,
provider failures, retry, recording preservation, and the follow-up limit. A separate local
integration check used synthetic speech, real cached MLX Whisper, and real Qwen3:4b:
the answer was transcribed, classified as `probe`, and its generated follow-up rendered in
the app test. Physical microphone capture and browser speech playback remain manual checks.
See README for commands. This checkpoint does not complete the broader POC: blueprint,
video, final coaching report, and multi-profile validation remain open.

## Product goal

Build an adaptive interview coach that uses the candidate's actual job description (JD) and resume. The interview should ask, listen, understand, probe, challenge, evaluate, and coach. The candidate can choose voice-only or video. The system should respond to answer quality, not follow a fixed question list.

## Decisions already made

| Decision | Requirement |
| --- | --- |
| Development and testing | On the owner's laptop. No hosted service is needed for POC or MVP. Deployment is considered after audience validation. |
| GitHub distribution | MVP must be downloadable and runnable on another laptop using documented setup. Target macOS, Windows, and Linux. |
| AI credentials in POC/MVP | The person running the app supplies provider, model, endpoint, and key in local configuration such as `.env`. Candidates do not see credential fields. |
| AI credentials in MVP+1 | In the deployed candidate flow, each candidate supplies their own provider/model/API key. Secrets are handled by the backend and are not saved by default. |
| Model architecture | Keep a provider abstraction. Start with one OpenAI-compatible endpoint in POC; broaden support in MVP. |
| Camera choice | Candidate chooses voice-only or video for each interview. Video is a required product capability. |
| Video by phase | POC: capture and replay. MVP: robust local recording, retention, and guided self-review. MVP+1: automated visual coaching. |
| Recording retention | Delete recordings after 5 days. If the laptop is off, cleanup runs on next app launch. |
| Local recording cap | No more than 100 recordings stored at once on the laptop. |
| Visual feedback | MVP+1 may comment on observable presentation cues with evidence. Do not present inferred emotion or a numeric confidence score as fact. |

## User journeys

**POC/MVP operator setup:** clone/download repository -> install dependencies -> create local configuration from `.env.example` -> add own model credentials -> launch local app. Configuration is validated before an interview starts.

**Candidate interview:** provide JD and resume -> choose voice-only or video -> review interview blueprint/role context -> start -> answer spoken questions -> receive clarifying/probing/challenging follow-ups -> end -> read evidence-linked coaching report -> retry. If video was chosen, replay the local recording while it is retained.

**MVP+1 deployed candidate setup:** select provider/model and enter own API key in the app before the interview. The hosted backend uses the key for that candidate's session without exposing it in client code or logs. This flow needs usability and security validation before release.

## POC - Prove the adaptive interview

Target: approximately 6-7 working days on the development laptop. This is a working demo estimate, not a deployment estimate.

- [ ] Build an interview setup screen for JD paste or PDF/DOCX upload, resume PDF/DOCX upload, and voice/video choice.
- [ ] Extract useful text from the JD and resume; identify responsibilities, skills, experience, projects, achievements, and competencies.
- [ ] Read one operator-configured OpenAI-compatible model endpoint and key from local configuration; report missing or invalid configuration clearly.
- [ ] Generate a structured interview blueprint with competencies and planned coverage.
- [ ] Implement an interview state machine: introduction -> question -> listen -> analyze answer -> clarify/probe/challenge/advance -> end -> report.
- [ ] Add microphone capture, transcription, and spoken interviewer prompts.
- [ ] Add optional camera recording and local replay.
- [ ] Produce a basic report with competency feedback and concrete examples from candidate answers.
- [ ] Test with at least a few distinct JD/resume combinations, including vague answers that should trigger follow-ups.

POC exit test: the interviewer asks a relevant question, probes a vague answer for personal ownership or measurable impact, advances when sufficient, and produces feedback tied to the answer. Voice-only and video paths both work.

## MVP - Make the local product usable and shareable

Target: approximately 9-12 working days total including POC. Deployment work is excluded. These items extend and harden the POC.

- [ ] Keep provider-specific code behind a common interface; support OpenAI, Grok, Anthropic, Gemini, and OpenAI-compatible endpoints as applicable. A local/open-weight model can be used through a compatible endpoint when available.
- [ ] Improve PDF/DOCX extraction, file validation, error messages, and handling of unreadable or scanned documents.
- [ ] Persist interview sessions, blueprints, transcripts, reports, and recording references in local SQLite; keep media as files outside the database.
- [ ] Improve voice turn-taking, pause/resume, permission errors, interrupted sessions, and candidate recovery.
- [ ] Record media in chunks, keep large recordings out of browser memory, and provide replay and guided self-review.
- [ ] Enforce the 100-recording local cap and 5-day recording deletion; run cleanup while open and on startup.
- [ ] Improve competency scoring and communication feedback with quoted or linked evidence from answers; support retry.
- [ ] Publish a GitHub-ready repository with pinned dependencies, `.env.example`, `.gitignore`, and clear macOS/Windows/Linux setup instructions. Never commit real API keys, resumes, transcripts, databases, or recordings.
- [ ] Verify installation and core interview flows across the supported operating systems and browsers, including microphone/camera permissions.

MVP exit test: a new user can download the repository, configure their own AI credentials locally, start the app, complete either interview mode, review a report, replay retained video, and retry. No candidate credential fields appear in the interview flow.

## MVP+1 - Deployment and candidate-managed AI

Schedule and detailed architecture to be estimated after POC/MVP validation. This phase is required if the product moves toward a deployed audience-facing version.

- [ ] Design the deployed candidate flow for provider, model, endpoint, and API-key entry.
- [ ] Validate credentials and supported endpoints; route provider requests through the backend. Do not log keys or store them by default.
- [ ] Decide account/session handling and usage controls for a public service.
- [ ] Move persistence and recording storage to deployment-appropriate services while retaining the 5-day recording rule unless explicitly changed.
- [ ] Add automated visual coaching with reviewable moments: framing, camera visibility, gaze toward camera, and other cues only where useful and validated.
- [ ] Treat eye contact and confidence as nuanced coaching topics, not objective traits inferred from a face. Use answer content and speech cues for communication feedback; validate visual claims with users.
- [ ] Test the deployed candidate experience, provider combinations, recording lifecycle, and feedback quality before release.

MVP+1 exit test: a candidate can supply their own supported AI credentials, complete a deployed interview in voice-only or video mode, and receive useful, evidence-linked coaching without exposing their key or receiving unsupported personality claims.

## Local architecture and capacity assumptions

- Browser UI plus a Python application listening on `localhost` for POC/MVP. No rented server is required during development and testing.
- Local SQLite holds structured interview data. Files on disk hold recordings and uploads. Paths must be configurable and never tied to one person's home directory.
- The operator's configured AI provider performs model inference over the internet. A fully offline model would require a separate hardware and performance assessment.
- Target 720p recording at approximately 1-1.5 Mbps for the candidate camera. A 30-minute recording is estimated at about 240-350 MB, so 100 recordings are about 24-35 GB. Budget roughly 80-100 GB of free laptop storage for bitrate variation and temporary files.
- Retention applies to recordings. Retention for transcripts, reports, and uploaded documents remains to be decided.
- Cleanup after 5 days occurs while the app is running and on next launch. A powered-off laptop cannot delete files at the exact five-day mark.

## Out of scope until specifically added

- Hosting or public deployment during POC/MVP.
- Candidate-entered provider credentials during POC/MVP.
- Automated video analysis during POC/MVP.
- Billing, enterprise administration, and hiring decisions made by AI.

## Open product decisions

1. Retention period for transcripts, reports, and uploaded JD/resume files.
2. Which observable video cues are useful enough to include in MVP+1, and how to validate them with candidates.
3. Deployment architecture, operating costs, and whether a candidate key remains session-only or can be securely saved by explicit choice.

## Working rule for coding agents

Before changing code, identify the target phase and relevant checklist items. Preserve phase boundaries. Record implementation and verification in the checklist only when completed. If a requested feature changes this plan, update this guide and the human-readable Word tracker together. Keep estimates labeled as estimates and do not mark a task complete based only on code being written.
