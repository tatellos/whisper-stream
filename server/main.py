import asyncio
import io
import json
import os
import datetime

import websockets
from whisper_jax import FlaxWhisperPipline
from pydub import AudioSegment

streamed_audio_filename = 'audio.wav'
decompressed_wave = "destination.wav"

# Load AI, then report that it's done and ready
pipeline = FlaxWhisperPipline("openai/whisper-large-v2")
print("READY")

q = asyncio.Queue()
session_store = {
    "example": {
        "websocket": "the websocket instance that spawned the session",
        "audio_offset": "the time in ms from where to start transcribing",
        "ogg_buffer": "an ever-growing ogg bytestream that is the result of the stream from the browser",
        "wave_filename": "some name",
        "ConnectionClosed": "False"
    }
}


async def websocket_handler(websocket, path):
    print(path)
    if path == "/socket/status":
        await websocket.send("hello")
        return

    session = get_session_from_path(path)
    print(session)
    if session is None: return

    session_store[session] = {
        "websocket": websocket,
        "audio_offset": 0,
        "ogg_buffer": b'',
        "wave_filename": session + streamed_audio_filename,
        "ConnectionClosed": False
    }

    listener_task = asyncio.create_task(listen_for_messages(session))

    print("Starting tasks", path)
    done, pending = await asyncio.wait(
        [listener_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    print("cleaning up")
    for task in pending:
        task.cancel()
    if os.path.exists(session_store[session]["wave_filename"]):
        os.remove(session_store[session]["wave_filename"])
    del session_store[session]


async def listen_for_messages(session):
    try:
        websocket = session_store[session]["websocket"]
        async for message in websocket:
            # TODO when messages build up, the queue is triggered on the first message already, but it would be more
            # efficient to trigger it only after the last message. Although this isn't a big problem, since all
            # messages are written to the session store buffer before the queue is emptied next.
            try:
                if session not in session_store or session_store[session]["ConnectionClosed"]: return

                if len(message) > 2:
                    session_store[session]["ogg_buffer"] += message
                    if q.empty():
                        # TODO this might mean that some users never get their voice heard. probably most easily solved by having a queue per session
                        # it distributes the transcription randomly. But the same would happen with different queues.
                        await q.put(session)
                        print("Triggered Queue", session)
            except Exception as e:
                print("Exception during message handling, continuing", e)
                continue
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")
        if session in session_store:
            session_store[session]["ConnectionClosed"] = True


async def send_messages():
    while True:
        try:
            session = await q.get()
            if session not in session_store or session_store[session]["ConnectionClosed"]: continue

            wave_filename = session_store[session]["wave_filename"]
            try:
                ogg_file = io.BytesIO(session_store[session]["ogg_buffer"])
                wave_audio = AudioSegment.from_file(ogg_file)
            except Exception as e:
                print("Error converting to wav", e)
                continue

            duration = save_wave_file_to_transcribe(session, wave_audio, wave_filename)

            try:
                # TODO this is a synchronous call. It blocks everything else, e.g. message reception (but they are
                # buffered)
                translation = pipeline(wave_filename, task="translate", return_timestamps=True)
            except Exception as e:
                print("Error transcribing", e)
                continue

            # keep only segments that are not longer/later than the duration of the file
            segments = [segment for segment in translation["chunks"] if segment["timestamp"][1] <= (duration / 1000) + 1]

            result = None
            if len(segments) > 1:
                # Commit to all segments except the last one
                result = " ".join([x["text"] for x in segments[:-1]])
                print("Sending result", result)
                session_store[session]["audio_offset"] += min(segments[-2]["timestamp"][1], segments[-1]["timestamp"][0]) * 1000

            if len(segments) > 0:
                # Add the last segment as a "maybe"
                response = {
                    "tentative": segments[-1]["text"]
                }
                if result is not None:
                    response["commit"] = result

                await send_response(response, session)

        except Exception as e:
            print("Exception during transcription loop, continuing.", e)
            continue


async def send_response(response, session):
    try:
        await session_store[session]["websocket"].send(json.dumps(response))
    except websockets.exceptions.ConnectionClosed:
        print("Closed connection: Session", session)
        if session in session_store:
            session_store[session]["ConnectionClosed"] = True


def save_wave_file_to_transcribe(session, wave_audio, wave_filename) -> int:
    start_time = session_store[session]["audio_offset"]
    duration = len(wave_audio) - start_time
    wave_audio[start_time:].export(wave_filename, format="wav")
    print(datetime.datetime.now(), " wrote to ", wave_filename)

    filesize = os.path.getsize(wave_filename)
    print("Transcribing filesize", filesize, "duration", duration, "ogg length is",
          len(session_store[session]["ogg_buffer"]))

    return duration


def get_session_from_path(path):
    # strip "/socket/" from the start
    session = path[8:]
    # Ensure that the session is six digits
    if len(session) != 6:
        return None
    try:
        int(session)
    except ValueError:
        return None

    return session


if __name__ == "__main__":
    server = "0.0.0.0"
    port = 8000
    start_server = websockets.serve(websocket_handler, server, port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_until_complete(send_messages())
    asyncio.get_event_loop().run_forever()
    print("listening on ", server, port)
