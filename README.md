# MscFinalProject
Repository for Digital Twin for Smart City Project for MSc For Roehampton University
https://github.com/manas-p-pandey/MscFinalProject

Trello Link
https://trello.com/b/gCxlxyuH/msc-project-board


Cloudflare service for tunneling domain to app
----------------------------------------------
!! Please open power shell in elevated mode for successfully hosting app running in docker container !!
install cli
choco install cloudflared

check vesion
cloudflared --version

authenticate with cloudflare account
cloudflared tunnel login

start tunnel to test
cloudflared tunnel --url http://localhost:8080

gives message if success
Your tunnel is live!

create tunnel with domain
cloudflared tunnel create mscproj

route traffic to tunnel
cloudflared tunnel route dns mscproj manas-mscproj.uk

navigate to directory and create yml
C:\Users\<user>\.cloudflared\config.yml:

add below to config.yml

tunnel: mscproj
credentials-file: C:\Users\<user>\.cloudflared\[key].json

ingress:
  - hostname: manas-mscproj.uk
    service: http://localhost:8080
  - service: http_status:404

start tunnel
cloudflared tunnel run mscproj

run tunnel as service
------------------------------------------
create .bat file at C:\Users\<user>\.cloudflared\ with below contents
cloudflared tunnel run mscproj

you should be able to access the app through web https://manas-mscproj.uk

create a [run.bat] file with command to run cloudflare tunnel
@echo off
cloudflared tunnel run mscproj

if the bat is run it should start tunnel and serve the pages through link

create windows service to host app on web
------------------------------------------
download and install nssm tool from https://nssm.cc/download

after download extract the zip folder and navigate to path where nssm.exe is located in command prompt

enter the command below to open nssm gui
nssm install DigitalTwinWebHost

in gui fill in details as below for application tab
path=C:\Windows\System32\cmd.exe
startup directory = C:\Users\<user>\.cloudflared
arguments= /c "C:\Users\manas\.cloudflared\run.bat"

check suitable options in the other tabs as needed or keep the default

click on install button and wait for success message.

run from command prompt in admin modesc start DigitalTwinWebHost
sc start DigitalTwinWebHost

once the service is started you should be able to see the app accessible from link manas-mscproj.uk

make sure before starting the service the app runs and listens request on https://localhost:8080

to remove serice use nssm and follow instrauctions
nssm remove DigitalTwinWebHost confirm









