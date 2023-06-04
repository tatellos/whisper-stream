import asyncio
import os

import websockets
import whisper

audio_model = whisper.load_model("tiny")

bytesToSave = b""
filename = 'audio.ogg'

async def websocket_handler(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        if len(message) > 5:
            print("appending to file")
            with open(filename, 'ab') as file:
                file.write(message)

            # result = audio_model.transcribe(filename, language="en", task="transcribe")
            await websocket.send('result["text"]')


# Start websocket server on port 8000
if __name__ == "__main__":
    start_server = websockets.serve(websocket_handler, "localhost", 8000)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
