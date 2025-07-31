# MscFinalProject
Repository for Digital Twin for Smart City Project for MSc For Roehampton University
https://github.com/manas-p-pandey/MscFinalProject

Trello Link
https://trello.com/b/gCxlxyuH/msc-project-board


Cloudflare service for tunneling domain to app
----------------------------------------------
install cli
choco install cloudflared

check vesion
cloudflared --version

authenticate with cloudflare account
cloudflared tunnel login

start tunnel
cloudflared tunnel --url http://localhost:8080

gives message if success
Your tunnel is live!

create tunnel with domain
cloudflared tunnel create mscproj

route traffic to tunnel
cloudflared tunnel route dns mscproj manas-mscproj.uk

navigate to directory and create yml
C:\Users\<YOU>\.cloudflared\config.yml:

add below to config.yml

tunnel: mscproj
credentials-file: C:\Users\<YOU>\.cloudflared\[key].json

ingress:
  - hostname: manas-mscproj.uk
    service: http://localhost:8080
  - service: http_status:404

start tunnel
cloudflared tunnel run myapp-tunnel

run tunnel as service
------------------------------------------
# Replace '<YOU>' with your actual Windows username
mkdir "C:\Windows\System32\config\systemprofile\.cloudflared"

copy "C:\Users\<YOU>\.cloudflared\config.yml" "C:\Windows\System32\config\systemprofile\.cloudflared\"
copy "C:\Users\<YOU>\.cloudflared\[key].json" "C:\Windows\System32\config\systemprofile\.cloudflared\"

to install service
cloudflared service install

to start service
net start cloudflared

to stop service
cloudflared service uninstall





