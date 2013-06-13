import sys
import socket
import string
import time
import os
import random
import lxml.html
import re
import threading


argv_flag = {'-c':None, '-h':None, '-p':None, '-k':None}
flag_help = {'-c':'channel ',
             '-h':'host',
             '-p':'port',
             '-k':'character to call on bot'}
show_help = 'Icorrect argument, "{} -help" for help'.format(sys.argv[0])

def cmd_arg():
    '''return IrcBot object based on values supplied by sys.argv'''
    arguments = sys.argv
    if len(sys.argv) == 1:
        connect = IrcBot()
    elif len(sys.argv) == 2:
        if sys.argv[1] == '-help':
            print('')
            for key in flag_help.keys():
                print('\t{0} -- {1}'.format(key, flag_help[key]))
            sys.exit()
        else:
            print(show_help)
    else:
        h, p, c , k = None, None, None, None
        for flag in argv_flag.keys():
            for user_flag in arguments:
                if flag == user_flag:
                    index = arguments.index(user_flag)
                    value = arguments[index + 1]
                    argv_flag[flag] = value
        connect = IrcBot(h=argv_flag['-h'], p=argv_flag['-p'], c=argv_flag['-c'],
                          k=argv_flag['-k'])
    return connect

class IrcBot:
    def __init__(self, h=None, p=None, c=None, k=None):
        '''adjust values based on sys.argv'''
        if h is None:
            self.host = "irc.freenode.net"
        else:
            self.host = h
        if p is None:
            self.port = 6667
        else:
            self.port = p
        if c is None:
            self.channel = '#robgraves'
        else:
            if c[:1] != '#':
                c = '#'+c
            self.channel = c
        if k is None:
            self.contact = ':'
        else:
            self.contact = k
            
        self.nick = "trivia_bot"
        self.ident = "trivia_bot"
        self.realname = "trivia_bot"
        self.list_cmds = {
            'help':(lambda:self.help()),
            'trivia':lambda:self.trivia()
            }
        
        self.op = ['metulburr','Awesome-O', 'robgraves','corp769',
                  'metulburr1', 'robgravesny', 'Optichip', 'Craps_Dealer']
        self.data = None
        self.operation = None
        self.addrname = None
        self.username = None
        self.text = None
        self.timer= None
        self.answer = ''
        self.question = ''
        self.game_in_progress = False
        
        self.sock = self.irc_conn()
        self.wait_event()
        
    def irc_conn(self):
        '''connect to server/port channel, send nick/user '''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('connecting to "{0}/{1}"'.format(self.host, self.port))
        sock.connect((self.host, self.port))
        print('sending NICK "{}"'.format(self.nick))
        sock.send("NICK {0}\r\n".format(self.nick).encode())
        sock.send("USER {0} {0} bla :{0}\r\n".format(
            self.ident,self.host, self.realname).encode())
        print('joining {}'.format(self.channel))
        sock.send(str.encode('JOIN '+self.channel+'\n'))
        return sock
    
    def say(self, string):
        '''send string to irc channel with PRIVMSG '''
        self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.channel, string).encode())
    
    def send_operation(self, operation=None, msg=None, username=None):
        '''send operation to irc with operation arg'''
        if msg is None:
            #send ping pong operation
            self.sock.send('{0} {1}\r\n'.format(operation, self.channel).encode())
        elif msg != None:
            #send private msg to one username
            self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.username,msg).encode())
    def get_user(self, stringer):
        start = stringer.find('~')
        end = stringer.find('@')
        user = stringer[start +1:end]
        return user
        
    def format_data(self):
        '''get data from server:
        self.operation = EXAMPLE: PRIVMSG, JOIN, QUIT
        self.text = what each username says
        self.addrname = the first name on address
        self.username = the username
        self.timer = time 
        '''
        data=self.sock.recv(1042) #recieve server messages
        data = data.decode('utf-8') #data decoded
        self.data = data.strip('\n\r') #data stripped
        try:
            self.operation = data.split()[1]
            textlist = data.split()[3:]
            text = ' '.join(textlist)
            self.text = text[1:]
            self.addrname = self.get_user(data) 
            self.username = data[:data.find('!')][1:]
        except IndexError:
            pass
        self.timer = time.asctime(time.localtime(time.time()))
        
    def print_console(self):
        '''print to console '''
        #print('{0} ({1}): {2}'.format(self.username, self.timer, self.text))
        print(self.data)
        
    def ping_pong(self):
        '''server ping pong handling'''
        try:
            if self.data[:4] == 'PING':
                self.send_operation('PONG')
        except TypeError: #startup data
            pass
        
    def upon_join(self):
        '''when someone joins the channel'''
        if self.operation == 'JOIN':
            pass
    
    def upon_leave(self):
        '''when someone leaves the channel'''
        if self.operation == 'QUIT' or self.operation == 'PART':
            pass
        
    def wait_event(self):
        #time.sleep(10) #wait to connect before starting loop
        while True:
            self.ping_pong()
            self.format_data()
            self.print_console()
            self.upon_join()
            self.upon_leave()
            
            '''
            if self.text.split()[1:][0][0] == 'start':
                self.game_in_progress = True
            elif self.text.split()[1:][0][0] == 'stop':
                self.game_in_progress = False
            '''
            
            self.check_cmd()
            if self.game_in_progress:
                if self.text.lower() == self.answer.lower():
                    self.say('{} recieved from {}'.format(self.text.lower(), self.username))
                
            '''
            #self.check_cmd()
            thread = threading.Thread(target=self.check_cmd)
            thread.start()
            thread2 = threading.Thread(target=self.play)
            thread2.start()
            self.play()
            '''
            
    def not_cmd(self, cmd):
        return '{0}: "{1}" is not one of my commands'.format(self.username, cmd)

    def check_cmd(self):
        '''check if contact is first char of text and send in cmd and its args to crapdealer_commands.commands'''
        if self.text[:1] == self.contact:
            returner = self.commands(self.text.split()[0][1:], self.text.split()[1:])
            if returner != None:
                self.say(returner)

    def commands(self, cmd, *args):
        if not args:
            self.help('trivia')
            return
        try:
            if args[0][0] == 'start':
                if not self.game_in_progress:
                    self.game_in_progress = True
                    thread = threading.Thread(target=self.play)
                    thread.start()
            elif args[0][0] == 'stop':
                self.game_in_progress = False
        except IndexError:
            self.help('trivia')
        
        return
        
        
        try:
            arg1 = args[0][0]
        except IndexError:
            arg1 = ''
        try:
            arg2 = args[0][1]
        except IndexError:
            arg2 = ''

        if cmd in self.list_cmds:
            if not arg1: #if no arguments
                self.list_cmds[cmd]()
            else: #argument with function, run function directly
                if cmd == 'help':# and arg1 in self.list_cmds.keys():
                    self.help(arg1)
                elif cmd == 'trivia':
                    self.trivia(args)
            
    def help(self, arg=None):
        helper = '{0}: {1}help  --show all commands'.format(self.username,self.contact)
        triv = '{0}: {1}trivia [start, stop] --start to start trivia session, stop to stop trivia session'.format(self.username,self.contact)
        
        if arg is None:
            tmp = []
            for key in self.list_cmds.keys():
                tmp.append(key)
            self.say('{0}help [cmd] for desc. cmds = {1}'.format(self.contact,tmp))
        else:
            if arg == 'help':
                self.say(helper)
            if arg == 'trivia':
                self.say(triv)

    '''
    def trivia(self, args=None):


        if not args:
            self.help('trivia')
            return
        elif args[0][0] == 'start':
            self.game_in_progress = True
        elif args[0][0] == 'stop':
            self.game_in_progress = False
    '''
            
    def play(self):
        timer = 20 
        def func(arg):
            time.sleep(5) #spacer between questions
            self.say('15 seconds...')
            time.sleep(5)
            self.say('10 seconds...')
            time.sleep(5)
            self.say('5 seconds...')
            time.sleep(5)
            self.say(arg)
            
        while self.game_in_progress:
            thread = threading.Thread(target=self.check_cmd)
            thread.start()
            
            url = 'http://www.triviacafe.com/random/'
            doc = lxml.html.parse(url)

            section = doc.xpath("//center")[0]
            #print(section.text_content())
            text = section.text_content()

            #get between Question: and Show Answer
            q = re.search(r'Question:.(.*?)Show Answer', text)
            self.question = q.group(1).strip()
            time.sleep(5) #separator between last answer and new question
            self.say(self.question)

            #get multiline between Hide Answer and New Question AKA the answer
            a = re.search(r'(?s)Hide Answer(.*?)New Question', text)
            self.answer = a.group(1).strip()
            #print(answer)

            thread = threading.Thread(target=func, args=(self.answer,))
            thread.start()
            print(self.answer)
            time.sleep(timer)
            ###make pause for 

    
    def create_pkl(picklepath, obj):
        files = open(picklepath, 'wb')
        pickle.dump(obj, files)
        files.close()
        
    def load_pkl(picklepath):
        files = open(picklepath, 'rb')
        obj = pickle.load(files)
        return obj

if __name__ == '__main__':
    connect = cmd_arg()
    try:
        print('channel: ', connect.channel)
        print('port: ', connect.port)
        print('host: ', connect.host)
        print('contact: ', connect.contact)
    except NameError:
        print(show_help)
        
        #stone