import sys
import os
from PIL import Image, ImageChops
import struct
import mmap
import copy
import re
import shutil
from collections import OrderedDict

version = "0.1"

def RGB_to_FTC(r, g, b):
	pixel = 0
	pixel += (r >> 3) << 11
	pixel += (g >> 2) << 5
	pixel += (b >> 3)
	return(pixel)

class TRSSprite(object):
	def __init__(self, mm, headeroffset, scanlength=800):
		self.headeroffset = headeroffset
		self.width = mm[headeroffset]
		self.height = mm[headeroffset+1]
		# 4-6 are empty
		self.unpacked_offset = struct.unpack(">I", mm[headeroffset+4:headeroffset+8])[0]
		self.packed_offset = struct.unpack(">I", mm[headeroffset+8:headeroffset+12])[0]
		if self.packed_offset > 0:
			self.packed = True
		else:
			self.packed = False
		if self.packed:
			self.unpacked_offset = 0
			# This is a modified implementation of noblesse_oblige's reading packed data method: https://github.com/larzm42/dominions-tools/blob/master/sprites.py#L224
			# as the data length isn't saved anywhere, we have to process it to work out how long it is
			# (I could just go to the next sprite, but I don't know how safe that really is: are sprites even necessarily packed in order...?)
			self.packed_data = b""
			offset = copy.copy(self.packed_offset)
			self.packed_data += mm[offset:offset+2]
			chunk_count = struct.unpack(">H", mm[offset:offset+2])[0] + 1
			#print(f"chunks: {chunk_count}")
			offset += 2
			pixels_recorded = 0
			for x in range(0, chunk_count):
				#print(mm[offset:offset+2])
				self.packed_data += mm[offset:offset+2]
				screen_offset = struct.unpack(">H", mm[offset:offset+2])[0] // 2
				offset += 2
				if scanlength < screen_offset:
					screen_offset += pixels_recorded
					pixels_recorded = 0
				else:
					pixels_recorded += screen_offset
				self.packed_data += mm[offset:offset+2]
				pixel_count = struct.unpack(">H", mm[offset:offset+2])[0]
				offset += 2
				if 0x8000 & pixel_count: continue
				pixel_count += 1
				#print(pixel_count)
				self.packed_data += mm[offset:offset+(pixel_count*2)]
				offset += (pixel_count*2)
				pixels_recorded += pixel_count
		else:
			self.packed_offset = 0
			self.unpacked_data = b""
			offset = copy.copy(self.unpacked_offset)
			self.unpacked_data = mm[offset:offset+((self.width*self.height)*2)]
	def writeData(self, f):
		if self.packed:
			#print(f.tell() - self.packed_offset)
			f.write(self.packed_data)
		else:
			#print(f.tell() - self.unpacked_offset)
			f.write(self.unpacked_data)
	def getDataSize(self):
		if self.packed:
			return(len(self.packed_data))
		return(len(self.unpacked_data))
	def replace(self, newspr, newwidth, newheight):
		i = Image.open(newspr)		
		i = i.resize((newwidth, newheight))
		i.thumbnail((newwidth, newheight), Image.LANCZOS)
		thumb = i
		thumb = i.crop((0, 0, newwidth, newheight))
		offset_x = int(max((newwidth - i.size[0])/2, 0))
		offset_y = int(max((newheight - i.size[1])/2, 0))
		
		thumb = ImageChops.offset(thumb, offset_x, offset_y)
		
		rgbimg = thumb.convert("RGB")
		out = b""
		for y in range(0, thumb.size[1]):
			for x in range(0, thumb.size[0]):
				p = rgbimg.getpixel((x, y))
				p = RGB_to_FTC(*p)
				#print(p)
				#print(rgbimg.getpixel((x, y)))
				out += struct.pack(">H", p)
		self.width = thumb.size[0]
		self.height = thumb.size[1]
		self.packed = False
		self.unpacked_data = out
		self.packed_offset = 0
	def writeHeader(self, f):
		if self.width > 255: self.width = 0
		if self.height > 255: self.height = 0
		#print(self.unpacked_offset, self.packed_offset)
		#print(f.tell())
		f.write(bytes([self.width]))
		f.write(bytes([self.height]))
		#print(f.tell())
		f.write(b"\x00\x00")
		
		#print(f.tell())
		f.write(struct.pack(">I", self.unpacked_offset))
		#print(f.tell())
		f.write(struct.pack(">I", self.packed_offset))
		#print(f.tell())
	def setOffset(self, offset):
		if self.packed:
			self.packed_offset = offset
		else:
			self.unpacked_offset = offset
			
			

