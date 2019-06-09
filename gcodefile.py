from gcodes import GCodeFactory

class GCodeFile:
	def __init__(self, file):
		self.file = file
		self._read_file()

	def _read_file(self):
		self.gcodes = []
		factory = GCodeFactory()
		with open(self.file, "r") as f:
			for line in f:
				tmp = line.strip()
				if tmp == '':
					self.gcodes.append(factory.create_whitespace())
				elif tmp.startswith(";"):
					self.gcodes.append(factory.create_comment(line))
				elif tmp.find(' ') > 0:
					g = factory.create(tmp[:tmp.find(' ')], line)
					if g:
						self.gcodes.append(g)
					else:
						print("<1> Unknown gcode element: {0}".format(line.rstrip()))
				else:
					g = factory.create(tmp, tmp)
					if g:
						self.gcodes.append(g)
					else:
						print("<2> Unknown gcode element: {0}".format(line.rstrip()))

	def print(self):
		print("Hello")
