from __future__ import annotations

import asyncio
import os
import sys
from typing import Callable

from config import DEEPGRAM_LANGUAGE, DEEPGRAM_MODEL, DEEPGRAM_RECONNECT_MAX_DELAY
from deepgram import AsyncDeepgramClient
from deepgram.listen.v1.socket_client import AsyncV1SocketClient
from deepgram.listen.v1.types.listen_v1results import ListenV1Results

TranscriptCallback = Callable[[str, bool], None]


class DeepgramTranscriber:
    """
    Streams audio blobs to Deepgram v1 and fires on_transcript for each result.

    Usage:
        transcriber = DeepgramTranscriber(api_key, callback)
        await transcriber.start()          # opens WS, begins listening
        await transcriber.send_audio(blob) # called per browser blob
        await transcriber.stop()           # closes stream cleanly
    """

    def __init__(
        self,
        api_key: str,
        on_transcript: TranscriptCallback,
        on_ready: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        encoding: str | None = None,
        sample_rate: int | None = None,
    ) -> None:
        self._api_key = api_key
        self._on_transcript = on_transcript
        self._on_ready = on_ready
        self._on_error = on_error
        self._encoding = encoding
        self._sample_rate = str(sample_rate) if sample_rate else None
        self._client = AsyncDeepgramClient(api_key=api_key)
        self._connection: AsyncV1SocketClient | None = None
        self._listen_task: asyncio.Task | None = None
        self._ready = asyncio.Event()
        self._stopped = False
        self._reconnect_header: bytes | None = None

    async def start(self) -> None:
        """Open the Deepgram WebSocket and wait until the connection is live."""
        self._ready.clear()
        self._listen_task = asyncio.create_task(self._run())
        await self._ready.wait()

    def set_reconnect_header(self, blob: bytes) -> None:
        """Cache the WebM initialization blob so it can be resent on every reconnect."""
        self._reconnect_header = blob

    async def _run(self) -> None:
        """Background task: hold the WS open, reconnect on timeout/error."""
        delay = 1.0
        is_reconnect = False
        while not self._stopped:
            try:
                async with self._client.listen.v1.connect(
                    model=DEEPGRAM_MODEL,
                    language=DEEPGRAM_LANGUAGE,
                    punctuate="true",
                    interim_results="true",
                    encoding=self._encoding,
                    sample_rate=self._sample_rate,
                ) as conn:
                    # On reconnect: inject the WebM header before accepting live audio.
                    # MediaRecorder only emits the init segment once at the start of a stream;
                    # without it Deepgram cannot parse subsequent cluster data.
                    if is_reconnect and self._reconnect_header is not None:
                        await conn.send_media(self._reconnect_header)
                    is_reconnect = True
                    self._connection = conn  # expose only after header is sent
                    delay = 1.0  # reset backoff on successful connect
                    self._ready.set()
                    if self._on_ready:
                        self._on_ready()
                    async for msg in conn:
                        if not isinstance(msg, ListenV1Results):
                            continue
                        transcript = msg.channel.alternatives[0].transcript if msg.channel.alternatives else ""
                        if not transcript:
                            continue
                        self._on_transcript(transcript, bool(msg.is_final))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                if self._stopped:
                    break
                print(f"[transcriber] error: {exc} — reconnecting in {delay:.0f}s", file=sys.stderr, flush=True)
                if self._on_error:
                    self._on_error(str(exc))
                self._ready.clear()
                self._connection = None
                await asyncio.sleep(delay)
                delay = min(delay * 2, DEEPGRAM_RECONNECT_MAX_DELAY)
        self._connection = None

    async def send_audio(self, blob: bytes) -> None:
        """Forward a raw audio blob to Deepgram."""
        if self._connection is not None:
            try:
                await self._connection.send_media(blob)
            except Exception:
                pass  # connection dropped mid-stream; reconnect loop handles it

    async def stop(self) -> None:
        """Signal end-of-stream to Deepgram and shut down gracefully."""
        self._stopped = True
        if self._connection is not None:
            try:
                await self._connection.send_close_stream()
            except Exception:
                pass
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None


# ---------------------------------------------------------------------------
# TRANS-04 verification: python transcriber.py <audio_file>
# Prints [INTERIM] / [FINAL] lines — final transcripts should appear within
# ~1 second of speech arriving.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.environ.get("DEEPGRAM_API_KEY", "")
    if not api_key:
        print("Error: DEEPGRAM_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <audio_file>", file=sys.stderr)
        print("       python transcriber.py --mic", file=sys.stderr)
        sys.exit(1)

    mic_mode = sys.argv[1] == "--mic"
    audio_path = None if mic_mode else sys.argv[1]

    def _print_transcript(text: str, is_final: bool) -> None:
        label = "[FINAL]  " if is_final else "[INTERIM]"
        print(f"{label} {text}", flush=True)

    async def _main() -> None:
        if mic_mode:
            import sounddevice as sd

            MIC_SAMPLE_RATE = 16000
            MIC_CHANNELS = 1
            MIC_BLOCK = 4096  # ~256ms of audio per chunk

            transcriber = DeepgramTranscriber(
                api_key=api_key,
                on_transcript=_print_transcript,
                encoding="linear16",
                sample_rate=MIC_SAMPLE_RATE,
            )
            await transcriber.start()
            print("[transcriber] connected — speak into your mic (Ctrl+C to stop)", flush=True)

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[bytes] = asyncio.Queue()

            def _sd_callback(indata, frames, time, status):
                loop.call_soon_threadsafe(queue.put_nowait, bytes(indata))

            with sd.RawInputStream(
                samplerate=MIC_SAMPLE_RATE,
                channels=MIC_CHANNELS,
                dtype="int16",
                blocksize=MIC_BLOCK,
                callback=_sd_callback,
            ):
                try:
                    while True:
                        chunk = await queue.get()
                        await transcriber.send_audio(chunk)
                except KeyboardInterrupt:
                    pass

            await transcriber.stop()
        else:
            transcriber = DeepgramTranscriber(api_key=api_key, on_transcript=_print_transcript)
            await transcriber.start()
            print(f"[transcriber] connected — streaming {audio_path}", flush=True)

            with open(audio_path, "rb") as f:
                while chunk := f.read(4096):
                    await transcriber.send_audio(chunk)
                    await asyncio.sleep(0.05)

            await asyncio.sleep(15)
            await transcriber.stop()

        print("[transcriber] done", flush=True)

    asyncio.run(_main())
