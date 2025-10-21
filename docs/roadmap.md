# Roadmap

This document outlines planned future enhancements for the Claude Skills MCP Server.

## Overview

The current implementation uses RAG-based semantic search to help Claude discover relevant skills. Future versions will expand capabilities to include code execution, binary tools, and more intelligent skill selection using MCP's advanced features.

## Planned Features

### 1. Sandboxed Python Execution

**Status**: Planned

**Goal**: Execute Python code that is part of skill definitions in a secure, isolated environment.

**Use Cases**:
- Skills that include setup scripts or data processing utilities
- Interactive skill demonstrations
- Pre-validation of skill code before Claude uses it
- Running skill-specific tests or examples

**Technical Considerations**:
- Container-based isolation (Docker, Podman, or gVisor)
- Resource limits (CPU, memory, network, filesystem)
- Execution timeout mechanisms
- Python environment management (dependencies, versions)
- Security sandboxing (no host filesystem access, restricted network)

**Implementation Options**:
- **Docker/Podman**: Industry standard, well-tested isolation
- **PyPy Sandbox**: Lighter weight, Python-specific
- **WebAssembly (WASM)**: Future-proof, excellent isolation
- **Firecracker/gVisor**: Lightweight VM approach

**Configuration Example** (proposed):
```json
{
  "execution": {
    "enable_python": true,
    "sandbox_type": "docker",
    "timeout_seconds": 30,
    "memory_limit_mb": 512,
    "allow_network": false,
    "allowed_packages": ["numpy", "pandas", "scikit-learn"]
  }
}
```

### 2. Binary Execution Support

**Status**: Planned

**Goal**: Enable skills to include and execute compiled binaries or system tools.

**Use Cases**:
- Bioinformatics tools (BLAST, BWA, SAMtools)
- Computational chemistry software (RDKit CLI, OpenBabel)
- System utilities required for scientific workflows
- Performance-critical components

**Technical Considerations**:
- Platform compatibility (Linux, macOS, Windows)
- Binary verification and checksums
- Dependency management (shared libraries)
- Even stricter sandboxing than Python (system calls restrictions)
- Digital signatures for trusted binaries

**Security Concerns**:
- Binary provenance verification
- Malware scanning
- Restricted syscalls (seccomp, AppArmor, SELinux)
- No privilege escalation

**Configuration Example** (proposed):
```json
{
  "execution": {
    "enable_binaries": true,
    "allowed_binaries": {
      "blast": {
        "path": "/usr/local/bin/blastn",
        "checksum": "sha256:abc123...",
        "max_runtime": 300
      }
    },
    "binary_sandbox": "firejail"
  }
}
```

### 3. MCP Sampling-Based Skill Selection

**Status**: Planned (highest priority for intelligence improvement)

**Goal**: Replace or augment RAG with MCP's `sampling` feature for more intelligent, context-aware skill selection.

**Current Limitation**: 
The RAG approach uses vector similarity on skill descriptions, which:
- Misses contextual nuances from the conversation
- Can't dynamically reason about skill combinations
- Doesn't learn from conversation history
- Limited to semantic similarity (no reasoning)

**MCP Sampling Approach**:
Instead of pre-computing embeddings, use MCP's `sampling` feature to let the LLM directly reason about which skills are most relevant given the full context of the conversation.

**How It Would Work**:
1. Claude requests skill selection via MCP sampling
2. Server provides all available skills (or metadata) as context
3. LLM reasons about task requirements and skill applicability
4. Returns ranked, contextually-appropriate skills with justification

**Benefits**:
- **Contextual awareness**: Considers entire conversation, not just current query
- **Reasoning-based**: Can understand complex multi-step tasks
- **Combination detection**: Identifies when multiple skills should be used together
- **Adaptive**: Improves as conversation progresses
- **Explainable**: LLM can explain why it chose specific skills

**Technical Implementation**:
- Expose skill catalog as MCP resource
- Use MCP sampling prompts for skill selection reasoning
- Optional: Hybrid approach (RAG for initial filtering, sampling for final selection)
- Cache LLM selection decisions to reduce latency

**Configuration Example** (proposed):
```json
{
  "skill_selection": {
    "method": "sampling",  // or "rag" or "hybrid"
    "sampling_config": {
      "model": "claude-3.5-sonnet",
      "max_tokens": 2048,
      "temperature": 0.3,
      "system_prompt": "Select the most relevant skills for the task..."
    },
    "hybrid_config": {
      "rag_prefilter": 20,
      "sampling_final_selection": 5
    }
  }
}
```

**References**:
- [MCP Sampling Specification](https://modelcontextprotocol.io/docs/concepts/sampling)
- [Using Sampling for Intelligent Tool Selection](https://modelcontextprotocol.io/docs/patterns/sampling)

### 4. Skill Composition and Workflows

**Status**: Future consideration

**Goal**: Enable skills to reference and compose other skills into workflows.

**Use Cases**:
- Multi-step scientific analysis pipelines
- Data preprocessing -> analysis -> visualization chains
- Conditional skill execution based on results

**Technical Considerations**:
- Workflow definition format (YAML, JSON)
- Dependency graphs
- Error handling and rollback
- Parallel execution where possible

### 5. Dynamic Skill Updates

**Status**: Future consideration

**Goal**: Hot-reload skills without server restart.

**Use Cases**:
- Rapid skill development iteration
- Community-contributed skill repositories
- Periodic pulls from GitHub sources

**Technical Considerations**:
- Filesystem watching for local skills
- GitHub webhooks or polling
- Re-indexing strategy (incremental vs. full)
- Cache invalidation

## Implementation Priorities

### Phase 1: Foundation (Current)
- ✅ Vector-based semantic search
- ✅ GitHub and local skill loading
- ✅ Basic MCP server implementation

### Phase 2: Intelligent Selection (Next)
- 🔄 MCP sampling-based skill selection
- 🔄 Hybrid RAG + sampling approach
- 🔄 Conversation context integration

### Phase 3: Execution Capabilities
- ⏳ Sandboxed Python execution
- ⏳ Security hardening and isolation
- ⏳ Resource management

### Phase 4: Extended Execution
- ⏳ Binary execution support
- ⏳ Cross-platform compatibility
- ⏳ Trusted binary registry

### Phase 5: Advanced Features
- ⏳ Skill composition and workflows
- ⏳ Dynamic skill updates
- ⏳ Performance optimizations

## Contributing to the Roadmap

We welcome community input on priorities and new feature ideas:

1. **Discuss**: Open an issue to discuss the feature
2. **Design**: Collaborate on technical approach
3. **Implement**: Submit PR with tests and documentation
4. **Review**: Maintainer review and feedback

For significant features (especially execution-related), security review is mandatory.

## Timeline

These features are planned but not yet scheduled. Priority will be determined by:
- Community demand and contribution
- Security and stability considerations
- Integration with Claude and MCP ecosystem developments
- K-Dense AI's commercial platform requirements

## Questions or Ideas?

- Open a [GitHub Issue](https://github.com/K-Dense-AI/claude-skills-mcp/issues)
- Email: [orion.li@k-dense.ai](mailto:orion.li@k-dense.ai)

---

**Legend**:
- ✅ Completed
- 🔄 In Progress
- ⏳ Planned

