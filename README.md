# BytesMusic

### A YouTube Music-style open-source music player — without the clutter.

**BytesMusic** is an open-source web music client built by **[@harshitethic](https://github.com/harshitethic)**.

It is designed to feel familiar to YouTube Music while using a custom **BytesMusic / @harshitethic** interface: dark, minimal, fast, and focused on listening.

> **Search music. Play it. Build a queue. Keep your history. Discover more.**

---

## Features

### Music discovery
- Search the public YouTube Music catalog
- Search by songs, artists, albums and videos
- Supports international music, including Hindi, Punjabi, Tamil, Telugu, English, and more
- Uses the open-source [`ytmusicapi`](https://github.com/sigma67/ytmusicapi) project
- No Google Cloud API key required

### Playback
- YouTube's official embedded player
- Play songs directly from search results
- Previous / next controls
- Persistent bottom player
- Volume control
- Shuffle
- Repeat
- Up Next queue

### Discovery & recommendations
- Recommendation section
- Queue-based listening
- Recently played history
- Personalized recommendations when a BytesMusic account is enabled

### Personal library
- Like songs
- Listening history
- Queue
- Optional account system

### Simple BytesMusic accounts

Accounts are completely optional.

Sign up with:

```text
Username
Password
Recovery question
Recovery answer
```

Password recovery uses the recovery answer.

There is intentionally:

- No Google OAuth
- No email verification
- No phone verification
- No QR authentication
- No API key required

This is a simple local account system intended for the BytesMusic project.

### Admin Panel

BytesMusic includes a built-in admin panel accessible at `/admin`.

- The first registered user automatically becomes the admin
- Admins can view dashboard statistics (total songs, users, plays, likes, artists, playlists)
- View and manage all users (promote/demote admin, delete users)
- Browse all play history and likes across the platform
- See most played and most liked songs, trending charts, and recent activity
- The admin panel is hidden from normal users — only admin accounts see the link

---

## Design

BytesMusic is styled around the **@harshitethic** portfolio aesthetic:

- Deep green / black interface
- Neon mint accents
- Minimal typography
- Technical / developer-inspired UI
- YouTube Music-inspired information architecture

---

## Architecture

```text
┌──────────────────────────────┐
│       BytesMusic UI          │
│      HTML / CSS / JS         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      BytesMusic Server       │
│          Python              │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│  ytmusicapi  │ │   SQLite     │
│ Music search │ │ Accounts /   │
│              │ │ History /    │
│              │ │ Likes /      │
│              │ │ Admin        │
└──────┬───────┘ └──────────────┘
       │
       ▼
┌──────────────────────────────┐
│ YouTube official embedded    │
│ player                       │
└──────────────────────────────┘
```

BytesMusic does **not** download, extract, or re-host YouTube audio.

---

## Getting Started

### Requirements

- Python 3.10+
- A modern browser
- Internet connection

### 1. Clone

```bash
git clone https://github.com/harshitethic/BytesMusic.git
cd BytesMusic
```

### 2. Install dependencies

Windows:

```powershell
py -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m pip install -r requirements.txt
```

### 3. Start BytesMusic

Windows:

```powershell
py app.py
```

macOS / Linux:

```bash
python3 app.py
```

### 4. Open the app

```text
http://localhost:8000
```

### 5. Admin Panel

The first account you create automatically becomes the admin. After signing in, visit:

```text
http://localhost:8000/admin
```

---

## Project Structure

```text
BytesMusic/
├── static/
│   ├── index.html
│   └── admin.html
├── tests/
│   └── test_app.py
├── .github/
│   └── workflows/
│       └── tests.yml
├── docs/
│   ├── bytesmusic-1.png
│   ├── bytesmusic-2.png
│   ├── bytesmusic-3.png
│   ├── bytesmusic-4.png
│   ├── bytesmusic-5.png
│   ├── bytesmusic-6.png
│   └── bytesmusic-7.png
├── app.py
├── requirements.txt
├── README.md
└── LICENSE
```

`bytesmusic.db` is generated locally at runtime and should not be committed.

---

## Configuration

BytesMusic is designed to run without paid APIs.

There is no Google/YouTube API key required for the core music search.

The project uses the public functionality exposed through the open-source `ytmusicapi` ecosystem.

---

## Privacy & accounts

BytesMusic does not require an account to search and listen.

If you create a BytesMusic account, account-related data is used for features such as history, likes, recommendations, and password recovery.

Do not use a password you use for important external accounts.

The built-in recovery-question system is intentionally simple and **should not be treated as enterprise-grade authentication**.

---

## Important

BytesMusic is an independent open-source project.

It is **not affiliated with, endorsed by, or sponsored by YouTube or Google**.

YouTube playback is provided through YouTube's official embedded player.

BytesMusic does not:

- Download YouTube audio
- Re-host YouTube audio
- Circumvent YouTube playback restrictions
- Provide DRM bypass functionality

Users are responsible for complying with the terms and laws applicable to the services and content they access.

---

## Roadmap

- [ ] Better recommendation engine
- [ ] Improved mobile experience
- [ ] PWA / installable app
- [ ] Playlists
- [ ] Public playlists
- [ ] Artist pages
- [ ] Album pages
- [ ] Better queue management
- [ ] Keyboard shortcuts
- [ ] More personalization
- [ ] Optional local AI music recommendations
- [ ] Accessibility improvements

---

## Contributing

Contributions are welcome.

```bash
git fork https://github.com/harshitethic/BytesMusic
```

Then:

```bash
git checkout -b feature/my-feature
```

Install the dependencies and run the test suite before opening a PR:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

For UI or API changes, also start the app locally and verify the affected flow:

```bash
python3 app.py
```

Make your changes, test them locally, and open a pull request. GitHub Actions runs the unit tests automatically on pushes and pull requests.

Good first contributions include UI improvements, bug fixes, mobile responsiveness, accessibility, search improvements, recommendation logic, documentation, and tests.

---

## Development

Run the server locally:

```bash
py app.py
```

Then open:

```text
http://localhost:8000
```

Before submitting a PR, make sure the app starts, search works, playback works, account functionality remains intact, and no secrets or runtime database files are committed.

### Running tests

The repository uses Python's built-in `unittest` framework. No separate test runner is required.

```bash
python3 -m unittest discover -s tests -v
```

The same command is executed by GitHub Actions for every push and pull request.

---

## License

Released under the [MIT License](LICENSE).

---

## Built by

### @harshitethic

**GitHub:** https://github.com/harshitethic  
**Portfolio:** https://harshitethic.com

---

## Support the project

If BytesMusic is useful to you:

- Star the repository
- Report bugs
- Suggest features
- Submit pull requests
- Share the project

---

<p align="center">
  <strong>BytesMusic</strong><br>
  Open music. Your way.
</p>
