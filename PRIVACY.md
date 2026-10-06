# Privacy Policy for YoutubeGenteiPlaylist

Last updated: October 2026

## 1. Overview
This Privacy Policy describes how the personal project application "YoutubeGenteiPlaylist" accesses, uses, and protects information when interacting with YouTube and Google APIs.

## 2. Information Collected and Accessed
The application accesses user data solely through the YouTube Data API v3 scopes requested during authentication:
- `https://www.googleapis.com/auth/youtube`
- `https://www.googleapis.com/auth/youtube.force-ssl`
- `https://www.googleapis.com/auth/youtube.readonly`

The application accesses:
- Channel details (channel ID, title)
- Video upload lists
- Playlists created by the user

## 3. How We Use the Information
The accessed data is used strictly for the following purposes:
- Managing and organizing the user's uploaded videos into daily unlisted playlists.
- Updating video privacy settings to unlisted as intended by the channel owner.

## 4. Data Storage and Security
- All authentication credentials and tokens are stored locally on the user's private environment or within private Google Cloud Run service instances.
- No personal user data or Google user credentials are ever transferred, sold, or shared with third parties or external servers.

## 5. User Control and Revocation
Users can revoke the application's access at any time via [Google Security Settings](https://myaccount.google.com/permissions).

## 6. Contact
For questions regarding this privacy policy, please contact:
- Developer Email: getagelessgetageless@gmail.com