class TRS(object):
	def __init__(self, fp):
		self.fp = fp
		self.sprites = []
		with open(fp, "rb") as f:
			with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
				offset = 0
				if mm[0:4].decode() != "TCSF":
					raise Exception("Bad TRS file: {}".format(fp))
				self.count = struct.unpack(">H", mm[4:6])[0]
				self.filever = struct.unpack(">H", mm[6:8])[0]
				self.scanlength = struct.unpack(">H", mm[8:10])[0]
				offset = 12
				for x in range(0, self.count):
					#print(f"Read spr {x+1} of {self.count}")
					self.sprites.append(TRSSprite(mm, offset, self.scanlength))
					offset += 12
	def save(self, fp):
		# Recalculate sprite offsets
		offset = 12 # TRS header is this long
		offset += (12*len(self.sprites)) # each sprite header is another 12 long
		for i, spr in enumerate(self.sprites):
			spr.setOffset(copy.copy(offset))
			#print(f"Set offset to {hex(offset)}")
			offset += spr.getDataSize()
		
		with open(fp, "wb") as f:
			f.write(b"TCSF")
			f.write(struct.pack(">H", self.count))
			f.write(struct.pack(">H", self.filever))
			f.write(struct.pack(">H", self.scanlength))
			f.write(b"\x00\x00")
			for spr in self.sprites:
				spr.writeHeader(f)
			for spr in self.sprites:
				spr.writeData(f)

def memeifyTRS(fp, memefp, width=32, height=32):
	t = TRS(fp)
	for i, spr in enumerate(t.sprites):
		print(f"Altering sprite {i+1} of {len(t.sprites)}")
		spr.replace(memefp, width, height)
	t.save(fp)
		
		
class TRSMError(Exception):
	pass
	
class TRSMAction(object):
	def __init__(self, trs, sprindex, width, height, repl):
		self.trs = trs
		self.sprindex = sprindex
		self.width = width
		self.height = height
		self.repl = repl
	def run(self, trsfiles):
		trs = trsfiles[self.trs]
		print(f"Replacing sprite {self.sprindex} in {self.trs} with {self.repl} {self.width}x{self.height}")
		trs.sprites[self.sprindex].replace(self.repl, self.width, self.height)
	
class TRSMOption(object):
	def __init__(self, name):
		self.name = name
		self.actions = []
	def doActions(self, trsfiles):
		for x in self.actions:
			x.run(trsfiles)
	def getReqFiles(self):
		reqs = set()
		for act in self.actions:
			reqs.add(act.trs.lower())
		return reqs
	
