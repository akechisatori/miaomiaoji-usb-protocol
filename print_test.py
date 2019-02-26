import usb.core
import usb.util
import struct, zlib, logging
from const import CommandByte


class MiaoMiao:
	standardKey = 0x35769521
	max_send_msg_length = 2016
	max_recv_msg_length = 1024
	padding_line = 300

	def __init__(self):
		self.crckeyset = False
		self.connected = True if self.connect() else False

	def connect(self):
		device = usb.core.find(idVendor=0x4348, idProduct=0x5584)
		if device is None:
			raise ValueError('Our device is not connected')
		device.set_configuration()
		self.read_addr = 0x81
		self.write_addr = 0x02
		self.device = device
		self.registerCrcKey()
		return True

	def disconnect(self):
		# try:
		
		# except:

  #           pass
		logging.info("Disconnected.")

	def crc32(self, content):
		return zlib.crc32(content, self.crcKey if self.crckeyset else self.standardKey)

	def packPerBytes(self, bytes, control_command, i):
		result = struct.pack('<BBB', 2, control_command, i)
		result += struct.pack('<H', len(bytes))
		result += bytes

		crc32 = self.crc32(bytes)
		print("crcKey: ",crc32)
		result += struct.pack('<I', crc32)
		result += struct.pack('<B', 3)

		return result


	def addBytesToList(self, bytes):
		length = self.max_send_msg_length
		result = [bytes[i:i+length] for i in range(0, len(bytes), length)]
		return result

	def send(self, allbytes, control_command, need_reply=True):
		print("Control Command: " + str(control_command))
		bytes_list = self.addBytesToList(allbytes)
		for i, bytes in enumerate(bytes_list):
			tmp = self.packPerBytes(bytes, control_command, i)
			self.sendMsgAllPackage(tmp)
		if need_reply:
			return self.recv()

	def sendMsgAllPackage(self, msg):
		write_len = self.device.write(self.write_addr, msg)
		if write_len == len(msg):
			return True
		else:
			return False

	def recv(self):
		raw_msg = self.device.read(self.read_addr, self.max_recv_msg_length)
		parsed = self.resultParser(bytes(raw_msg))
		logging.info("Received %d packets: " % len(parsed) + "".join([str(p) for p in parsed]))
		return raw_msg, parsed

	def resultParser(self, data):
		print("Parsing Data: "+ str(data))
		print("Data Length: " + str(len(data)))
		base = 0
		res = []
		while base < len(data):
			class Info(object):
				def __str__(self):
					string = "\nControl command: %s(%s)\nPayload length: %d\nPayload(hex): %s" % (
                        self.command, CommandByte.findCommand(self.command)
                        , self.payload_length, bytes(self.payload)
                    )
					return string
			info = Info()
			_, info.command, _, info.payload_length = struct.unpack('<BBBH', data[base:base+5])
			info.payload = data[base + 5: base + 5 + info.payload_length]
			info.crc32 = data[base + 5 + info.payload_length: base + 9 + info.payload_length]
			base += 10 + info.payload_length
			res.append(info)

		return res

	def sendPaperType(self, paperType=0):
		msg = struct.pack('<B', paperType)
		self.send(msg, CommandByte.PRT_SET_PAPER_TYPE)

	def querySN(self):
		msg = struct.pack('<B', 1)
		return self.send(msg, CommandByte.PRT_GET_SN)

	def sendDensity(self, density):
		msg = struct.pack('<B', 1)
		return self.send(msg, CommandByte.PRT_SET_HEAT_DENSITY)


	def queryBatteryStatus(self):
		msg = struct.pack('<B', 1)
		return self.send(msg, CommandByte.PRT_GET_BAT_STATUS)

	def sendImage(self, binary_img):
		binary_img = bytes(binary_img,'utf-8')
		self.sendPaperType()
		print("Image Length: " + str(len(binary_img)))
		msg = struct.pack("<%ds" % len(binary_img), binary_img)
		self.send(msg, CommandByte.PRT_PRINT_DATA)
		self.sendFeedLine(self.padding_line)

	def sendFeedLine(self, length):
		msg = struct.pack('<H', length)
		self.send(msg, CommandByte.PRT_FEED_LINE)

	def TestPage(self):
		msg = struct.pack("<B", 1)
		return self.send(msg,CommandByte.PRT_PRINT_TEST_PAGE)

	def BatteryStatus(self):
		msg = struct.pack("<B", 1)
		return self.send(msg,CommandByte.PRT_GET_BAT_STATUS)


	def registerCrcKey(self, key=0x6968634 ^ 0x2e696d):
		logging.info("Setting CRC32 key...")
		msg = struct.pack('<I', int(key ^ self.standardKey))
		ret = self.send(msg, CommandByte.PRT_SET_CRC_KEY)
		self.crcKey = key
		self.crckeyset = True
		logging.info("CRC32 key set")

if __name__ == "__main__":
	logging.getLogger().setLevel(logging.INFO)
	mm = MiaoMiao()
	if mm.connected:
		mm.sendDensity(100)
		mm.TestPage()
		from image_process import ImageConverter

		img = ImageConverter.image2bmp("/tmp/temp.bmp")
		mm.sendImage(img)
		pass



