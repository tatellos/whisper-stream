let startButton = document.getElementById("start");
let stopButton = document.getElementById("stop");
let mediaRecorder;
let socket;

startButton.onclick = () => {
    startButton.disabled = true;
    stopButton.disabled = false;
    // Get microphone access
    navigator.mediaDevices.getUserMedia({audio: true})
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: "audio/webm;codecs=opus",
                bitsPerSecond: 256000
            });
            mediaRecorder.start(1000); // commit every second

            socket = new WebSocket('ws://localhost:8000');

            socket.onmessage = msg => {
                const response = JSON.parse(msg.data)
                const p = document.createElement("p");
                p.textContent = response["commit"]
                document.getElementById("transcription").appendChild(p)
                document.getElementById("tentative").textContent = response["tentative"];
            }

            mediaRecorder.addEventListener('dataavailable', e => {
                // This should be called roughly every second, by the mediaRecorder
                socket.send(e.data)
            });

            console.log("Streaming audio to user with bitrate", mediaRecorder.audioBitsPerSecond)
            console.log("Streaming audio to user with mimeType", mediaRecorder.mimeType)
        })
        .catch(err => {
            console.log('Unable to access mic', err);
        });
}

stopButton.onclick = () => {
    startButton.disabled = false;
    stopButton.disabled = true;
    mediaRecorder.stop();
    socket.close();
}
