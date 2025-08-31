SupportYourCreator — Play2Earn Discord Bots

Overview
- Two Discord bots that power a Play2Earn flow for the Fortnite Island Creator ecosystem .
- Players submit proof of played time to the bot via DM; OCR and embedded hash validation verifies the image proof.
- Roles and giveaway eligibility are granted based on minutes played, invites, and creator code.
- A secondary bot tracks invites, updates a live leaderboard, and maintains member stats of the Discord server.

Key Features
- Proof Submission: Users click a button, DM the bot an image, and receive acceptance/rejection feedback.
- OCR Verification: `ai.py` uses Tesseract + OpenCV to extract and validate map code, hash, and played minutes.
- Weighted Giveaways: Winners are selected with chances weighted by minutes, invites, and creator code.
- Roles Automation: Roles like Bronze/Gold/Diamond/Champion/Unreal assigned based on played minutes thresholds.
- Invite Tracking: Tracks inviter relationships and updates a channel with joins/leaves and invite totals.
- Leaderboard: Periodically updates a message showing top supporters and their stats.
- Persistence: Local filesystem JSON cache plus PostgreSQL persistence, with background queues for non-blocking I/O.

Repo Structure
- `main.py`: Primary entrypoint. Handles DMs, proof processing, admin commands, and starts queue workers. Spawns secondary bot process.
- `src/`
  - `src/ai.py`: OCR pipeline and hash verification logic.
  - `src/config.py`: Loads IDs/tokens/URLs from environment variables and centralizes configuration.
  - `src/db_handler.py`: Local JSON cache, async PostgreSQL sync, image download + object-storage upload helpers.
  - `src/play2earn_bot.py`: Secondary bot. Tracks invites, updates leaderboard and member stats.
  - `src/queues.py`: Async queues for rate limiting Discord API, CPU-intensive tasks, PostgreSQL, and object storage.
- `manual_sender.py`: Helper script to post initial messages/components to channels.
- `models/`: Tesseract model data directory (used by OCR).
- `timeTracker.verse`: UEFN Verse device script that shows the player their minutes + hash for screenshot proof.
- `requirements.txt`: Python dependencies (pip-compatible).

This project was developed on Replit.
