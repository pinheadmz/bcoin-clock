import requests
import curses
import pyqrcode
import atexit
import time
import os, sys
import json

### default endpoints, not using any API key
# testnet
#nodeurl = "http://127.0.0.1:18332/"
#wallurl = "http://127.0.0.1:18334/wallet/primary/"
# main
nodeurl = "http://127.0.0.1:8332/"
wallurl = "http://127.0.0.1:8334/wallet/primary/"

### set up some functions to get data from bcoin
def getInfo():
	return requests.get(nodeurl).json()

def getAddress():
	params = {"account":"default"}
	return requests.post(wallurl + 'address', json=params).json()

def getBalance():
	return requests.get(wallurl + 'balance?account=default').json()

### read the JSON files from disk, store the last 20 in memory, and remove the files
BLOCKS_DIR = os.path.expanduser('~') + '/blocks/'
BLOCKS = {}
def readFiles(dict, dir, log):
	files = [files for (dirpath, dirnames, files) in os.walk(dir)][0]
	for index in files:
		if log:
			sys.stdout.write("\rHeight: " + str(index))
		try:
			with open (dir + index) as file:
				dict[int(index)] = json.load(file)
		except:
			pass
		sortedDictKeys = sorted(dict)
		if len(sortedDictKeys) > 20:
			del dict[sortedDictKeys[0]]

### display address and QR code
def displayAddr():
	addr = getAddress()['address']
	code = pyqrcode.create(addr, 'M', version=3).terminal()
	
	# switch back to terminal
	endCurses()
	# display QR code
	os.system('clear')
	print addr
	print
	print code
	print
	raw_input("Press Enter to continue...")
	# switch back to our curses UI
	startCurses()
	
### print the text info display
def printInfo(info, balance):
	# pull the relevant bits from the data
	progress = info['chain']['progress']
	latestHeight = info['chain']['height']
	latestHash = info['chain']['tip']
	confbal = balance['confirmed']
	unconfbal = balance['unconfirmed']
	# print it to the screen
	stdscr.erase()
	stdscr.addstr(0, 0, "Progress: " + str(int(progress*100000000)/1000000.0) + "%")
	stdscr.addstr(1, 0, "Height: " + str(latestHeight))
	stdscr.addstr(2, 0, "Hash: " + str(latestHash))
	stdscr.addstr(3, 0, "Confirmed balance: " + str(confbal))
	stdscr.addstr(4, 0, "Unconfirmed balance: " + str(unconfbal))
	
	stdscr.addstr(5, 0, "Window size: " + str(WINDOW / 60) + " min")

	drawBlockchain()

	# print menu on bottom
	menu = "[Q]uit   [D]eposit [+/-]Zoom"
	stdscr.addstr(MAXYX[0]-1, 0, menu)
	stdscr.refresh()

### draw the recent blockchain
WINDOW = 30 * 60 # total seconds across width of screen
def drawBlockchain():
	axis = 24
	secondsPerCol = WINDOW/MAXYX[1]
	stdscr.addstr(axis, 0, "[" + "-" * (MAXYX[1]-2) + "]")
	now = int(time.time())
	down = True	

	for index, block in BLOCKS.items():
		secondsAgo = now - block['time']
		
		if secondsAgo < WINDOW:
			top = axis if down else axis-15
			col = MAXYX[1] - (secondsAgo / secondsPerCol) - 8
			if col > 0:
				stdscr.addstr(axis, col, "|")
				stdscr.addstr(top+1, col, "#" + str(index))
				stdscr.addstr(top+2, col, "Hash:")
				for i in range(8):
					stdscr.addstr(top+3+i, col+1, block['hash'][i*8:i*8+8])
				stdscr.addstr(top+11, col, "TXs:")
				stdscr.addstr(top+12, col+1, str("{:,}".format(block['totalTX'])))
				stdscr.addstr(top+13, col, "Age:")
				stdscr.addstr(top+14, col+1, str(secondsAgo/60) + ":" + str(secondsAgo%60).zfill(2))
				down = not down

### start the curses text-based terminal interface
REFRESH = 1 # refresh rate in seconds
MAXYX = None
stdscr = None
def startCurses():
	global stdscr, MAXYX
	stdscr = curses.initscr()
	curses.noecho()
	curses.cbreak()
	curses.halfdelay(REFRESH * 10) # blocking value is x 0.1 seconds
	MAXYX = stdscr.getmaxyx() # store window dimensions
startCurses()
def endCurses():
	curses.nocbreak()
	curses.echo()
	curses.endwin()

### automatically cleanup curses settings on exit
def cleanup():
	time.sleep(10)
	endCurses()
	os.system('clear')
	print "bye!"
atexit.register(cleanup)

### stash cursor in the bottom right corner
def hideCursor():
	stdscr.addstr(MAXYX[0]-1, MAXYX[1]-1, "")

### check for keyboard input -- also serves as the pause between REFRESH cycles
def checkKeyIn():
	global WINDOW
	keyNum = stdscr.getch()
	if keyNum == -1:
		return False
	else:
		key = chr(keyNum)
	if key in ("q", "Q"):
		sys.exit()
	if key in ("d", "D"):
		displayAddr()
	if key in ("-"):
		WINDOW += 10 * 60
	if key in ("+"):
		WINDOW -= 10 * 60
		if WINDOW < 0:
			WINDOW = 10 * 60

### the main loop!
os.system('clear')
print "Syncing with bcoin..."
readFiles(BLOCKS, BLOCKS_DIR, True)
while True:
	# read block headers from files
	readFiles(BLOCKS, BLOCKS_DIR, False)
	# get data from servers
	info = getInfo()
	balance = getBalance()
	# draw!
	printInfo(info, balance)
	hideCursor()
	checkKeyIn()
