# BytesMusic

An open-source YouTube Music client. Search the real YouTube Music public catalog — Hindi, Punjabi, Tamil, Telugu, English and more — through the open-source `ytmusicapi` library. No Google Cloud API key required.

## Features

- **Search** the full YouTube Music public song catalog
- **Play** songs with an embedded YouTube player
- **Queue** with shuffle and repeat controls
- **Accounts** with username, email, and recovery-based password reset
- **History** — tracks your recently played songs
- **Likes** — save your favorite songs
- **Admin Panel** — full platform dashboard for the admin account

## Admin Access

Only the account registered with the email `technoproboizz@gmail.com` receives admin privileges. No other account can become admin.

- Admin panel at `/admin`
- Dashboard with platform-wide stats (unique songs, users, plays, likes, artists)
- 7-day plays chart
- Most played / most liked tables
- User management (view and delete non-admin users)
- Full activity and likes history across all users

## Tech

- **Backend**: Python `http.server`, SQLite
- **Search**: `ytmusicapi` (unauthenticated YouTube Music public search)
- **Frontend**: Vanilla HTML/CSS/JS — no build step
- **Auth**: PBKDF2-SHA256 password hashing with per-user salt

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:8000`.

## Author

**Harshit Ethic**
- [GitHub](https://github.com/harshitethic)
- [Website](https://harshitethic.com)

## License

MIT
