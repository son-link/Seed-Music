#!/usr/bin/env python2
#-*- coding: UTF-8 -*-

#  Seed Music
#  Copyright 2012 Alfonso Saavedra "Son Link" <sonlink.dourden@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#

##### Import modules #####

try:
	import os
	import gobject
	import pygst
	pygst.require("0.10")
	import gst
	import sys
	import pynotify
	import thread
	import curses
	
	from os.path import join, getsize, isdir
	from mimetypes import guess_type
	from random import shuffle
	from sys import stdout, argv
	from os import access, path, R_OK
	
except ImportError:
	print "Error in Import modules.\n"
	exit(1)

gobject.threads_init()

class UM_allFromDirectory():
	
	"""
	The AllFromDirectory class returns a dictionary with all
	songs identified by integer number.
	"""
	
	def __init__(self, directory):
		self.directory = directory
		self.biblio = dict()
		self.autoid = 0
			
	def get(self):
		
		"""
		Recursive search into the directory. Returns the dictionary.
		"""
		
		for root, dirs, files in os.walk(self.directory):
			for self.filen in files:
				self.mime = guess_type(self.filen)
				self.auxmime = str(self.mime[0])
				self.endmime = self.auxmime.split('/')
				if self.endmime[0] == "audio":
					self.biblio[self.autoid] = root+'/'+self.filen
					self.autoid = self.autoid + 1
					
		return self.biblio
			
	def getLen(self):
		
		"""
		Returns the total items count from dictionary.
		"""
		return len(self.biblio)	
		
class UM_player():
	def __init__(self):
		
		stdscr.addstr(0, 1, 'Welcome to Unseed Music' , curses.color_pair(0) )
		stdscr.refresh()
		
		##### Start instances ####
		x = UM_allFromDirectory(directory)
		self.m = UM_notify()
		
		self.biblio = x.get()
		self.total_tracks = x.getLen()
		self.numeros = range(0, int(self.total_tracks))
		shuffle(self.numeros)
		self.n = 0
		self.block_tags = False
		self.if_play = 1 #0 Pause, 1 Play, -1 Stop
		#print "Total files: ", str(x.getLen())
		
		self.create_pipeline()
		thread.start_new_thread(self.keys, ())
		
	def create_pipeline(self):
		"""
		Create the necessary GStreamer pipeline to play the music.
		"""
		try:
			n = self.numeros[0]
			self.track = self.biblio[n]
			cdsrc = 'filesrc name=src location="%s" ! decodebin name=decode ! audioconvert name=convert ! alsasink name=sink ' % (self.track)
			
			self.pipeline = gst.parse_launch(cdsrc)
			bus = self.pipeline.get_bus()
			
			bus.add_signal_watch()
			
			bus.connect("message::tag", self.bus_message_tag)
			bus.connect("message::error", self.bus_message_error)
			bus.connect("message::eos", self.nextSong)
			
			self.pipeline.set_state(gst.STATE_PLAYING)
			
		except:
			loop.quit()
			curses.endwin()
			print "...Where did you put the songs?"
			exit(1)
			
	def bus_message_error(self, bus, message):
		
		f = open('/tmp/unseedmusic.log', 'w+')
		log = f.read()
		
		"""
		Show GStreamer error.
		"""
		
		e, d = message.parse_error()
		f.write('%s ERROR: %s => %s\n' % (log, self.track, str(e)))
		f.close()
		self.nextSong(1)
	
	def bus_message_tag(self, bus, message):
		
		"""
		Show the bus message tags (in this case the metadata from audio files).
		"""
		
		if not self.block_tags:
			self.block_tags = True
			
			tags = ''
			self.file_tags = {}
			taglist = message.parse_tag()
			for key in taglist.keys():
				try:
					self.file_tags[key] = taglist[key]
				except:
					return False

			try:
				self.song = self.file_tags['title'] + " "
			except:
				self.song = "Unknown title "
				
			try:
				self.arti= self.file_tags['artist']
			except:
				self.arti= "Unknown artist"				

			stdscr.clear()
			stdscr.addstr(0, 1, 'Welcome to Seed Music')
			stdscr.addstr(2, 1, 'Artist: %s' % str(self.arti))
			stdscr.addstr(3, 1, 'Title:  %s' % str(self.song))
			stdscr.addstr(5, 1, ' p: Play/Pause ', curses.A_REVERSE)
			stdscr.addstr(5, 18, ' n: Next track ', curses.A_REVERSE)
			stdscr.addstr(7, 1, ' s: Stop ', curses.A_REVERSE)
			stdscr.addstr(7, 18, ' q: Quit ', curses.A_REVERSE)
			
			stdscr.refresh()
			
			self.m.create(self.song, self.arti)
			self.m.show()
					
	def nextSong(self, w, *args):
		"""
		Play the next song.
		"""
		
		try:
			if self.n < self.total_tracks-1:
				self.n += 1
				n = self.numeros[self.n]
				self.track = self.biblio[n]
				self.pipeline.set_state(gst.STATE_READY)
				self.pipeline.get_by_name('src').set_property('location', 
														"%s" % self.track)
				self.pipeline.get_by_name('decode').connect('new-decoded-pad',
														self.new_decoded_pad)
				self.pipeline.get_by_name('decode').connect('removed-decoded-pad',
														self.removed_decoded_pad)
					
				self.pipeline.set_state(gst.STATE_PLAYING)
				self.block_tags = False
			else:
				self.close()
			
		except IndexError:
			exit(1)
		
	def new_decoded_pad(self, dbin, pad, islast):
		"""
		Create new pad.
		"""
		try:
			pad.link(self.pipeline.get_by_name('convert').get_pad("sink"))
		except gst.LinkError: pass 
		
	def removed_decoded_pad(self, dbin, pad):
		pad.unlink(self.pipeline.get_by_name('convert').get_pad("sink"))
		
	def keys(self):
		
		while True:
			k = stdscr.getch()
					
			if k == ord('n'):
				#Next Song
				self.nextSong(1)
				
			elif k == ord('p'):
				# Play/Pause
				self.play_pause()
				
			elif k == ord('s'):
				# Play/Pause
				self.stop()
						
			elif k == ord('q'):
				# Quit program
				self.close()
	
	def play_pause(self):
		if self.if_play == 0:
			self.pipeline.set_state(gst.STATE_PLAYING)
			self.if_play = 1
			
		elif self.if_play == 1:
			self.pipeline.set_state(gst.STATE_PAUSED)
			self.if_play = 0
			
		else:
			self.pipeline.set_state(gst.STATE_PLAYING)
			self.if_play = 1
			
	def stop(self):
		self.pipeline.set_state(gst.STATE_NULL)
		self.if_play = -1
	
	def close(self):
		self.pipeline.set_state(gst.STATE_NULL)
		curses.endwin()
		loop.quit()
		exit()

