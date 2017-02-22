import socket
import requests
import re
import time
import zmq
import sys

from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw

channel = sys.argv[1]
ircport = sys.argv[2]

ircname = 'XXXXXXX'
ircauth = 'oauth:XXXXXXX'
headers = {'Client-ID': 'XXXXXXX'}

zmqcont = zmq.Context()
zmqsock = zmqcont.socket(zmq.PAIR)
zmqsock.bind('tcp://*:' + port)

emotes = []
badges = []

# update twitch channel emote database
twitch = requests.get(
    "https://api.twitch.tv/kraken/chat/" +
    channel +
    '/emoticons',
    headers=headers
)

assert twitch.status_code == 200, 'failed retrieving twitch emotes:\n' + json.dumps(twitch.json(), indent=4)

for emote in twitch.json()['emoticons']:
    emotes.append( (emote['regex'], emote['url'], 'png') )

# update twitch channel badge database
twitch = requests.get(
    "https://api.twitch.tv/kraken/channels/" +
    channel,
    headers=headers
)

assert twitch.status_code == 200, 'failed retrieving twitch channel id:\n' + json.dumps(twitch.json(), indent=4)

id = twitch.json()['_id']

twitch = requests.get(
    "https://badges.twitch.tv/v1/badges/channels/" +
    str(id) +
    '/display',
    headers=headers
)

assert twitch.status_code == 200, 'failed retrieving twitch channel badges:\n' + json.dumps(twitch.json(), indent=4)

for name, data in twitch.json()['badge_sets'].items():
    for version in data:
        badges.append((
            name + '_' + version,
            version['image_url_1x'],
            'png'
        ))

# update twitch global emote database
twitch = requests.get(
    "https://badges.twitch.tv/v1/badges/global/display",
    headers=headers
)

assert twitch.status_code == 200, 'failed retrieving twitch global badges:\n' + json.dumps(twitch.json(), indent=4)

for name, data in twitch.json()['badge_sets'].items():
    for version in data:
        badges.append((
            name + '_' + version,
            version['image_url_1x'],
            'png'
        ))

# update bttv channel emote database
bttv = requests.get(
    "https://api.betterttv.net/2/channels/" +
    channel
)

assert bttv.status_code == 200, 'failed retrieving channel bttv emotes:\n' + json.dumps(bttv.json(), indent=4)

for emote in bttv.json()['emotes']:
    emotez.append( (
        emote['code'],
        'https://cdn.betterttv.net/emote/' + emote['id'] + '/1x',
        emote['imageType']
    ) )

# update bttv global emote database
bttv = requests.get("https://api.betterttv.net/2/emotes")

assert bttv.status_code == 200, 'failed retrieving channel bttv emotes:\n' + json.dumps(bttv.json(), indent=4)

for emote in bttv.json()['emotes']:
    emotez.append( (
        emote['code'],
        'https://cdn.betterttv.net/emote/' + emote['id'] + '/1x',
        emote['imageType']
    ) )

# save updates
for emote in emotes:
    name, url, type = emote
    
    if os.path.isfile('emotes/' + name + '.' + type): continue
    
    while True:
        image = requests.get(url)
        
        if image.status_code == 200: break
        else: time.sleep(5)
    
    try:
        with open('emotes/' + name + '.' + type, 'w') as file:
            file.write(image)
    
    except:
        print 'emote has weird name:', name

for badge in badges:
    name, url, type = badge
    
    if os.path.isfile('badges/' + name + '.' + type): continue
    
    while True:
        image = requests.get(url)
        
        if image.status_code == 200: break
        else: time.sleep(5)
    
    try:
        with open('badges/' + name + '.' + type, 'w') as file:
            file.write(image)
    
    except:
        print 'badge has weird name:', name

# load regexes
emotes = {emote[:-4]: emote for emote in os.listdir('emotes/')}

