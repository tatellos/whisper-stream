import asyncio
import json
import os

import websockets
import whisper
from pydub import AudioSegment

streamed_audio = 'audio.ogg'
if os.path.exists(streamed_audio):
    os.remove(streamed_audio)
decompressed_wave = "destination.wav"
if os.path.exists(decompressed_wave):
    os.remove(decompressed_wave)

audio_model = whisper.load_model("tiny")

print("READY")


async def websocket_handler(websocket, path):
    q = asyncio.Queue()
    listener_task = asyncio.create_task(listen_for_messages(websocket, q))
    sender_task = asyncio.create_task(send_messages(websocket, q))

    print("Starting tasks")
    done, pending = await asyncio.wait(
        [listener_task, sender_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    print("cleaning up")
    for task in pending:
        task.cancel()


async def listen_for_messages(websocket, q):
    try:
        async for message in websocket:
            print(f"Received message: {message[:10]}...")
            if len(message) > 5:
                print("appending x bytes to file", len(message))
                with open(streamed_audio, 'ab') as file:
                    file.write(message)
                await q.put(streamed_audio)
                print("Triggered Queue")
    except websockets.exceptions.ConnectionClosed:
        print("ConnectionClosed")


async def send_messages(websocket, q):
    start_time = 0
    while True:
        if q.empty():
            fname = await q.get()
        while not q.empty():
            fname = await q.get()
        print("Converting audio")
        all_sound = AudioSegment.from_file(fname, format="webm", codec="opus")
        print("Ogg filesize", len(all_sound))
        duration = len(all_sound) - start_time
        all_sound[start_time:].export(decompressed_wave, format="wav")
        print("Finished wav audio")

        filesize = os.path.getsize(decompressed_wave)
        print("Transcribing filesize", filesize)
        translation = audio_model.transcribe(decompressed_wave, language="de", task="translate")
        segments = translation["segments"]
        # remove segments that are longer/later than the duration of the file
        segments = [segment for segment in segments if segment["end"] <= duration / 1000]
        print(len(segments), "segments: \n", printSegments(segments))
        result = None
        if len(segments) > 1:
            result = " ".join([x["text"] for x in segments[:-1]])
            print("Sending result", result)
            start_time += min(segments[-2]["end"], segments[-1]["start"]) * 1000
            print("New start time:", start_time)
        if len(segments) > 0:
            response = {
                "tentative": segments[-1]["text"]
            }
            if result is not None:
                response["commit"] = result
            await websocket.send(json.dumps(response))


def printSegments(segments):
    return "\n".join(
        [" ".join(["          ", str(x["start"]), str(x["end"]), str(x["text"])]) for x in segments]
    )


# Start websocket server on port 8000
if __name__ == "__main__":
    start_server = websockets.serve(websocket_handler, "localhost", 8000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
