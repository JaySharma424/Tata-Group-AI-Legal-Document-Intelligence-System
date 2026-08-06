# 🏛️ Tata AI Legal Intelligence - Frontend Client

This repository contains the **Frontend Client** for the Tata AI Legal Intelligence portal. It is a modern, responsive, and highly secure React application designed for corporate legal and compliance teams to upload documents, review AI-generated Risk Matrices, and manage audit trails.

---

## ✨ Frontend Features

*   **🔒 Secure Authentication Flow:** Implements a robust login gateway (`AuthGate`) with JWT-based session management. 
*   **🛡️ Global Axios Interceptors:** Automatically attaches the Bearer token to all outgoing API requests and gracefully handles `401 Unauthorized` responses by clearing local storage and redirecting to login.
*   **🎨 Glassmorphism UI:** Built with Tailwind CSS, featuring a sleek, dark-mode enterprise aesthetic with backdrop blurs, gradients, and highly readable typography.
*   **📄 Dynamic Document Workspace:** A centralized dashboard for uploading legal contracts (PDF/Docx) and viewing real-time AI parsing metrics, RAG rationales, and risk scores.
*   **🗂️ Real-Time Audit Sidebar:** An auto-refreshing history sidebar that tracks accepted/rejected documents across the user's isolated workspace.
*   **📦 Blob PDF Handling:** Seamless frontend processing for downloading binary PDF blob data to generate certified Executive Audit Packages.
*   **💬 Floating AI Assistant:** Integrated `LegalChatWidget` that maintains context of the currently active document for RAG-based Q&A.

---

## 🛠️ Technology Stack

*   **Core:** React 18 & TypeScript
*   **Build Tool:** Vite (for lightning-fast HMR and optimized builds)
*   **Styling:** Tailwind CSS
*   **HTTP Client:** Axios
*   **Icons:** Lucide React

---

## 📂 Key Component Structure

*   `src/App.tsx`: The main layout container. Manages the global authentication state, applies Axios interceptors, and orchestrates the layout (Header, Sidebar, Workspace, Chat).
*   `src/components/AuthGate.tsx`: The entry point for unauthenticated users. Captures login credentials and stores the JWT in `localStorage`.
*   `src/components/DocumentWorkspace.tsx`: The core UI where users upload files, view the extracted RAG Risk Matrix, accept/reject documents, and download the audit PDF.
*   `src/components/DocumentHistorySidebar.tsx`: A side navigation panel that fetches and displays the user's secure audit archive.
*   `src/components/LegalChatWidget.tsx`: A persistent, interactive chat window for querying the Aadhya AI assistant.

---

## 🚀 Getting Started

### Prerequisites
*   Node.js (v18 or higher recommended)
*   npm or yarn

### Installation & Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend