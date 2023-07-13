# TODO Ideas: Reset the buffer. Build a simple index for frames, to make sure they are processed in correct order
import asyncio
import io
import json
import os
import datetime

import websockets
import whisper
from pydub import AudioSegment

streamed_audio_filename = 'audio.wav'
decompressed_wave = "destination.wav"

# Load AI, then report that it's done and ready
audio_model = whisper.load_model("tiny")
print("READY")

q = asyncio.Queue()
session_store = {
    "example": {
        "websocket": "the websocket instance that spawned the session",
        "skip_wav_seconds": "the time in ms from where to start transcribing",
        "ogg_buffer": {
            0: ["a dict of arrays. Keys correspond to separate OGG files, e.g. minutes recorded (restarting "
                "the recorder every minute)"],
            1: ["Elements in the inner arrays are chunks of ogg audio."],
            2: ["They have an index so that out-of-order packets are transcribed in the correct order."]
        },
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
        "skip_wav_seconds": 0,
        "ogg_buffer": dict(),
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
        async for rawMessage in websocket:
            if session_store[session]["ConnectionClosed"]: return

            message = json.loads(rawMessage)
            chunk = message["chunk"]
            ogg_buffer = session_store[session]["ogg_buffer"]
            if chunk not in ogg_buffer:
                ogg_buffer[chunk] = []
            ogg_buffer[chunk].append(message)

            if q.empty():
                # TODO this might mean that some users never get their voice heard. probably most easily solved by having a queue per session
                # it distributes the transcription randomly. But the same would happen with different queues.
                await q.put(session)
                print("Triggered Queue", session)
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")
        if session in session_store:
            session_store[session]["ConnectionClosed"] = True


async def send_messages():
    while True:
        session = await q.get()
        if session_store[session]["ConnectionClosed"]: return

        while
        duration, filesize, wave_filename = await export_wave_file_from_smart_start(session)
        print("Transcribing filesize", filesize, "duration", duration, "ogg length is",
              len(session_store[session]["ogg_buffer"]))
        try:
            translation = audio_model.transcribe(wave_filename, language="de", task="translate")
        except Exception as e:
            print("Error transcribing", e)
            continue
        segments = translation["segments"]
        # remove segments that are longer/later than the duration of the file
        segments = [segment for segment in segments if segment["end"] <= (duration / 1000) + 1]
        # print(len(segments), "segments: \n", print_segments(segments))
        result = None
        if len(segments) > 1:
            result = " ".join([x["text"] for x in segments[:-1]])
            print("Sending result", result)
            session_store[session]["skip_wav_seconds"] += min(segments[-2]["end"], segments[-1]["start"]) * 1000
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
                if session in session_store:
                    session_store[session]["ConnectionClosed"] = True


async def export_wave_file_from_smart_start(session):
    ogg_buffer = session_store[session]["ogg_buffer"]
    ogg_files = list(ogg_buffer.keys())
    if len(ogg_files) > 2:
        # TODO change to IF to gcheck for the start time istead!
        del ogg_buffer[ogg_files[0]]

    # TODO need to concat the bytestrings in the next lines
    ogg_file_a = io.BytesIO(ogg_buffer[ogg_files[-2]])
    ogg_file_b = io.BytesIO(ogg_buffer[ogg_files[-1]])

    wave_audio_a = AudioSegment.from_file(ogg_file_a)
    wave_audio_b = AudioSegment.from_file(ogg_file_b)


    start_time = session_store[session]["skip_wav_seconds"]
    duration = len(wave_audio) - start_time

    wave_filename = session_store[session]["wave_filename"]
    wave_audio[start_time:].export(wave_filename, format="wav")
    print(datetime.datetime.now(), " wrote to ", wave_filename)
    filesize = os.path.getsize(wave_filename)

    return duration, filesize, wave_filename


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


def print_segments(segments):
    return "\n".join(
        [" ".join(["          ", str(x["start"]), str(x["end"]), str(x["text"])]) for x in segments]
    )


if __name__ == "__main__":
    server = "0.0.0.0"
    port = 8000
    start_server = websockets.serve(websocket_handler, server, port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_until_complete(send_messages())
    asyncio.get_event_loop().run_forever()
    print("listening on ", server, port)
