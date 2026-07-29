# Engineering & Decision Journal

> **Purpose:** Documenting real-time decision-making, architectural iterations, AI integrations, and mistake-catch logs throughout the development of VANI-DRISHTI Core Engine.

---

## 🗓️ Phase 0: Problem Scoping & Architecture Design

### 💡 Initial Brainstorming & AI Collaboration
- **Question Posed to AI:** "How to minimize latency when passing raw video frames to a Python/Node backend for real-time sign language detection?"
- **AI Recommendation:** The AI initially suggested sending base64-encoded video frames over WebSocket for every single frame (30 FPS).
- **The Catch / Where AI Was Misleading:**
  - Base64 encoding adds ~33% overhead to payload size.
  - Sending raw frames at 30 FPS over WebSockets creates network congestion and high server load.
- **Architectural Correction:**
  - Decided to move landmark/keypoint extraction (MediaPipe) to the **Client-side / Edge (Browser)** using WebAssembly.
  - Only transfer lightweight 3D coordinate arrays (JSON/Binary Buffer) over WebSocket to the backend inference model.
  - **Result:** Reduced network bandwidth requirement by >90%.

---

## 🧭 Day 0: Live Repo & Product Discipline
- Repository opened early to show the real engineering journey instead of waiting for a polished final build.
- Focused on **scope validation, problem research, and architecture discipline** before jumping into code.
- Constraint chosen: one narrow, deep problem with high-quality execution rather than broad surface-level scope.
- Immediate deliverable: a small, demonstrable prototype of edge landmark extraction and lightweight backend inference.

## 🚦 Next Planned Milestones
- [x] Scope PRD & System Architecture Diagram
- [x] Open the repo with live documentation and transparent progress tracking
- [ ] Implement client-side WebAssembly MediaPipe Pipeline
- [ ] Build WebSocket buffer pipeline for sequence creation
- [ ] Measure & Log Frame Processing Latency Benchmarks
- [ ] Capture AI misdirections and fixes as part of the journal
