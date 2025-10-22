"""Tests for update checker functionality."""

from unittest.mock import Mock, patch


from claude_skills_mcp_backend.update_checker import (
    GitHubSourceTracker,
    LocalSourceTracker,
    UpdateChecker,
)


class TestGitHubSourceTracker:
    """Tests for GitHubSourceTracker."""

    def test_parse_github_url(self):
        """Test parsing GitHub URLs."""
        tracker = GitHubSourceTracker()

        # Basic URL
        result = tracker._parse_github_url("https://github.com/owner/repo")
        assert result == ("owner", "repo", "main")

        # URL with branch
        result = tracker._parse_github_url("https://github.com/owner/repo/tree/develop")
        assert result == ("owner", "repo", "develop")

        # URL with branch and subpath
        result = tracker._parse_github_url(
            "https://github.com/owner/repo/tree/main/subdir"
        )
        assert result == ("owner", "repo", "main")

        # Invalid URL
        result = tracker._parse_github_url("https://github.com/owner")
        assert result is None

    def test_get_state_key(self):
        """Test state key generation."""
        tracker = GitHubSourceTracker()
        key = tracker._get_state_key("owner", "repo", "main")
        assert key == "owner/repo/main"

    @patch("claude_skills_mcp_backend.update_checker.httpx.Client")
    def test_check_for_updates_first_time(self, mock_client_class):
        """Test first-time check (should not trigger update)."""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"sha": "abc123"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        tracker = GitHubSourceTracker()
        source_config = {"url": "https://github.com/owner/repo"}

        # First check should return False (no update)
        result = tracker.check_for_updates(source_config)
        assert result is False

        # Verify SHA was saved
        assert tracker.state_manager.get("owner/repo/main") == "abc123"

    @patch("claude_skills_mcp_backend.update_checker.httpx.Client")
    def test_check_for_updates_with_change(self, mock_client_class):
        """Test detecting a change."""
        tracker = GitHubSourceTracker()

        # Set initial state
        tracker.state_manager.set("owner/repo/main", "abc123")

        # Mock HTTP response with new SHA
        mock_response = Mock()
        mock_response.json.return_value = {"sha": "def456"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        source_config = {"url": "https://github.com/owner/repo"}

        # Should detect change
        result = tracker.check_for_updates(source_config)
        assert result is True

        # Verify SHA was updated
        assert tracker.state_manager.get("owner/repo/main") == "def456"

    @patch("claude_skills_mcp_backend.update_checker.httpx.Client")
    def test_check_for_updates_no_change(self, mock_client_class):
        """Test no change detected."""
        tracker = GitHubSourceTracker()

        # Set initial state
        tracker.state_manager.set("owner/repo/main", "abc123")

        # Mock HTTP response with same SHA
        mock_response = Mock()
        mock_response.json.return_value = {"sha": "abc123"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        source_config = {"url": "https://github.com/owner/repo"}

        # Should not detect change
        result = tracker.check_for_updates(source_config)
        assert result is False

    def test_get_api_usage(self):
        """Test API usage tracking."""
        tracker = GitHubSourceTracker()
        tracker.api_calls_this_hour = 5

        usage = tracker.get_api_usage()
        assert usage["calls_this_hour"] == 5
        assert usage["limit_per_hour"] == 60
        assert usage["authenticated"] is False

        # With token
        tracker_auth = GitHubSourceTracker(github_token="test_token")
        usage = tracker_auth.get_api_usage()
        assert usage["limit_per_hour"] == 5000
        assert usage["authenticated"] is True


class TestLocalSourceTracker:
    """Tests for LocalSourceTracker."""

    def test_check_for_updates_first_time(self, tmp_path):
        """Test first-time check for local source."""
        # Create a test skill file
        skill_dir = tmp_path / "skill1"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("test content")

        tracker = LocalSourceTracker()
        source_config = {"path": str(tmp_path)}

        # First check should return False
        result = tracker.check_for_updates(source_config)
        assert result is False

    def test_check_for_updates_with_modification(self, tmp_path):
        """Test detecting modified files."""
        # Create initial skill file
        skill_dir = tmp_path / "skill1"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("test content")

        tracker = LocalSourceTracker()
        source_config = {"path": str(tmp_path)}

        # First check
        tracker.check_for_updates(source_config)

        # Modify the file
        import time

        time.sleep(0.01)  # Ensure mtime changes
        skill_file.write_text("modified content")

        # Should detect change
        result = tracker.check_for_updates(source_config)
        assert result is True

    def test_check_for_updates_nonexistent_path(self):
        """Test handling nonexistent path."""
        tracker = LocalSourceTracker()
        source_config = {"path": "/nonexistent/path"}

        # Should not crash
        result = tracker.check_for_updates(source_config)
        assert result is False


class TestUpdateChecker:
    """Tests for UpdateChecker."""

    @patch("claude_skills_mcp_backend.update_checker.httpx.Client")
    def test_check_for_updates_mixed_sources(self, mock_client_class, tmp_path):
        """Test checking multiple source types."""
        # Setup GitHub mock
        mock_response = Mock()
        mock_response.json.return_value = {"sha": "abc123"}
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Setup local path
        skill_dir = tmp_path / "skill1"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("content")

        checker = UpdateChecker()

        # Clear any existing state to ensure clean test
        checker.github_tracker.state_manager.clear()
        checker.local_tracker.state_manager.clear()

        sources = [
            {"type": "github", "url": "https://github.com/owner/repo"},
            {"type": "local", "path": str(tmp_path)},
        ]

        result = checker.check_for_updates(sources)

        # First check should not trigger updates (establishes baseline)
        assert result.has_updates is False
        assert len(result.changed_sources) == 0
        assert result.api_calls_made >= 0

    def test_get_api_usage(self):
        """Test getting API usage stats."""
        checker = UpdateChecker()
        usage = checker.get_api_usage()

        assert "calls_this_hour" in usage
        assert "limit_per_hour" in usage
        assert "authenticated" in usage