class UM_notify():
	"""
	The UM_notify class contains all functions for manage notifications. 
	"""
	
	def __init__(self):
		pass
		
	def create(self, song, artist):
		"""
		Create new notification.
		"""
		
		self.song = song
		self.arti = artist
		
		pynotify.init("Unseen Music")
		
		self.strnot = "Listening " + str(self.song) + "by: " + str(self.arti)
		
		self.notify = pynotify.Notification("Unseen Music", self.strnot)
		self.notify.set_urgency(pynotify.URGENCY_NORMAL)
		self.notify.set_timeout(4000)
		self.notify.add_action("clicked", "Next", p.nextSong, None)
		
	def show(self):
		"""
		Show new notification.
		"""
		
		self.notify.show()

##### main street! #####
if len(sys.argv) == 2:
	directory = sys.argv[1]
	
	if not isdir(directory):
		print '%s is not a directory' % directory
	elif not access(directory, R_OK):
			print 'You don\'t have read permisions in %s' % directory
			
	else:
		# Init Curses
		stdscr = curses.initscr()
		curses.start_color()
		curses.noecho()
		curses.cbreak()

		begin_x = 0 ; begin_y = 0
		height = 10 ; width = 40
		win = curses.newwin(height, width, begin_y, begin_x)

		mega = list()
		p = UM_player()

		loop = gobject.MainLoop()
		try:
			loop.run()
		except KeyboardInterrupt:
			p.close()
			exit()
else:
	print 'Usage: %s <dir>' % sys.argv[0]
	exit(1)
