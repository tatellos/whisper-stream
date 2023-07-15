sudo echo hello

git clone https://github.com/tatellos/whisper-stream.git

### with flax
#downlaod flax first
sudo apt install libcudnn8=8.9.3.28-1+cuda12.1

#sudo apt update
#sudo apt upgrade -y
sudo apt install -y ffmpeg #nginx xorg nvidia-driver-460
#sudo reboot

cd whisper-stream/server
pip install --upgrade pip
pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
pip install -r requirements.txt
#wget http://arens.ma/static/large-v2.pt
#mv large-v2.pt ~/.cache/whisper/
python3 main.py

sudo mkdir /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt

sudo nano /etc/nginx/sites-enabled/default

sudo systemctl reload nginx
python3 main.py