class TRSM(object):
	def __init__(self, fp):
		self.fp = fp
		self.name = fp
		self.description = ""
		self.author = ""
		self.options = OrderedDict()
		with open(fp, "r") as f:
			inopt = False
			for i, line in enumerate(f):
				if line.strip() == "": continue
				if line.strip().startswith("--"): continue
				if not inopt:
					line = line.strip()
					m = re.match("#modname \"(.*)\"", line)
					if m is not None:
						self.name = m.groups()[0]
						continue
					m = re.match("#description \"(.*)\"", line)
					if m is not None:
						self.description = m.groups()[0]
						continue
					m = re.match("#author \"(.*)\"", line)
					if m is not None:
						self.author = m.groups()[0]
						continue
					m = re.match("#option \"(.*)\"", line)
					if m is not None:
						curropt = TRSMOption(m.groups()[0])
						inopt = True
						continue
					raise TRSMError(f"Unexpected content on line {i+1} - {line}")
				else:
					m = re.match(r"#edittrs ([a-zA-Z0-9]*) (\d*) (\d*)x(\d*) \"(.*)\"", line)
					if m is not None:
						g = m.groups()
						trs = g[0]
						sprindex = int(g[1])
						width = int(g[2])
						height = int(g[3])
						repl = g[4]
						act = TRSMAction(trs, sprindex, width, height, repl)
						curropt.actions.append(act)
						continue
					if line.startswith("#end"):
						self.options[curropt.name] = curropt
						curropt = None
						inopt = False
						continue
					raise TRSMError(f"Unexpected content inside #option block on line {i+1} - {line}")
	def run(self):
		print(f"{self.name} by {self.author}\n{self.description}\n\n")
		optstorun = []
		for optname, opt in self.options.items():
			while 1:
				print(f"Install option \"{optname}\"? [y/n]")
				i = input().strip().lower()
				if i == "y":
					optstorun.append(opt)
					break
				elif i == "n":
					break
				print("Please enter Y or N.")
		
		print("Gathering dependencies...")
		
		# Figure out which trs files we need to open
		files = set()
		for opt in optstorun:
			files = files.union(opt.getReqFiles())
		
		trsfiles = {}
		for file in files:
			trsfiles[file] = TRS(file + ".trs")
			
		for opt in optstorun:
			print(f"Performing operations for option \"{opt.name}\"")
			opt.doActions(trsfiles)
			
		for filename, file in trsfiles.items():
			print(f"Rewriting TRS file {filename}.trs")
			file.save(file.fp)
			
def backupTRS():
	ls = os.listdir(".")
	if not os.path.isdir("./TRSBackup"):
		os.mkdir("./TRSBackup")
	for file in ls:
		if file.lower().endswith(".trs"):
			shutil.copy(file, os.path.join("./TRSBackup", file))
	print("Backed up current TRS files.")
	
def restoreBackup():
	if not os.path.isdir("./TRSBackup"):
		print("Cannot restore. Backup not found!")
		return()
	ls = os.listdir("./TRSBackup")
	for file in ls:
		if file.lower().endswith(".trs"):
			shutil.copy(os.path.join("./TRSBackup", file), file)
	print("Restored from backup.")
					
def main():
	ls = os.listdir(".")
	mods = []
	for f in ls:
		if f.endswith(".trsm"):
			print(f"Parsing mod: {f}...")
			mods.append(TRSM(f))
	print(f"TRSModder v{version}\n\nThis program allows you to replace Dominions 5 sprites inside the TRS file containers.\nThis makes modifications to vanilla sprites usable in multiplayer, where only you will see them.")
	print(f"This has not been extensively tested. USE AT YOUR OWN RISK.\nUnexpected local crashes are the most likely way for things to go wrong.\nThis has not yet been tested in real multiplayer games.")
	print(f"Updates to Dominions will likely overwrite your changes.\nVerifying files through Steam and recreating your backups is STRONGLY recommended after every update.")
	print("\n\n")
	
	# Look for backups
	if not os.path.isdir("./TRSBackup"):
		print("It looks like you haven't made a backup yet. Creating one, because doing so is a very good idea.")
		backupTRS()
	
	while 1:
		print("Menu: enter the appropriate number to pick its option")
		print("\n")
		print("0: Back up TRS files")
		print("1: Restore backup of TRS files")
		print("2: Exit")
		for i, mod in enumerate(mods):
			print(f"{i+3}: Install components from mod {mod.name}")
		i = input()
		try:
			i = int(i)
		except:
			print("Enter a numeric value corresponding to one of the options.")
			continue
		print("\n\n")
		if i == 0:
			i2 = input("Backup already exists. Enter y to overwrite, or anything else to cancel. ").lower()
			if i2 == "y":
				backupTRS()
		elif i == 1:
			i2 = input("Restore from backup? Enter y to confirm, or anything else to cancel. ").lower()
			if i2 == "y":
				restoreBackup()
		elif i == 2:
			return()
		else:
			try:
				mod = mods[i-3]
			except IndexError:
				print("Specified index not found.")
				continue
			mod.run()
		
if __name__ == "__main__":
	main()