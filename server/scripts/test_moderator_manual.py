"""Print manual Socket.IO / UX verification steps (no automation)."""


def main() -> None:
    print(
        """
Manual moderator & chat checks (server + 3 browsers):

1) Question: send "@moderator what should we prioritize?" → facilitator reply ~30s
2) Silence: leave one user quiet 3+ min → invite by name (active mode)
3) Dominance: one user sends many messages → balance prompt
4) Language: "you're an idiot" or two strong terms → warning banner + flagged bubble
5) End session → personalized feedback per user on Feedback page

See /health for llm_provider, socketio_async_mode, supabase_connected.
"""
    )


if __name__ == "__main__":
    main()
