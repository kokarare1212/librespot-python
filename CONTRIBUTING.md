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