emotes['B)'] = 'B-?\).png'
emotes[':z'] = '\:-?[z|Z|\|].png'
emotes[':)'] = '\:-?\).png'
emotes[':('] = '\:-?\(.png'
emotes[':P'] = '\:-?(p|P).png'
emotes[':p'] = '\:-?(p|P).png'
emotes[';P'] = '\;-?(p|P).png'
emotes[';p'] = '\;-?(p|P).png'
emotes['<3'] = '\&lt\;3.png'
emotes[';)'] = '\;-?\).png'
emotes['R)'] = 'R-?\).png'
emotes[':D'] = '\:-?D.png'
emotes[':O'] = '\:-?(o|O).png'
emotes['><'] = '\&gt\;\(.png'
emotes['O.o'] = '[oO](_|\.)[oO].png'

badges = {badge[:-4].replace('-', '/'): badge for badge in os.listdir('badges/')}

# tell renderer irc worker is ready
print 'ready'

# turn text into an image array
def string_image(string, bold=False, color='white'):
    if bold: font = ImageFont.truetype('ArialBold.ttf', 13)
    else:    font = ImageFont.truetype('Arial.ttf', 13)
    
    img = Image.new('RGB', (1, 1))
    drw = ImageDraw.Draw(img)
    w,h = drw.textsize(string, font)

    img = Image.new('RGB', (w,h), 'black')
    drw = ImageDraw.Draw(img)
    drw.text((0,0), string, fill=colour, font=font)
    
    return numpy.array(img)

# stick rendered element into image
def render_this(image, element, start):
    h,w,c = element.shape
    
    if h > 30:
        d = (h-30)/2
        image[:, start:start+w, :] = element[h-30-d:h-d,:,:]
    else:
        d = (30-h)/2
        image[30-h-d:30-d, start:start+w, :] = elements
    
    return image

# render chat message
def render(message):
    lines = [numpy.zeros((30,100,3), dtype='unit8')]
    image = lines[-1]
    start = 1
    
    badge = re.search(r'(?<=@badges=).+(?=;color)', message)
    color = re.search(r'(?<=mod=)\d(?=;room)'     , message)
    uname = re.search(r'(?<=color=).+(?=;display)', message)
    words = re.search(r'(?<=@).+(?=\.tmi\.)'      , message)
    
    # render badges
    for badge in re.findall(r'\w+/\d+', badge):
        badge = numpy.array(Image(badges[badge]))
        image = render_this(image, badge, start)
        start+= w + 2
    
    # render username
    uname = string_image(uname + ':', bold=True, color=color)
    image = render_this(image, uname, start)
    start = start + w + 4
    
    # render text and emotes
    for word in words.split():
        if word in emotes:
            word = emotes[word]
            word = Image(word)
            word = numpy.array(word)
        else word = string_image(word)
        
        h,w,c = word.shape
        
        if start+w+1 > 100:
            lines+= [numpy.zeros((30,100,3), dtype='unit8')]
            image = lines[-1]
            start = 1
        
        image = render_this(image, word, start)
        start = start + w + 4
    
    return numpy.concatenate(lines)

# irc loop
while True:
    
    try:
        ircSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ircServ = 'irc.twitch.tv'
        ircchan = '#' + channel
        
        ircSock.connect((ircServ, 6667))
        ircSock.send(str('PASS ' + ircauth + '\r\n').encode('UTF-8'))
        ircSock.send(str('NICK ' + ircname + '\r\n').encode('UTF-8'))
        ircSock.send(str('JOIN ' + ircchan + '\r\n').encode('UTF-8'))
        ircSock.send(str('CAP REQ :twitch.tv/tags :twitch.tv/commands\r\n').encode('UTF-8'))
        
        linesplit = re.compile(b'\r?\n')
        ircBuffer = b''
        
        while True:
            
            ircBuffer+= ircSock.recv(1024)
            messages  = linesplit.split(ircBuffer)
            ircBuffer = messages.pop()
            
            for message in messages:
                if message.startswith('PING'):
                    ircSock.send(str('PONG :tmi.twitch.tv\r\n').encode('UTF-8'))
                
                zmqsock.send(render(message).tostring())
    
    except Exception as e:
        print 'connection error to %s\'s irc:\n%s' % (channel,str(e))
    
    time.sleep(5)