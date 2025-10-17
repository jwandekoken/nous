# Project Scope: AI Agent Memory System

This document outlines the scope for building a memory system for AI Agents using a knowledge graph.

## Core Concepts

The system is built around four fundamental concepts:

1.  **Entity**: Represents a canonical person, place, or concept. Each `Entity` has a stable, unique identifier.
2.  **Identifier**: An external identifier linked to an `Entity`, such as an email address, phone number, or username. It's used to look up and identify entities.
3.  **Fact**: A discrete piece of information or an attribute related to an `Entity` (e.g., "lives in New York", "works at Acme Corp").
4.  **Source**: The origin of a `Fact`, providing traceability. This could be a chat message, an email, or a document.

## System Workflow

The basic workflow of the memory system is as follows:

1.  An `Entity` is created or identified using an `Identifier`.
2.  Information is processed from a `Source` to extract `Facts`.
3.  These `Facts` are then associated with the corresponding `Entity`.

This structure allows the system to build a rich, interconnected memory graph for an AI agent, with clear provenance for every piece of information.
