# Generative AI Immigration and Booking Scheduler

## 📌 Project Overview

The **Generative AI Immigration and Booking Scheduler** is an intelligent, multi-agent conversational system designed to streamline immigration-related consultations and appointment scheduling for Canadian migration services.

This sophisticated application combines natural language processing, document understanding, and automated booking management to provide a seamless user experience.

---

## ⚙️ Core Architecture

### 1. Multi-Agent LangGraph Framework

The system uses a modular architecture built on **LangGraph**, featuring:

- **Intent Classification Agent** — Routes user queries to appropriate agents.
- **Immigration Information Agent** — Provides guidance on Canadian migration processes.
- **Booking Management Agent** — Handles appointment scheduling and form workflows.
- **Fallback Agent** — Gracefully manages out-of-scope queries.

---

### 2. Intelligent Workflow Orchestration

The main graph orchestrator coordinates the specialized agents:

- **Dynamic Intent Routing** — Classifies messages into categories: inquiries, bookings, or fallback.
- **Context-Aware Processing** — Maintains history and user state across sessions.
- **Parallel Processing** — Supports handling of multiple intents concurrently.

---

### 3. Advanced Booking System

Implements a structured booking state machine:

- **Information Extraction** — Extracts details like name, email, date, and time from natural language.
- **Form Validation** — Ensures all required data is collected before proceeding.
- **Confirmation Workflow** — Guides users through a multi-step confirmation process.
- **Database Integration** — Uses SQLite and SQLAlchemy for persistent data storage.

---

### 4. RAG-Enhanced Immigration Knowledge Base

- **Document Processing** — ChromaDB stores vectorized immigration documents.
- **Semantic Search** — Powered by Sentence Transformers for smart retrieval.
- **Contextual Responses** — Provides accurate, citation-backed answers.

---

## ✨ Key Features

### 🧠 Intelligent Conversation Management

- Multi-turn conversation handling
- Context preservation across turns
- Date/time recognition (e.g., "tomorrow", "next week")

### 💾 Robust Data Management

- SQLAlchemy-based models for users and bookings
- Repository pattern for clean data access
- Service layer for encapsulated business logic

### 🗣️ Advanced NLP Capabilities

- Intent classification with fallback handling
- Extraction of structured info from free-form input
- Email and date/time validation

### 🎯 User Experience Features

- Form state management across steps
- Friendly error handling
- Multi-step confirmation workflows

---

## 🧪 Technical Implementation

### 🛠️ Technology Stack

- **Backend**: Python + FastAPI
- **AI/ML**: LangChain + LangGraph
- **Database**: SQLite + SQLAlchemy
- **Vector Store**: ChromaDB
- **NLP Models**: Sentence Transformers

### 🔄 Workflow Overview

1. **Message Intake** — Input routed through intent classifier.
2. **Agent Selection** — Intent determines which agent handles the message.
3. **Context Management** — Maintains state during conversation flow.
4. **Response Generation** — Agents generate appropriate replies.
5. **Action Execution** — Booking actions persist data to the database.

---

## 📎 Summary

This project showcases a robust integration of **conversational AI**, **document understanding**, and **workflow automation** — tailored for Canadian immigration services. The architecture prioritizes scalability, maintainability, and user satisfaction through intelligent, real-time interaction.
