sudo echo hello

git clone https://github.com/tatellos/whisper-stream.git
#sudo apt update
#sudo apt upgrade -y
sudo apt install -y ffmpeg nginx #xorg nvidia-driver-460
#sudo reboot

cd whisper-stream/server
pip install -r requirements.txt
python3 main.py

sudo mkdir /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt

sudo nano /etc/nginx/sites-enabled/default

sudo systemctl reload nginx
python3 main.py
