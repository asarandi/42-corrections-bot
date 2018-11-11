# 42-corrections-bot
parses your intra page and sends a slack notification (and/or sms) when you have a correction
</br>
### install the prerequisites:
```bash
apt install python3-pip
pip3 install bs4
pip3 install twilio
pip3 install slackclient
```
</br>
### edit the script and add your credentials
</br>

### add crontab 
```bash
crontab -e
```
(adjust folder paths as necessary)
```bash
*/15 * * * * cd /home/ubuntu/corrections; /usr/bin/python3 corrections-bot.py >> execution.log 2>&1
```
</br>

### done

</br>
</br>
</br>

#### correction appears on our intra profile page

![corrections-bot screenshot 1](screenshots/img1.png)
</br>
</br>
#### bot sends a direct message to owner

![corrections-bot screenshot 2](screenshots/img2.png)
</br>
</br>
#### bot sends a group message to owner and correction partner

![corrections-bot screenshot 3](screenshots/img3.png)
</br>
</br>
#### bot sends a direct message to owner

![corrections-bot screenshot 4](screenshots/img4.png)
</br>
</br>
#### bot sends a group message to owner and correction partner

![corrections-bot screenshot 5](screenshots/img5.png)
</br>
</br>
#### bot sends sms message to owner

![corrections-bot screenshot 6](screenshots/img6.png)
</br>
</br>
#### bot sends sms message to owner

![corrections-bot screenshot 7](screenshots/img7.png)
</br>
