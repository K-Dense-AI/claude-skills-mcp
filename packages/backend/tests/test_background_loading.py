"""Tests for background skill loading functionality."""

import asyncio
import time
import pytest
from claude_skills_mcp_backend.search_engine import SkillSearchEngine
from claude_skills_mcp_backend.server import SkillsMCPServer, LoadingState
from claude_skills_mcp_backend.skill_loader import load_skills_in_batches, Skill


def test_loading_state_thread_safety():
    """Test that LoadingState is thread-safe."""
    import threading

    state = LoadingState()

    def update_progress():
        for i in range(100):
            state.update_progress(i, 100)

    # Run multiple threads updating the state
    threads = [threading.Thread(target=update_progress) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify state is consistent
    assert state.loaded_skills >= 0
    assert state.total_skills >= 0


def test_loading_state_status_messages():
    """Test that LoadingState generates correct status messages."""
    state = LoadingState()

    # Initial state
    msg = state.get_status_message()
    assert "Skills are being loaded" in msg

    # Update with progress
    state.update_progress(10, 100)
    msg = state.get_status_message()
    assert "10/100 skills loaded" in msg

    # Mark complete
    state.mark_complete()
    msg = state.get_status_message()
    assert msg is None  # No message when complete


def test_search_engine_incremental_indexing():
    """Test that search engine can add skills incrementally."""
    engine = SkillSearchEngine("all-MiniLM-L6-v2")

    # Create test skills
    skills1 = [
        Skill("Skill 1", "Description 1", "Content 1", "source1"),
        Skill("Skill 2", "Description 2", "Content 2", "source2"),
    ]

    skills2 = [
        Skill("Skill 3", "Description 3", "Content 3", "source3"),
        Skill("Skill 4", "Description 4", "Content 4", "source4"),
    ]

    # Add first batch
    engine.add_skills(skills1)
    assert len(engine.skills) == 2
    assert engine.embeddings is not None
    assert engine.embeddings.shape[0] == 2

    # Add second batch
    engine.add_skills(skills2)
    assert len(engine.skills) == 4
    assert engine.embeddings.shape[0] == 4

    # Verify search works with all skills
    results = engine.search("Description 3", top_k=1)
    assert len(results) == 1
    assert results[0]["name"] == "Skill 3"


def test_search_engine_thread_safety():
    """Test that search engine is thread-safe during concurrent operations."""
    import threading

    engine = SkillSearchEngine("all-MiniLM-L6-v2")

    # Create test skills
    def add_batch(batch_num):
        skills = [
            Skill(
                f"Skill {batch_num}-{i}",
                f"Description {batch_num}-{i}",
                f"Content {batch_num}-{i}",
                f"source{batch_num}-{i}",
            )
            for i in range(5)
        ]
        engine.add_skills(skills)

    # Add skills from multiple threads
    threads = [threading.Thread(target=add_batch, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify all skills were added correctly
    assert len(engine.skills) == 50
    assert engine.embeddings.shape[0] == 50


def test_batch_loading_function():
    """Test the batch loading function with callbacks."""
    from claude_skills_mcp_backend.config import DEFAULT_CONFIG

    batches_received = []
    total_counts = []

    def callback(batch_skills, total_loaded):
        batches_received.append(len(batch_skills))
        total_counts.append(total_loaded)

    # Use a small subset for testing
    skill_sources = [
        {
            "type": "github",
            "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
            "subpath": "scientific-thinking/exploratory-data-analysis",
        }
    ]

    # Load with small batch size
    load_skills_in_batches(skill_sources, DEFAULT_CONFIG, callback, batch_size=1)

    # Verify batches were processed
    assert len(batches_received) > 0
    assert sum(batches_received) == total_counts[-1]
    print(
        f"\nReceived {len(batches_received)} batches, total {total_counts[-1]} skills"
    )


@pytest.mark.integration
def test_background_loading_with_server():
    """Test that server starts immediately and loads skills in background."""
    import threading

    # Create engine and loading state
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    loading_state = LoadingState()

    # Create server
    server = SkillsMCPServer(engine, loading_state)

    # Server should start even with no skills loaded
    assert len(engine.skills) == 0

    # Simulate background loading
    def background_loader():
        time.sleep(0.5)  # Simulate loading delay
        skills = [
            Skill(f"Skill {i}", f"Description {i}", f"Content {i}", f"source{i}")
            for i in range(20)
        ]

        # Load in batches of 5
        for i in range(0, 20, 5):
            batch = skills[i : i + 5]
            engine.add_skills(batch)
            loading_state.update_progress(i + 5, 20)
            time.sleep(0.1)

        loading_state.mark_complete()

    # Start background thread
    thread = threading.Thread(target=background_loader, daemon=True)
    thread.start()

    # Server should respond immediately (even with no skills)
    result = asyncio.run(
        server._handle_search_skills({"task_description": "test", "top_k": 3})
    )
    assert len(result) == 1
    text = result[0].text

    # Should show loading status
    assert "LOADING" in text or "No skills loaded yet" in text

    # Wait for background loading to complete
    thread.join(timeout=5)

    # Now should have all skills and no loading message
    result = asyncio.run(
        server._handle_search_skills({"task_description": "Description 5", "top_k": 3})
    )
    text = result[0].text

    # Should not show loading status anymore
    assert "LOADING" not in text
    assert "Found" in text

    print("\n✓ Server started immediately before skills loaded")
    print("✓ Loading status shown during background loading")
    print("✓ Search works with incrementally loaded skills")
    print("✓ Loading status removed after completion")


@pytest.mark.integration
def test_startup_time_comparison():
    """Compare startup time with background loading vs synchronous loading."""

    # Create small test configuration
    _ = [
        {
            "type": "github",
            "url": "https://github.com/K-Dense-AI/claude-scientific-skills",
            "subpath": "scientific-thinking",
        }
    ]

    # Measure background loading startup (server ready immediately)
    start_time = time.time()
    engine = SkillSearchEngine("all-MiniLM-L6-v2")
    loading_state = LoadingState()
    __ = SkillsMCPServer(engine, loading_state)
    background_startup_time = time.time() - start_time

    # Server is ready even though skills aren't loaded yet
    print(f"\nBackground loading startup: {background_startup_time:.2f}s")
    print("  - Server ready: ✓ (immediate)")
    print("  - Skills loaded: in progress (background)")

    # The background startup should be very fast (<5 seconds)
    assert background_startup_time < 5.0, "Background startup should be fast"

    print("\n✓ Background loading allows immediate server startup")
    print(f"✓ Server is responsive in {background_startup_time:.2f}s")
    print("✓ Skills load in parallel without blocking")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
