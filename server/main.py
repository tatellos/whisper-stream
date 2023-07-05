# main TODO: fix ogg / wave shit. try without compression somehow?
# parallel users somehow break each other, and it's not clear how:
# probably because
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
audio_model = whisper.load_model("tiny")
print("READY")


async def websocket_handler(websocket, path):
    print(path)
    session = get_session_from_path(path)
    print(session)
    if session is None: return

    q = asyncio.Queue()
    listener_task = asyncio.create_task(listen_for_messages(websocket, q, session))
    sender_task = asyncio.create_task(send_messages(websocket, q))

    print("Starting tasks", path)
    done, pending = await asyncio.wait(
        [listener_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    print("cleaning up")
    for task in pending:
        task.cancel()

async def listen_for_messages(websocket, q, session):
    ogg_bytes = b'' # TODO This ogg file grows forever
    try:
        async for message in websocket:
            if len(message) > 2:
                if message == "reset":
                    # TODO the frontend could send these reset messages every like 3 minutes
                    ogg_bytes = b''
                    continue
                ogg_bytes += message
                ogg_file = io.BytesIO(ogg_bytes)
                wave_audio = AudioSegment.from_file(ogg_file)
                wave_filename = session + streamed_audio_filename
                wave_audio.export(wave_filename, format="wav")
                print(datetime.datetime.now(), " wrote to ", wave_filename)
                if q.empty():
                    await q.put(session)
                    print("Triggered Queue", session)
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")


async def send_messages(websocket, q):
    start_time = 0 # TODO the start time is mixed between sessions. Very bad. XXX
    while True:
        session = await q.get()
        wave_filename = session + streamed_audio_filename
        duration = len(AudioSegment.from_wav(wave_filename)) - start_time
        filesize = os.path.getsize(wave_filename)
        print("Transcribing filesize", filesize, "duration", duration)
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
            start_time += min(segments[-2]["end"], segments[-1]["start"]) * 1000
            # print("New start time:", start_time)
        if len(segments) > 0:
            response = {
                "tentative": segments[-1]["text"]
            }
            if result is not None:
                response["commit"] = result
            await websocket.send(json.dumps(response))


if __name__ == "__main__":
    server = "localhost"
    port = 8000
    start_server = websockets.serve(websocket_handler, server, port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
    print("listening on ", server, port)
