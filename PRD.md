# Product Requirement Document (PRD)
## Project: VANI-DRISHTI Core Translation Engine (Micro-Module)

### 1. Problem Statement
Real-time Sign Language Recognition (SLR) systems often suffer from high frame-processing latency, stream dropouts, and poor real-time audio synthesis integration. Existing approaches rely on monolithic heavy models that are difficult to run efficiently in low-latency Web environments.

### 2. Core Objectives
- Build a lightweight, modular real-time video stream processor using WebRTC/OpenCV.
- Translate keypoint data (Hand/Pose landmarks) into structured textual token streams.
- Integrate AI as a thinking and design partner for architectural optimization, prompt tuning, and edge-case handling.
- Maintain Sub-200ms end-to-end latency for frame ingestion to text token generation.

### 3. User Personas
- **Primary User:** Hearing and Speech Impaired individuals requiring live conversion during video calls or in-person communication.
- **Secondary User:** Non-sign language speakers needing real-time audio/text interpretation.

### 4. System Requirements & Scope

#### Functional Requirements
- **Video Ingestion Pipeline:** Capture webcam frame streams efficiently without clogging the JS main thread.
- **Feature Extraction Layer:** Extract 3D hand and pose landmarks (MediaPipe / Custom Model).
- **Inference Engine:** Process keypoints via an optimized sequence model (LSTM / Transformer / Lightweight Neural Net).
- **Text & Audio Output:** Emit real-time text tokens and stream TTS (Text-to-Speech) audio output.

#### Non-Functional Requirements
- **Latency:** End-to-end processing time < 200ms per frame batch.
- **Resilience:** Graceful handling of low-light conditions, missing hand landmarks, and stream interruptions.
- **Maintainability:** Clean separation between video capture, AI inference, and UI rendering layers.

### 5. Execution Plan
- **Phase 0:** Live repo setup, requirements validation, architecture design, and daily decision tracking.
- **Phase 1:** Build a client-side landmark extraction pipeline (browser/WebAssembly) and send compact keypoint data to the backend.
- **Phase 2:** Implement backend sequence creation, model inference, and text-token generation.
- **Phase 3:** Measure latency, log benchmark results, and handle edge-case resilience.
- **Phase 4:** Document what worked, what failed, and how AI guidance was corrected.

### 6. Validation Criteria
- Early deliverable: documented, working prototype that demonstrates edge landmark extraction and light-weight backend inference.
- Evidence of product thinking: scoped problem, assumptions tested, and trade-offs explicitly recorded.
- Transparency: repo updates and journal entries visible from the first commit.

---