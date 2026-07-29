# VANI-DRISHTI Engine: Real-Time Sign Language Translation Sub-Module

> **A focused, deep-dive exploration of low-latency video frame ingestion, landmark extraction, and AI-driven sequence classification.**

---

## 📌 Project Overview
VANI-DRISHTI Engine is a specialized sub-module designed to tackle the most critical challenge in automated Sign Language Interpretation: **Real-time, low-latency streaming and accurate feature inference.**

Rather than building a surface-level UI, this repository focuses deeply on product architecture, system resilience, and leveraging AI tools throughout the full engineering lifecycle.

---

## 🏗️ Proposed Architecture Flow
[Webcam Feed / Stream]
│
▼
[Frame Decimator & Ingestion Engine]
│
▼
[MediaPipe / Keypoint Feature Extractor]
│
▼
[Inference Pipeline (Sequence Model)]
│
▼
[Text Streamer & Audio TTS Synthesizer]


---

## ⚙️ Key Technical Challenges Being Addressed
1. **Frame Dropping & Bottlenecks:** Preventing UI lag while processing high-FPS video streams.
2. **Missing Landmark Fallbacks:** Handling partial hand occlusion gracefully.
3. **AI Hallucination & Misdirection:** Documenting where AI coding tools suggested suboptimal architectures and how they were caught and corrected.

---

## 🧭 Live Project Transparency
This repository is intentionally open from Day 1 to make the engineering journey visible.
- **`PRD.md`** defines the problem, scope, and target metrics.
- **`JOURNAL.md`** captures the live decision log, AI corrections, dead ends, and trade-offs.
- **`README.md`** explains the current architecture focus and where the work is headed.

> The repo is being built rough and often, not held back for a polished reveal. Follow the progress as it happens.

## 📍 Current Status
- Problem scope defined
- Architecture designed
- Live documentation and tracking established
- Next step: prototype client-side landmark extraction and backend inference pipeline
