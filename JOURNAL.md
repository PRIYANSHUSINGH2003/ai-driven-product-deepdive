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

## 🚦 Next Planned Milestones
- [x] Scope PRD & System Architecture Diagram
- [ ] Implement client-side WebAssembly MediaPipe Pipeline
- [ ] Build WebSocket buffer pipeline for sequence creation
- [ ] Measure & Log Frame Processing Latency Benchmarks