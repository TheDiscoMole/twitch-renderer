import requests
import json
import time
import os
import zmq
import subprocess
import numpy

port = 13370
headers = {'Client-ID': 'XXXXXXX'}
context = zmq.Conext()

class Renderer:
    
    def __init__(self, channel, video=True, audio=True, chat=True, flush=True):
        self.channel = channel
        
        self.video = video
        self.audio = audio
        self.chat  = chat
        self.flush = flush
        
        self.port, port = port, port + 10
    
    def start(self):
        ffmpeg = []
        
        if self.video:
            
            ffmpeg += ['-map', '0:v']
            ffmpeg += ['-f', 'image2pipe']
            ffmpeg += ['-pix_fmt', 'rgb24']
            ffmpeg += ['-framerate', '30']
            ffmpeg += ['-vcodec', 'rawvideo']
            ffmpeg += ['http://localhost:%d' % self.port + 0]
            
            self.video = zmq.socket(zmq.STREAM)
            self.video.bind('tcp://*:%d' % self.port + 0)
        
        if self.audio:
            
            ffmpeg += ['-map', '0:a']
            ffmpeg += ['-f', 's16le']
            ffmpeg += ['-ac', '2']
            ffmpeg += ['-ar', '%d' % (44100 / 30)]
            ffmpeg += ['-acodec', 'pcm_s16le']
            ffmpeg += ['http://localhost:%d' % self.port + 1]
            
            self.audio = zmq.socket(zmq.STREAM)
            self.audio.bind('tcp://*:%d' % self.port + 1)
        
        if self.video or self.audio
            
            self.ffmpeg = subprocess.call([
                'ffmpeg',
                '-i', self.__hls__(),
                '-loglevel', 'error'
            ] += ffmpeg )
        
        if self.chat:
            
            self.irc = subprocess.Popen([
                'python', 'irc.py', channel, str(self.port + 2)
            ], stdout=subprocess.PIPE)
            
            assert self.irc.stdout.readline() == 'ready', 'error initialising irc worker'
            
            self.chat = zmq.socket(zmq.PAIR)
            self.chat.bind('tcp://*:%d' % self.port + 2)
            
            self.chat_frame = numpy.zeros((360,100,3))
    
    def __iter__(self, flush=True):
        results = []
        
        while True:
            
            # get current video frame
            if self.video:
                results += [None]
                
                while True:
                    try: results[-1] = self.video.recv(zmq.NOBLOCK)
                    except: break
            
            # get current audio frame
            if self.audio:
                results += [None]
                
                while True:
                    try: results[-1] = self.audio.recv(zmq.NOBLOCK)
                    except: break
            
            # get current chat frame
            if self.chat:
                messages = []
                
                while True:
                    try: messages += [self.chat.recv(zms.NOBLOCK)]
                    except: pass
                
                if messages:
                    messages = [self.chat_frame] + messages
                    
                    self.chat_frame = numpy.concatenate(messages)
                    h,w,c = self.chat_frame.shape
                    
                    self.chat_frame = self.chat_frame[h-360:,:,:]
                
                results[-1] = self.chat_frame
        
        yield results
    
    def __hls__(self):
        # fetch access token to stream
        access = requests.get(
            "http://api.twitch.tv/api/channels/" +
            channel +
            '/access_token',
            headers=headers
        )
        
        assert access.status_code == 200, 'stream access tokens failed:\n' + json.dumps(access.json(), indent=4)
        
        access = access.json()
        
        # fetch stream quality urls
        m3u8 = requests.get(
            "http://usher.twitch.tv/api/channel/hls/" +
            channel +
            ".m3u8?nauth=" +
            access['token'] +
            "&nauthsig=" +
            access['sig']
        )
        
        assert m3u8.status_code == 200, 'failed retrieving VOD download qualities m3u\n' + json.dumps(m3u8.json(), indent=4)
        
        m3u8 = ''.join(m3u8)
        
        # fetch stream hls stream url
        hls = re.search(
            'video="low"' if video else 'video="audio_only"',
            qualities, re.IGNORECASE
        ).span()[0]
        
        return re.search(
            r'http[s]?:\/\/.+\.m3u8',
            m3u8[hls:]
        ).group()
    
    def __del__(self):
        if self.ffmpeg: self.ffmpeg.terminate()
        if self.irc: self.irc.terminate()