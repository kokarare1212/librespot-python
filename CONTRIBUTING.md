# Contributing

## What this library is

- A headless Spotify client, allowing you to **authenticate and retrieve a decrypted audio stream for any track**.
- *Not* a standalone audio player: the **provided stream must be piped to another application** (like `ffplay`) or handled by a server to be played.

## Environment setup

### Prerequisites
- Python 3.10+

### Install runtime packages

```sh
pip install -r requirements.txt
```

### Install protoc

> This step is **only needed if you're changing any `.proto` serialization schema files**,
> which will subsequently require using the protoc compiler to generate updated versions of 
> the `*_pb2.py` Python stubs that implement serialization/deserialization for those schemas.

- Go to the [protobuf release matching the version pinned in `requirements.txt`](https://github.com/protocolbuffers/protobuf/releases/tag/v3.20.1).
- Download and install the `protoc-*.zip` file meant for your platform.

After modifying the `.proto` files you need to, **make sure to follow [these steps](#protocol-buffer-generation) to regenerate the Python stubs**.

## Protocol buffer generation

> These steps are only necessary after changing `.proto` files.

- From the repository root, conveniently recompile all `.proto` schema files with this command:

    ```bash
    find proto -name "*.proto" | xargs protoc -I=proto --python_out=librespot/proto
    ```

- Alternatively, to recompile a single file (e.g. `proto/metadata.proto`), run:

    ```bash
    protoc -I=proto --python_out=librespot/proto proto/metadata.proto
    ```

- Commit both the source `.proto` and the regenerated Python output **together** so they can
be compared easily.

## Architecture

The main components are:

- **`Session` class** *(entrypoint)*

    - `Session.Builder` is used to configure and create a session, via one of:

        - username/password
        - stored credentials
        - OAuth
 
    - An active session is **required** for all other operations.

- **`ApiClient` class**

    - A high-level client for making standard HTTPS requests to Spotify's Web API endpoints (e.g., `https://spclient.wg.spotify.com`).
    - Accessed via `session.api()`, it provides convenient methods like `get_metadata_4_track()` and handles client tokens automatically.

- **`MercuryClient` class**

    - The low-level client for Spotify's proprietary `mercury` protocol, which uses `hm://` URIs.
    - Accessed via `session.mercury()`, it handles sending and receiving messages over the main session connection for metadata lookups and subscriptions that are not available via the standard Web API.

- **`DealerClient` class**

    - Manages the persistent WebSocket (`wss://`) connection to Spotify's `dealer` service.
    - Accessed via `session.dealer()`, it listens for and dispatches real-time, asynchronous JSON-based events, such as remote player state changes or notifications from other connected devices.

- **`Session.Receiver` thread**

    - Spawned after authentication to read every encrypted packet coming from the access point.
    - Routes decoded commands to subsystems (`MercuryClient`, `AudioKeyManager`, `ChannelManager`, etc.) and responds to keep-alive pings to hold the session open.

- **Metadata types**

    - The `librespot.metadata` module provides typed identifiers (`TrackId`, `AlbumId`, `PlaylistId`, `EpisodeId`, etc.) used to reference Spotify content throughout the API.
    - They are constructed from Spotify identifiers, typically using one of the following methods:

        - `from_uri()`: For all ID types.
        - `from_base62()`: For most ID types (e.g., tracks, albums, artists).

- **`PlayableContentFeeder` class**

    - Retrieves audio streams; is accessed via `session.content_feeder()`.
    - `load(playable_id, audio_quality_picker, preload, halt_listener)`:

        - Accepts:

            - a `TrackId` or `EpisodeId` (any `PlayableId`)
            - an `AudioQualityPicker`
            - a `preload` flag
            - an optional `HaltListener` callback (pass `None` if unneeded).

        - Returns a `LoadedStream` that contains the decrypted stream together with:

            - track/episode metadata
            - normalization data
            - transfer metrics

- **`audio` module**
    
    - Contains tools for format selection, quality management, streaming, and decryption.
    - `VorbisOnlyAudioQuality` and `LosslessOnlyAudioQuality` choose the best matching `Metadata.AudioFile` for a preferred container/quality combination.
    - `CdnManager` acquires and refreshes signed CDN URLs, feeding a `Streamer` that decrypts chunks on the fly while staying seekable.

- **`AudioKeyManager` and `ChannelManager`**

    - Handle the low-level transport for protected audio: `AudioKeyManager` requests AES keys, and `ChannelManager` can stream encrypted chunks directly from the access point when CDN delivery is unavailable.
    - Both are driven transparently by `PlayableContentFeeder`/`CdnManager`, so callers only interact with the decrypted `LoadedStream`.

- **`EventService` class**

    - Asynchronous publisher that emits telemetry (e.g., fetch metrics, playback events) to `hm://event-service/v1/events` via Mercury.
    - Accessible through `session.event_service()` for consumers that need to forward custom events.

- **`TokenProvider` class**

    - Caches Login5 access tokens per scope, refreshing them proactively as they near expiry.
    - Used by `ApiClient` to supply the correct `Authorization` headers for Spotify Web API calls.

- **`SearchManager` class**

    - High-level wrapper around `hm://searchview/km/v4/search/...` requests sent over Mercury.
    - Fills in username, locale, and country defaults from the current session before dispatching the call.

- **OAuth tokens for Spotify Web API**

    - Can be obtained via `session.tokens().get(scope)`
    - Enable authenticated API calls for operations like search, playlist management, and user data access
