let startButton = document.getElementById("start");
let stopButton = document.getElementById("stop");
let mediaRecorder;
let socket;

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const randomSixDigits = Math.floor(Math.random() * 900000) + 100000;
const socketBaseUrl = protocol + '//' + window.location.host + "/socket/";
statusSocket = new WebSocket(socketBaseUrl + "status");
const timerForError = setTimeout(() => document.getElementById("status").style.display = "inherit", 500)
statusSocket.onmessage = hello => {
    statusSocket.close();
    clearTimeout(timerForError)
    document.getElementById("status").style.display = "none"
}

const socketUrl = socketBaseUrl + randomSixDigits;

startButton.onclick = () => {
    startButton.disabled = true;
    stopButton.disabled = false;
    // Get microphone access
    navigator.mediaDevices.getUserMedia({audio: true})
        .then(stream => {
            mediaRecorder = new MediaRecorder(stream, {
                mimeType: "audio/webm;codecs=opus", bitsPerSecond: 256000
            });
            mediaRecorder.start(1000); // chunk every second

            socket = new WebSocket(socketUrl);

            socket.onmessage = msg => {
                const response = JSON.parse(msg.data)
                const p = document.createElement("p");
                p.textContent = response["commit"]
                document.getElementById("transcription").appendChild(p)
                document.getElementById("tentative").textContent = response["tentative"];
            }

            mediaRecorder.addEventListener('dataavailable', e => {
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
