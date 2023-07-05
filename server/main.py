import asyncio
import io
import json
import os
import datetime

import websockets
import whisper
from pydub import AudioSegment

from server.utils import get_session_from_path

streamed_audio_filename = 'audio.wav'
decompressed_wave = "destination.wav"

# Load AI, then report that it's done and ready
audio_model = whisper.load_model("medium")
print("READY")

q = asyncio.Queue()
session_store = {
    "example": {
        "websocket": "the websocket instance that spawned the session",
        "audio_offset": "the time in ms from where to start transcribing",
        "ogg_buffer": "an ever-growing ogg bytestream that is the result of the stream from the browser"
    }
}


async def websocket_handler(websocket, path):
    print(path)
    session = get_session_from_path(path)
    print(session)
    if session is None: return

    session_store[session] = {
        "websocket": websocket,
        "audio_offset": 0,
        "ogg_buffer": b'',
        "wave_filename": session + streamed_audio_filename
    }

    listener_task = asyncio.create_task(listen_for_messages(websocket, session))

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


async def listen_for_messages(websocket, session):
    try:
        async for message in websocket:
            if len(message) > 2:
                if message == "reset":
                    # TODO the frontend could send these reset messages every like 3 minutes
                    session_store[session]["ogg_buffer"] = b''
                    continue
                session_store[session]["ogg_buffer"] += message
                if q.empty():
                    # TODO this might mean that some users never get their voice heard. probably most easily solved by having a queue per session
                    # it distributes the transcription randomly. But the same would happen with different queues.
                    await q.put(session)
                    print("Triggered Queue", session)
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")


async def send_messages():
    while True:
        session = await q.get()
        wave_filename = session_store[session]["wave_filename"]
        ogg_file = io.BytesIO(session_store[session]["ogg_buffer"])

        wave_audio = AudioSegment.from_file(ogg_file)
        start_time = session_store[session]["audio_offset"]
        duration = len(wave_audio) - start_time
        wave_audio[start_time:].export(wave_filename, format="wav")
        print(datetime.datetime.now(), " wrote to ", wave_filename)

        filesize = os.path.getsize(wave_filename)
        print("Transcribing filesize", filesize, "duration", duration, "ogg length is",
              len(session_store[session]["ogg_buffer"]))
        try:
            translation = audio_model.transcribe(wave_filename, language="de", task="translate")
        except Exception as e:
            print("Error transcribing", e)
            continue
        segments = translation["segments"]
        # remove segments that are longer/later than the duration of the file
        segments = [segment for segment in segments if segment["end"] <= duration / 1000]
        # print(len(segments), "segments: \n", print_segments(segments))
        result = None
        if len(segments) > 1:
            result = " ".join([x["text"] for x in segments[:-1]])
            print("Sending result", result)
            session_store[session]["audio_offset"] += min(segments[-2]["end"], segments[-1]["start"]) * 1000
            # print("New start time:", start_time)
        if len(segments) > 0:
            response = {
                "tentative": segments[-1]["text"]
            }
            if result is not None:
                response["commit"] = result
            try:
                await session_store[session]["websocket"].send(json.dumps(response))
            except websockets.exceptions.ConnectionClosed:
                print("Closed connection: Session", session)


if __name__ == "__main__":
    server = "localhost"
    port = 8000
    start_server = websockets.serve(websocket_handler, server, port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_until_complete(send_messages())
    asyncio.get_event_loop().run_forever()
    print("listening on ", server, port)
